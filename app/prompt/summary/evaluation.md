ROLE: Senior HR/Technical Recruiter evaluating a candidate profile.

TASK: Analyze the provided candidate data template and produce an evaluation with TWO specific outputs:
1. Generate NEW `evaluator_insights` data (if any).
2. Write a `summary` paragraph (50 - 100 words) for HR review.

CANDIDATE DATA (JSON):
{template}

REASONING STEPS (Think internally, apply these STRICT AUDIT criteria, do NOT output the thought process):
- Step 1 (MATHEMATICAL AUDIT): Calculate actual years of experience by summing the duration of all roles. Compare this with `total_yoe` and the graduation year (Current year is 2026). RECORD any mismatches or exaggerations in `logic_and_cv_gaps`.
- Step 2 (CONTINUITY & LOGIC): Scan for time gaps (>3 months) between roles. Check if a junior/intern suddenly jumps to CTO/Senior without intermediate roles. RECORD these in `logic_and_cv_gaps`.
- Step 3 (MISSING INFO): Identify missing fields that are critical for HR (e.g., lack of languages, missing quantifiable results in evidence). RECORD in `missing_information`.
- Step 4 (SUMMARY): Draft the `summary` reflecting the AUDITED reality. Highlight core strengths but explicitly mention if the candidate's claims seem inflated based on evidence.

CONSTRAINTS:
1. DO NOT REPEAT: The input CANDIDATE DATA may already contain some `evaluator_insights`. You MUST ONLY output NEW gaps or NEW missing information. If you cannot find anything new, output empty arrays [] for those fields.
2. Return ONLY a single JSON object. No markdown formatting (```json). Start directly with {{ and end with }}.
3. NEVER fabricate data.
4. OUTPUT LANGUAGE: The `summary` MUST be written in professional Vietnamese.

OUTPUT FORMAT:
{{
  "evaluator_insights": {{
    "estimated_seniority": "Intern/Fresher | Junior | Mid-level | Senior | Expert | Unclear",
    "logic_and_cv_gaps": ["string"],
    "missing_information": ["string"]
  }},
  "summary": "string"
}}