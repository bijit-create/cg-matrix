"""Multi-Perspective AI Evaluation — calls AI 3 times with different lenses, combines quantitatively."""

import json
from concurrent.futures import ThreadPoolExecutor
from agents.api import generate_agent_response

DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "decision": {"type": "boolean"},
        "confidence": {"type": "number"},
        "reason": {"type": "string"},
    },
    "required": ["decision", "confidence", "reason"],
}

QA_SCHEMA = {
    "type": "object",
    "properties": {
        "pass": {"type": "boolean"},
        "issues": {"type": "array", "items": {"type": "string"}},
        "score": {"type": "number"},
    },
    "required": ["pass", "score"],
}


def evaluate_image_need(stem: str, q_type: str, subject: str, grade: str) -> dict:
    """3-perspective image decision: student, teacher, assessment designer."""
    perspectives = [
        f'You are a Grade {grade} {subject} student. Would you understand this question BETTER with a picture? Question: "{stem}"',
        f'You are a {subject} teacher for Grade {grade}. Does this question REQUIRE a visual element to be a valid assessment item? Question: "{stem}"',
        f'You are a TIMSS assessment expert. Would adding an image change the CONSTRUCT being measured? Question: "{stem}" Subject: {subject}, Grade: {grade}',
    ]

    def call(prompt):
        try:
            return generate_agent_response("Image Analysis", prompt, "{}", DECISION_SCHEMA, cacheable=False)
        except:
            return None

    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(call, perspectives))

    votes = [r for r in results if r]
    if not votes:
        return {"needs_image": False, "confidence": 0, "reasons": ["All perspectives failed"]}

    yes_weight = sum(v["confidence"] / 100 for v in votes if v["decision"])
    no_weight = sum(v["confidence"] / 100 for v in votes if not v["decision"])
    reasons = [f"{'YES' if v['decision'] else 'NO'} ({v['confidence']}%): {v['reason']}" for v in votes]

    needs_image = yes_weight > no_weight
    total = yes_weight + no_weight
    confidence = round((max(yes_weight, no_weight) / total) * 100) if total > 0 else 0

    return {"needs_image": needs_image, "confidence": confidence, "reasons": reasons}


def evaluate_question_quality(question: dict, subject: str, grade: str, lo: str) -> dict:
    """3-perspective QA: factual, pedagogical, language."""
    stem = question.get("stem", "")
    q_type = question.get("type", "mcq")
    options = "\n".join(f"{o.get('label','?')}. {o.get('text','')}" for o in question.get("options", []))
    answer = question.get("answer", "")
    q_summary = f"Type: {q_type}\nStem: {stem}\n{f'Options:\n{options}' if options else ''}\nAnswer: {answer}"

    prompts = [
        f"You are a {subject} expert for Grade {grade}. Check FACTUAL accuracy ONLY. Is the answer correct? Any factual errors? Units correct?\nQuestion:\n{q_summary}\nLO: {lo}",
        f"You are a curriculum specialist. Check PEDAGOGICAL quality ONLY. Right cognitive level? Diagnostic? Plausible distractors? Clear stem?\nQuestion:\n{q_summary}\nLO: {lo}\nGrade: {grade}",
        f"You are a language reviewer for Indian schools. Check LANGUAGE ONLY. UK English? Grade-appropriate vocabulary? Cultural relevance? Gender-neutral?\nQuestion:\n{q_summary}",
    ]
    lenses = ["Factual", "Pedagogical", "Language"]

    def call(args):
        lens, prompt = args
        try:
            r = generate_agent_response("AI SME QA", prompt, "{}", QA_SCHEMA, cacheable=False)
            return {"lens": lens, "score": r.get("score", 50), "issues": [f"[{lens}] {i}" for i in r.get("issues", [])], "pass": r.get("pass", True)}
        except:
            return {"lens": lens, "score": 50, "issues": [f"[{lens}] Review failed"], "pass": True}

    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(call, zip(lenses, prompts)))

    all_issues = []
    total_score = 0
    for r in results:
        all_issues.extend(r["issues"])
        total_score += r["score"]

    overall_score = round(total_score / len(results)) if results else 50
    has_critical = any(r["score"] < 30 for r in results)
    passed = overall_score >= 60 and not has_critical

    return {"pass": passed, "overall_score": overall_score, "issues": all_issues, "perspectives": results}
