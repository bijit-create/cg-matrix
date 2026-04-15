"""JSON schemas for structured Gemini output."""

INTAKE = {
    "type": "object",
    "properties": {
        "task_id": {"type": "string"}, "grade": {"type": "string"},
        "subject": {"type": "string"}, "learning_objective": {"type": "string"},
        "skill": {"type": "string"}, "target_question_count": {"type": "integer"},
        "readiness_status": {"type": "string", "enum": ["ready", "blocked"]},
    },
    "required": ["grade", "subject", "learning_objective", "skill", "target_question_count"],
}

CONSTRUCT = {
    "type": "object",
    "properties": {
        "construct_statement": {"type": "string"},
        "evidence_of_mastery": {"type": "string"},
        "non_evidence_or_out_of_scope": {"type": "string"},
        "bundled_constructs_flag": {"type": "boolean"},
    },
    "required": ["construct_statement", "evidence_of_mastery"],
}

SUBSKILL = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "subskill_id": {"type": "string"},
            "subskill_description": {"type": "string"},
            "complexity_level": {"type": "string"},
            "suitable_CG_cells": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["subskill_id", "subskill_description"],
    },
}

CONTENT_SCOPE = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "id": {"type": "string"}, "category": {"type": "string"},
            "knowledge_point": {"type": "string"}, "source": {"type": "string"},
            "grade_level": {"type": "string", "enum": ["primary", "middle", "high"]},
            "scope_type": {"type": "string", "enum": ["core", "supporting", "advanced"]},
            "flag": {"type": "string"},
        },
        "required": ["id", "category", "knowledge_point", "scope_type"],
    },
}

CG_MATRIX_CELL = {
    "type": "object",
    "properties": {
        "count": {"type": "integer"},
        "definition": {"type": "string"},
        "status": {"type": "string", "enum": ["active", "not_required", "not_applicable"]},
    },
    "required": ["count", "definition", "status"],
}

CG_MAPPER = {
    "type": "object",
    "properties": {
        "matrix": {
            "type": "object",
            "properties": {k: CG_MATRIX_CELL for k in ["R1", "U1", "U2", "A2", "A3", "AN2", "AN3"]},
            "required": ["R1", "U1", "U2", "A2", "A3", "AN2", "AN3"],
        },
        "total_questions": {"type": "integer"},
    },
    "required": ["matrix", "total_questions"],
}

MISCONCEPTION = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "misconception_id": {"type": "string"},
            "misconception_text": {"type": "string"},
            "type": {"type": "string", "enum": ["conceptual", "procedural", "factual"]},
            "prevalence": {"type": "string", "enum": ["common", "moderate", "rare"]},
            "incorrect_reasoning": {"type": "string"},
        },
        "required": ["misconception_id", "misconception_text", "type"],
    },
}

GENERATION = {
    "type": "object",
    "properties": {
        "id": {"type": "string"}, "type": {"type": "string"},
        "stem": {"type": "string"}, "answer": {"type": "string"},
        "rationale": {"type": "string"}, "needs_image": {"type": "boolean"},
        "options": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "label": {"type": "string"}, "text": {"type": "string"},
                "correct": {"type": "boolean"}, "why_wrong": {"type": "string"},
            },
            "required": ["label", "text", "correct"],
        }},
        "steps": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "text": {"type": "string"}, "correct": {"type": "boolean"}, "fix": {"type": "string"},
            },
            "required": ["text", "correct"],
        }},
        "pairs": {"type": "array", "items": {"type": "string"}},
        "items": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["id", "type", "stem", "answer"],
}

QA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "question_id": {"type": "string"}, "pass": {"type": "boolean"},
            "issues": {"type": "array", "items": {"type": "string"}},
            "severity": {"type": "string", "enum": ["critical", "major", "minor", "none"]},
        },
        "required": ["question_id", "pass"],
    },
}
