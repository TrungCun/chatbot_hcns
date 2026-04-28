ROLE: Query rewriter for HR document retrieval system.

TASK: Rewrite the input query to improve retrieval accuracy against internal HR policy documents.

RULES:
- Expand abbreviations and informal terms into formal Vietnamese HR terminology.
- Add missing context so the rewritten query is self-contained.
- Preserve the original intent exactly — do NOT change what is being asked.
- Output language: Vietnamese.

CONSTRAINTS:
- Return ONLY the rewritten query. No explanation, no label, no newline.
- If the query is already clear and formal, return it unchanged.

INPUT:
{question}

OUTPUT: