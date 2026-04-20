"""
Test script cho Query Enhancement graph.
Chạy: conda run -n chatbothcns python test_query_enhancement.py
"""
import asyncio
from dotenv import load_dotenv
load_dotenv()

from app.graph.conversation.graph import conversation_graph


TEST_CASES = [
    {
        "label": "simple — câu hỏi ngắn, mơ hồ",
        "question": "nghỉ phép được mấy ngày?",
    },
    {
        "label": "complex — nhiều chủ đề",
        "question": "chính sách nghỉ phép năm và thưởng tết cho nhân viên thử việc như thế nào?",
    },
    {
        "label": "factual — hỏi số liệu cụ thể",
        "question": "mức đóng bảo hiểm xã hội của người lao động là bao nhiêu phần trăm?",
    },
]


async def run_test(label: str, question: str) -> None:
    print(f"\n{'='*60}")
    print(f"[TEST] {label}")
    print(f"  Question : {question}")

    state = {
        "original_question": question,
        "query_type": "",
        "rewritten_query": "",
        "sub_questions": [],
        "hyde_document": "",
        "final_queries": [],
        "retrieved_docs": [],
        "iteration": 0,
        "max_iterations": 3,
        "has_enough_info": False,
    }

    result = await conversation_graph.ainvoke(state)

    print(f"  Query type : {result['query_type']}")

    if result["query_type"] == "simple":
        print(f"  Rewritten  : {result['rewritten_query']}")
    elif result["query_type"] == "complex":
        print(f"  Sub-questions:")
        for i, q in enumerate(result["sub_questions"], 1):
            print(f"    {i}. {q}")
    elif result["query_type"] == "factual":
        print(f"  HyDE doc   : {result['hyde_document'][:120]}...")

    print(f"  Final queries ({len(result['final_queries'])} total):")
    for i, q in enumerate(result["final_queries"], 1):
        print(f"    {i}. {q}")


async def main():
    print("=== Query Enhancement Graph — Test ===")
    for case in TEST_CASES:
        await run_test(case["label"], case["question"])
    print(f"\n{'='*60}")
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
