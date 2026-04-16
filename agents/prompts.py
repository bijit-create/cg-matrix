"""All agent prompts — structured, sized for fast API calls (<1,500 chars each).
Research basis: Haladyna-Downing-Rodriguez (2002), Rodriguez (2005, 2014), Gierl (2017), ETS (2014), NCF 2023."""

# --- Phase 1 agents ---

INTAKE = """Normalise raw input into a structured task brief. Detect missing fields, ambiguities, conflicts. Output: grade, subject, LO, skill, count, readiness_status."""

CONSTRUCT = """Define the assessment construct — the precise capability measured. What is valid evidence of mastery? What is out of scope? If LO bundles multiple constructs, split them."""

SUBSKILL = """Break the SKILL into 3-6 testable subskills. Focus on SKILL DESCRIPTION (what student DOES), not LO.
Each subskill = specific, observable ACTION. Start with: Identify, Classify, Compare, Apply, Analyse.
Span from simple (recall) to complex (analysis). Each targets a DIFFERENT cognitive operation."""

# --- Content & Matrix agents ---

CONTENT_SCOPING = """Extract testable knowledge points from chapter content for a specific subskill.
CRITICAL: Extract REAL FACTS — not topic headings.
BAD: "Types of food" (heading). GOOD: "Wheat, rice, maize are cereals from plants" (testable fact).
Each point = COMPLETE, TESTABLE statement with specific examples/names/numbers.
Mark: core/supporting/advanced. Grade: primary/middle/high. 3-8 points per subskill."""

CG_MAPPER = """Define a content-specific CG Matrix. Each cell = [Cognitive action] + [content] + [constraint].
Cells: R1(recall), U1(explain), U2(compare/classify), A2(apply to new), A3(multi-step), AN2(analyse patterns), AN3(analyse reasoning).
For each: one-line definition, count, status (active/not_required). Do NOT force-fill all cells."""

MISCONCEPTION = """Select research-backed misconceptions. NEVER invent. Only use catalog_matches or research_findings.
Select 4-8 most relevant. Preserve original IDs and sources."""

# --- Generation: TWO STAGES ---

GENERATION_STAGE1 = """Generate ONE assessment question. UK English. Indian context (₹, names: Riya, Aarav, Kabir, Priya).

OUTPUT: id, type, stem, answer, rationale, needs_image, + type-specific fields.

RULES:
- Generate ONLY from "selected_content". Use EXACT terminology from content.
- ONE problem per stem. Stem contains ALL info needed to answer.
- Use scenarios: "Riya measured..." not "Measure the..."
- NEVER: negative phrasing, "Which is true/false?", passive voice, textbook verbatim.
- Grade: Primary(1-5)=max 15 words/sentence. Middle(6-8)=textbook terms OK. High(9-12)=technical OK.
- needs_image: Decide intelligently per question. Let subject and content decide.

PICTURE-BASED QUESTIONS:
When content involves real objects, organisms, diagrams — design the MCQ so stem or options REQUIRE a picture.
Examples: "Look at the picture. Which is a herbivore?" or "Which picture shows a plant-based food?"
Set needs_image=true. Write stem assuming student WILL see the image.
Grammar/vocabulary/pure math — most questions will NOT need images. That is correct."""

GENERATION_STAGE2 = """Review and improve this generated question. You are a senior assessment reviewer.

CHECK AND FIX:
1. UK ENGLISH: colour, favourite, organise, analyse, behaviour, centre, defence, metre. Fix US spellings.
2. DISTRACTORS: Each wrong option must attract students with a SPECIFIC misconception. Add "why_wrong" = exact reasoning error.
3. OPTIONS: Similar length/grammar. Correct NOT longer. No "all/none of the above".
4. GRADE FIT: Vocabulary appropriate for the grade?
5. DIAGNOSTIC: Does a wrong answer reveal a specific gap?

Return improved question in same format. If already good, return unchanged."""

# Legacy alias for compatibility
GENERATION = GENERATION_STAGE1

# --- QA ---

QA = """Check: (1) factual accuracy — is answer correct? (2) cognitive match — right CG cell level? (3) distractors — plausible and diagnostic? (4) language — UK English, grade-appropriate, Indian context?
Return: pass, issues, severity, score (0-100)."""

# --- Externalized dicts ---

TYPE_INSTRUCTIONS = {
    "mcq": "MCQ with 4 options (A,B,C,D). 1 correct. Wrong options need why_wrong.",
    "true_false": "True/False question. Stem is a clear statement. 2 options: True and False. Add why_wrong for the wrong answer. Statement must test a SPECIFIC fact.",
    "fill_blank": "Fill-in-the-blank. Put ##answer## in stem. Set answer field. (Math only)",
    "one_word": "One-word/short answer. Single word or number answer. (Math only)",
    "match": "Match-the-following. pairs array: ['X → Y', ...]. Min 3 pairs.",
    "arrange": "Arrange-in-order. items array in correct sequence. Min 4 items.",
}

CELL_RULES = {
    "R1": "R1 — Remember DOK1: Student IDENTIFIES/RECALLS/NAMES facts from memory.",
    "U1": "U1 — Understand DOK1: Student EXPLAINS/INTERPRETS defining characteristics.",
    "U2": "U2 — Understand DOK2: Student COMPARES/CLASSIFIES using explicit criteria.",
    "A2": "A2 — Apply DOK2: Student APPLIES learned rules to NEW concrete examples.",
    "A3": "A3 — Apply DOK3: Student APPLIES rules across MULTIPLE STEPS. Multi-step scenarios combining conditions.",
    "AN2": "AN2 — Analyse DOK2: Student ANALYSES/INFERS patterns in structured data.",
    "AN3": "AN3 — Analyse DOK3: Student EVALUATES REASONING, draws conclusions, compares interpretations, identifies faulty logic.",
}

# All subjects: MCQ, True/False, Match, Arrange. NO error analysis.
TYPE_ROTATION = {
    "R1": ["mcq", "true_false", "mcq", "match", "true_false"],
    "U1": ["mcq", "true_false", "mcq", "true_false", "mcq"],
    "U2": ["mcq", "match", "arrange", "mcq", "true_false"],
    "A2": ["mcq", "arrange", "mcq", "match", "mcq"],
    "A3": ["mcq", "arrange", "true_false", "mcq"],
    "AN2": ["mcq", "match", "true_false", "arrange", "mcq"],
    "AN3": ["mcq", "true_false", "arrange", "mcq"],
}

# Math: adds FIB and one_word
MATH_TYPE_ROTATION = {
    "R1": ["mcq", "fill_blank", "one_word", "true_false", "mcq"],
    "U1": ["mcq", "fill_blank", "true_false", "one_word", "mcq"],
    "U2": ["mcq", "match", "fill_blank", "arrange", "one_word"],
    "A2": ["mcq", "fill_blank", "one_word", "match", "mcq"],
    "A3": ["mcq", "fill_blank", "one_word", "arrange"],
    "AN2": ["mcq", "fill_blank", "match", "one_word", "true_false"],
    "AN3": ["mcq", "fill_blank", "true_false", "arrange"],
}
