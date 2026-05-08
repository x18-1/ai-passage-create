"""热点分析、过滤、排序和选题生成服务"""

import json
import logging
import math
import re
import asyncio
from datetime import datetime, timedelta
from typing import Any, Optional
from urllib.parse import urlparse

from openai import AsyncOpenAI

from app.config import settings
from app.schemas.hotspot import (
    HotspotAnalysis,
    HotspotPreMatch,
    HotspotRawItem,
    HotspotVO,
    TopicSuggestionVO,
)

IMPORTANCE_ORDER = {
    "urgent": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
}

SOURCE_PRIORITY = {
    "twitter": 1,
    "weibo": 2,
    "bilibili": 3,
    "hackernews": 4,
    "sogou": 5,
    "bing": 6,
}

logger = logging.getLogger(__name__)


class HotspotAnalysisService:
    """热点分析服务"""

    def __init__(self, ai_client: Optional[AsyncOpenAI] = None):
        self.ai_client = ai_client
        self.model = settings.dashscope_model
        self._expansion_cache: dict[str, list[str]] = {}

    def expand_keyword_locally(self, keyword: str) -> list[str]:
        """不依赖 AI 的基础查询扩展"""
        normalized = keyword.strip()
        if not normalized:
            return []

        terms = [normalized]
        parts = [part for part in re.split(r"[\s\-_\/\\·]+", normalized) if len(part) >= 2]
        if len(parts) > 1:
            terms.extend(parts)
            terms.extend(f"{parts[index]} {parts[index + 1]}" for index in range(len(parts) - 1))

        if re.search(r"[\u4e00-\u9fff]", normalized):
            compact = re.sub(r"\s+", "", normalized)
            if compact != normalized:
                terms.append(compact)

        return list(dict.fromkeys(term for term in terms if term))

    async def expand_keyword(self, keyword: str) -> list[str]:
        """AI 查询扩展，失败时回退本地扩展"""
        if keyword in self._expansion_cache:
            logger.info("热点关键词扩展命中缓存 keyword=%s", keyword)
            return self._expansion_cache[keyword]

        local_terms = self.expand_keyword_locally(keyword)
        if not self.ai_client:
            logger.info("热点关键词扩展使用本地规则 keyword=%s count=%s", keyword, len(local_terms))
            self._expansion_cache[keyword] = local_terms
            return local_terms

        prompt = f"""你是搜索查询扩展专家。请为监控关键词生成 5-12 个检索变体。
要求：
1. 保留原始关键词。
2. 包含常见简称、别名、中英文表达、空格/连字符变体。
3. 不加入过于泛化的词。
4. 只输出 JSON 字符串数组。

关键词：{keyword}"""
        try:
            response = await self.ai_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            content = response.choices[0].message.content or "[]"
            parsed = self._parse_json_array(content)
            expanded = [item.strip() for item in parsed if isinstance(item, str) and item.strip()]
            result = list(dict.fromkeys([*local_terms, *expanded]))
            logger.info("热点关键词扩展完成 keyword=%s count=%s", keyword, len(result))
            self._expansion_cache[keyword] = result
            return result
        except Exception as error:
            logger.exception("热点关键词扩展失败，回退本地规则 keyword=%s error=%s", keyword, error)
            self._expansion_cache[keyword] = local_terms
            return local_terms

    def pre_match_keyword(self, text: str, expanded_keywords: list[str]) -> HotspotPreMatch:
        """检查文本是否包含扩展关键词"""
        lower_text = text.lower()
        matched_terms = [term for term in expanded_keywords if term.lower() in lower_text]
        return HotspotPreMatch(matched=bool(matched_terms), matchedTerms=matched_terms)

    def deduplicate_results(self, items: list[HotspotRawItem]) -> list[HotspotRawItem]:
        """按标准化 URL 和标题去重"""
        seen_urls: set[str] = set()
        seen_titles: set[str] = set()
        result: list[HotspotRawItem] = []

        for item in items:
            normalized_url = self._normalize_url(item.url)
            normalized_title = self._normalize_title(item.title)
            if normalized_url in seen_urls or normalized_title in seen_titles:
                continue
            seen_urls.add(normalized_url)
            seen_titles.add(normalized_title)
            result.append(item)

        return result

    async def analyze_items(self, keyword: str, expanded_keywords: list[str], items: list[HotspotRawItem]) -> list[HotspotRawItem]:
        """给热点补充 AI 分析"""
        semaphore = asyncio.Semaphore(3)
        logger.info("热点 AI 分析开始 keyword=%s count=%s concurrency=3", keyword, len(items))

        async def analyze_one(item: HotspotRawItem) -> HotspotRawItem:
            full_text = f"{item.title}\n{item.content}"
            pre_match = self.pre_match_keyword(full_text, expanded_keywords)
            async with semaphore:
                item.analysis = await self.analyze_content(full_text, keyword, pre_match)
            self._apply_pre_match_floor(item.analysis, pre_match)
            logger.info(
                "热点 AI 分析完成 source=%s relevance=%s importance=%s keywordMentioned=%s matchedTerms=%s title=%s",
                item.source,
                item.analysis.relevance,
                item.analysis.importance,
                item.analysis.keyword_mentioned,
                pre_match.matched_terms[:3],
                item.title[:80],
            )
            return item

        return await asyncio.gather(*(analyze_one(item) for item in items))

    async def analyze_content(self, content: str, keyword: str, pre_match: HotspotPreMatch) -> HotspotAnalysis:
        """分析内容真实性、相关性和重要程度"""
        if not self.ai_client:
            return HotspotAnalysis(
                isReal=True,
                relevance=55 if pre_match.matched else 20,
                relevanceReason="未配置 AI 服务，使用关键词预匹配规则",
                keywordMentioned=pre_match.matched,
                importance="medium" if pre_match.matched else "low",
                summary=content[:80],
            )

        prompt = self._build_analysis_prompt(keyword, pre_match)
        try:
            response = await self.ai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt},
                    {"role": "user", "content": content[:2000]},
                ],
                temperature=0.2,
            )
            raw_content = response.choices[0].message.content or "{}"
            parsed = self._parse_json_object(raw_content)
            return HotspotAnalysis(
                isReal=bool(parsed.get("isReal", True)),
                relevance=max(0, min(100, int(parsed.get("relevance", 0) or 0))),
                relevanceReason=str(parsed.get("relevanceReason", ""))[:240],
                keywordMentioned=bool(parsed.get("keywordMentioned", False)),
                importance=parsed.get("importance") if parsed.get("importance") in IMPORTANCE_ORDER else "low",
                summary=str(parsed.get("summary", ""))[:180],
            )
        except Exception as error:
            logger.exception("热点 AI 内容分析失败，使用降级规则 keyword=%s error=%s", keyword, error)
            return HotspotAnalysis(
                isReal=True,
                relevance=45 if pre_match.matched else 15,
                relevanceReason="AI 分析失败，使用降级规则",
                keywordMentioned=pre_match.matched,
                importance="low",
                summary=content[:80],
            )

    def filter_and_rank(self, items: list[HotspotRawItem]) -> list[HotspotRawItem]:
        """过滤并排序热点"""
        cutoff = datetime.now() - timedelta(days=7)
        candidates: list[HotspotRawItem] = []
        for item in items:
            if item.published_at and item.published_at < cutoff:
                logger.info("热点过滤：过期 source=%s title=%s", item.source, item.title[:80])
                continue
            if not item.analysis:
                logger.info("热点过滤：无分析结果 source=%s title=%s", item.source, item.title[:80])
                continue
            if not item.analysis.is_real:
                logger.info("热点过滤：疑似虚假或垃圾内容 source=%s title=%s", item.source, item.title[:80])
                continue
            if item.analysis.relevance < 50:
                logger.info(
                    "热点过滤：相关性过低 source=%s relevance=%s title=%s",
                    item.source,
                    item.analysis.relevance,
                    item.title[:80],
                )
                continue
            if not item.analysis.keyword_mentioned and item.analysis.relevance < 65:
                logger.info(
                    "热点过滤：未直接提及关键词且相关性不足 source=%s relevance=%s title=%s",
                    item.source,
                    item.analysis.relevance,
                    item.title[:80],
                )
                continue
            item.heat_score = self.calc_hot_score(item)
            logger.info(
                "热点命中 source=%s heatScore=%.2f importance=%s relevance=%s title=%s",
                item.source,
                item.heat_score,
                item.analysis.importance,
                item.analysis.relevance,
                item.title[:80],
            )
            candidates.append(item)

        return sorted(candidates, key=self._rank_key)

    def prioritize_for_analysis(self, items: list[HotspotRawItem], expanded_keywords: list[str]) -> list[HotspotRawItem]:
        """按新鲜度、关键词命中、来源优先级和已有互动排序待分析候选"""
        cutoff = datetime.now() - timedelta(days=7)
        fresh_items = [item for item in items if not item.published_at or item.published_at >= cutoff]

        def rank_key(item: HotspotRawItem):
            full_text = f"{item.title}\n{item.content}"
            pre_match = self.pre_match_keyword(full_text, expanded_keywords)
            published_ts = item.published_at.timestamp() if item.published_at else 0
            engagement = (
                (item.like_count or 0) * 10
                + (item.retweet_count or 0) * 5
                + ((item.comment_count or 0) + (item.reply_count or 0) + (item.quote_count or 0)) * 3
                + math.log10(max(item.view_count or 0, 1)) * 2
            )
            return (
                0 if pre_match.matched else 1,
                SOURCE_PRIORITY.get(item.source, 99),
                -engagement,
                -published_ts,
            )

        sorted_items = sorted(fresh_items, key=rank_key)
        logger.info("热点候选排序完成 raw=%s fresh=%s", len(items), len(sorted_items))
        return sorted_items

    def _apply_pre_match_floor(self, analysis: HotspotAnalysis, pre_match: HotspotPreMatch) -> None:
        if not pre_match.matched or not analysis.is_real:
            return
        analysis.keyword_mentioned = True
        if analysis.relevance < 65:
            analysis.relevance = 65
            if not analysis.relevance_reason:
                analysis.relevance_reason = "标题或正文直接命中监控关键词，按规则保留为候选热点"
        if analysis.importance == "low":
            analysis.importance = "medium"

    def calc_hot_score(self, item: HotspotRawItem) -> float:
        """计算热度分，互动优先，浏览量对数缩放"""
        likes = item.like_count or 0
        retweets = item.retweet_count or 0
        comments = (item.comment_count or 0) + (item.reply_count or 0) + (item.quote_count or 0)
        views = item.view_count or 0
        return likes * 10 + retweets * 5 + comments * 3 + math.log10(max(views, 1)) * 2

    async def generate_topic_suggestions(
        self,
        keyword: str,
        hotspots: list[HotspotRawItem],
        limit: int,
    ) -> list[TopicSuggestionVO]:
        """基于热点生成选题建议"""
        if not hotspots:
            return []
        if not self.ai_client:
            return self._fallback_suggestions(keyword, hotspots, limit)

        prompt = self._build_topic_prompt(keyword, hotspots[:8], limit)
        try:
            response = await self.ai_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.55,
            )
            raw_content = response.choices[0].message.content or "[]"
            parsed = self._parse_json_array(raw_content)
            suggestions = [
                TopicSuggestionVO(
                    title=str(item.get("title", ""))[:120],
                    contentDescription=str(item.get("contentDescription", ""))[:600],
                    angle=str(item.get("angle", ""))[:160],
                    viralReason=str(item.get("viralReason", ""))[:240],
                    suitablePlatforms=list(item.get("suitablePlatforms", []))[:5],
                    sourceHotspotTitles=list(item.get("sourceHotspotTitles", []))[:5],
                )
                for item in parsed
                if isinstance(item, dict) and item.get("title") and item.get("contentDescription")
            ]
            return suggestions[:limit] or self._fallback_suggestions(keyword, hotspots, limit)
        except Exception as error:
            logger.exception("热点选题生成失败，使用降级规则 keyword=%s error=%s", keyword, error)
            return self._fallback_suggestions(keyword, hotspots, limit)

    def to_vo(self, item: HotspotRawItem) -> HotspotVO:
        """转换为前端展示对象"""
        analysis = item.analysis or HotspotAnalysis()
        return HotspotVO(
            title=item.title,
            content=item.content,
            url=item.url,
            source=item.source,
            publishedAt=item.published_at.isoformat() if item.published_at else None,
            heatScore=round(item.heat_score, 2),
            isReal=analysis.is_real,
            relevance=analysis.relevance,
            relevanceReason=analysis.relevance_reason,
            keywordMentioned=analysis.keyword_mentioned,
            importance=analysis.importance,
            summary=analysis.summary,
            viewCount=item.view_count,
            likeCount=item.like_count,
            retweetCount=item.retweet_count,
            commentCount=item.comment_count,
            authorName=item.author_name,
        )

    def _rank_key(self, item: HotspotRawItem):
        analysis = item.analysis or HotspotAnalysis()
        published_ts = item.published_at.timestamp() if item.published_at else 0
        return (
            IMPORTANCE_ORDER.get(analysis.importance, 4),
            -item.heat_score,
            -analysis.relevance,
            SOURCE_PRIORITY.get(item.source, 99),
            -published_ts,
        )

    def _fallback_suggestions(self, keyword: str, hotspots: list[HotspotRawItem], limit: int) -> list[TopicSuggestionVO]:
        suggestions: list[TopicSuggestionVO] = []
        for item in hotspots[:limit]:
            summary = item.analysis.summary if item.analysis else item.content[:80]
            suggestions.append(
                TopicSuggestionVO(
                    title=f"{keyword}热点解读：{item.title[:48]}",
                    contentDescription=f"围绕热点「{item.title}」展开，先交代事件背景，再分析它与「{keyword}」的关系，最后给出对普通用户、创作者或从业者的启发。参考信息：{summary}",
                    angle="热点解读 + 趋势分析 + 实用建议",
                    viralReason="热点自带关注度，结合明确人群收益和观点判断，更容易形成点击和转发。",
                    suitablePlatforms=["公众号", "头条", "知乎", "小红书"],
                    sourceHotspotTitles=[item.title],
                )
            )
        return suggestions

    def _normalize_url(self, url: str) -> str:
        parsed = urlparse(url.strip())
        host = parsed.netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        path = parsed.path.rstrip("/")
        return f"{parsed.scheme.lower()}://{host}{path}"

    def _normalize_title(self, title: str) -> str:
        return re.sub(r"\s+", "", title.strip().lower())

    def _parse_json_object(self, content: str) -> dict[str, Any]:
        match = re.search(r"\{[\s\S]*\}", content.strip())
        if not match:
            return {}
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else {}

    def _parse_json_array(self, content: str) -> list[Any]:
        match = re.search(r"\[[\s\S]*\]", content.strip())
        if not match:
            return []
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, list) else []

    def _build_analysis_prompt(self, keyword: str, pre_match: HotspotPreMatch) -> str:
        match_hint = (
            f"文本预匹配命中：{'、'.join(pre_match.matched_terms)}"
            if pre_match.matched
            else f"文本未直接提及关键词「{keyword}」，请严格判断相关性。"
        )
        return f"""你是热点内容分析专家。请判断内容是否适合围绕关键词「{keyword}」创作爆款文章。
{match_hint}

输出 JSON：
{{
  "isReal": true,
  "relevance": 0,
  "relevanceReason": "说明为什么相关或不相关",
  "keywordMentioned": true,
  "importance": "low|medium|high|urgent",
  "summary": "一句话中文摘要"
}}

只输出 JSON。"""

    def _build_topic_prompt(self, keyword: str, hotspots: list[HotspotRawItem], limit: int) -> str:
        hotspot_text = "\n".join(
            f"{index + 1}. [{item.source}] {item.title}\n摘要：{item.analysis.summary if item.analysis else item.content[:100]}\n链接：{item.url}"
            for index, item in enumerate(hotspots)
        )
        return f"""你是爆款文章选题策划。请基于以下热点，为关键词「{keyword}」生成 {limit} 个可直接复制到创作平台的文章选题。

热点：
{hotspot_text}

输出 JSON 数组，每项格式：
{{
  "title": "选题标题",
  "contentDescription": "给写作智能体的内容描述，包含背景、核心观点、结构建议和可引用热点",
  "angle": "推荐切入角度",
  "viralReason": "为什么可能成为爆文",
  "suitablePlatforms": ["公众号", "知乎"],
  "sourceHotspotTitles": ["引用的热点标题"]
}}

要求标题有传播性但不要标题党，描述要具体，方便用户复制到选题和补充描述。只输出 JSON。"""
