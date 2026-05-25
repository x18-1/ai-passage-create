"""Build stage-specific context blocks for article creation agents."""

from app.schemas.agent_context import AgentContext
from app.services.memory_service import MemoryService
from app.services.rag_knowledge_service import RagKnowledgeService
from app.services.writing_skill_service import WritingSkillService


class AgentContextBuilder:
    def __init__(self, db, memory_service=None, writing_skill_service=None, rag_knowledge_service=None):
        self.db = db
        self.memory_service = memory_service or MemoryService(db)
        self.writing_skill_service = writing_skill_service or WritingSkillService(db)
        self.rag_knowledge_service = rag_knowledge_service or RagKnowledgeService(db)

    async def build_context(
        self,
        user_id: int,
        task_id: str,
        stage: str,
        topic: str,
        style: str | None,
        enabled_skill_refs: list[str],
        enable_memory: bool,
        enable_rag: bool,
        rag_collections: list[str],
    ) -> AgentContext:
        memory_context = ""
        skill_context = ""
        rag_context = ""

        if enable_memory:
            memories = await self.memory_service.list_for_stage(user_id, stage)
            memory_context = "\n".join(f"- {memory.title}: {memory.content}" for memory in memories)

        skills = await self.writing_skill_service.list_for_stage(user_id, stage, enabled_skill_refs)
        skill_context = "\n".join(f"- {skill.name}: {skill.content}" for skill in skills)

        if enable_rag and stage in {"title", "outline", "content"}:
            rag_context = await self.rag_knowledge_service.query_prompt_context(
                user_id=user_id,
                query=topic,
                collections=rag_collections,
                top_k=5,
            )

        instruction_block = self._compose_instruction_block(memory_context, skill_context, rag_context)
        await self._save_snapshot(
            user_id=user_id,
            task_id=task_id,
            stage=stage,
            memory_context=memory_context,
            skill_context=skill_context,
            rag_context=rag_context,
            instruction_block=instruction_block,
        )
        return AgentContext(
            memory_context=memory_context,
            skill_context=skill_context,
            rag_context=rag_context,
            instruction_block=instruction_block,
        )

    def _compose_instruction_block(self, memory_context: str, skill_context: str, rag_context: str) -> str:
        sections = []
        if memory_context:
            sections.append(f"【用户长期偏好】\n{memory_context}")
        if skill_context:
            sections.append(f"【启用写作 Skill】\n{skill_context}")
        if rag_context:
            sections.append(f"【相关知识库资料】\n{rag_context}\n请基于资料写作；资料不足时不要编造具体事实。")
        return "\n\n".join(sections)

    async def _save_snapshot(
        self,
        user_id: int,
        task_id: str,
        stage: str,
        memory_context: str,
        skill_context: str,
        rag_context: str,
        instruction_block: str,
    ) -> None:
        token_estimate = max(1, len(instruction_block) // 4) if instruction_block else 0
        await self.db.execute(
            query="""
                INSERT INTO agent_context_snapshot (
                    taskId, userId, stage, memoryContext, skillContext, ragContext, tokenEstimate
                )
                VALUES (
                    :taskId, :userId, :stage, :memoryContext, :skillContext, :ragContext, :tokenEstimate
                )
            """,
            values={
                "taskId": task_id,
                "userId": user_id,
                "stage": stage,
                "memoryContext": memory_context,
                "skillContext": skill_context,
                "ragContext": rag_context,
                "tokenEstimate": token_estimate,
            },
        )
