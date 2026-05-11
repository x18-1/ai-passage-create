import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.rag.kernel import RagQueryResult, format_results_for_prompt


def test_format_results_for_prompt_includes_source_and_score():
    results = [
        RagQueryResult(text="AI 编程正在改变 IDE 工作流", source="hotspot.md", score=0.91),
        RagQueryResult(text="开发者工具需要强调效率收益", source="doc.md", score=0.82),
    ]

    prompt = format_results_for_prompt(results)

    assert "AI 编程正在改变 IDE 工作流" in prompt
    assert "来源: hotspot.md" in prompt
    assert "相关度: 0.91" in prompt
    assert "开发者工具需要强调效率收益" in prompt
