"""CG-Matrix Gen System — Streamlit Edition"""

import json, streamlit as st
from agents.api import generate_agent_response, generate_with_search
from agents import prompts, schemas
from utils.file_parser import parse_file
from utils.exporter import export_to_excel

st.set_page_config(page_title="CG-Matrix Gen", page_icon="🧠", layout="wide")

# --- Auth Gate ---
def check_auth():
    secret = st.secrets.get("APP_SECRET", "")
    if not secret:
        return True
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if st.session_state.authenticated:
        return True
    st.markdown("## 🧠 CG-Matrix Gen System")
    token = st.text_input("Access Token", type="password", key="auth_input")
    if st.button("Enter", type="primary"):
        if token == secret:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Invalid token.")
    return False

if not check_auth():
    st.stop()

# --- Sidebar ---
mode = st.sidebar.radio("Mode", ["⚡ Quick Generate", "🔬 Full Pipeline"], index=0)
st.sidebar.markdown("---")
st.sidebar.caption("CG-Matrix Gen System v2.0")

# ============================================================
# QUICK GENERATE
# ============================================================
if mode == "⚡ Quick Generate":
    st.title("⚡ Quick Generate")
    st.caption("Input → Questions. No gates, no approvals.")

    col_input, col_results = st.columns([1, 2])

    with col_input:
        # Init defaults
        for k, v in [("q_lo", ""), ("q_skill", ""), ("q_tsv", "")]:
            if k not in st.session_state: st.session_state[k] = v

        tsv = st.text_area("Quick Paste (TSV Row)", height=60, placeholder="Paste Excel row...", key="q_tsv")

        # TSV auto-parse — populate session state so widgets update on next rerun
        if tsv and tsv.strip():
            try:
                row = tsv.strip().split("\n")[-1].split("\t")
                if len(row) >= 6:
                    if not st.session_state.q_skill: st.session_state.q_skill = row[5]
                    if len(row) > 15 and not st.session_state.q_lo: st.session_state.q_lo = row[15]
                    st.session_state["meta"] = {"grade": row[1], "subject": row[0], "skill_code": row[3] if len(row) > 3 else ""}
            except: pass

        lo = st.text_area("Learning Objective", height=60, key="q_lo")
        skill = st.text_input("Skill Description", key="q_skill")
        count = st.number_input("Questions", min_value=1, max_value=30, value=15)

        uploaded = st.file_uploader("Upload Content (PDF/DOCX/Excel)", type=["pdf", "docx", "xlsx"])
        content = st.text_area("Or paste chapter text", height=100)
        if uploaded:
            try:
                text = parse_file(uploaded.name, uploaded.read())
                content = (content or "") + "\n\n" + text
                st.success(f"Extracted {len(text)} chars from {uploaded.name}")
            except Exception as e:
                st.error(str(e))

        generate_btn = st.button("🚀 Generate All", type="primary", use_container_width=True, disabled=not lo or not skill)

    # Init session state
    if "questions" not in st.session_state:
        st.session_state.questions = []
    if "logs" not in st.session_state:
        st.session_state.logs = []

    meta = st.session_state.get("meta", {})

    if generate_btn:
        st.session_state.questions = []
        st.session_state.logs = []
        progress = col_results.empty()
        log_area = col_results.empty()

        def log(msg):
            st.session_state.logs.append(msg)

        with st.spinner("Building Hess Matrix..."):
            log("Building Hess Matrix...")
            try:
                matrix = generate_agent_response("Custom Hess Matrix Agent", prompts.CG_MAPPER, json.dumps({
                    "construct": skill, "subskills": [skill], "target_questions": count,
                    "grade": meta.get("grade", ""), "subject": meta.get("subject", ""),
                    "learning_objective": lo, "skill": skill,
                    "approved_knowledge_points": content[:2000] if content else lo,
                }), schemas.CG_MAPPER)

                cg = matrix.get("matrix", {})
                cells = [(c, d["count"], d.get("definition", c)) for c, d in cg.items()
                         if d.get("status") == "active" and d.get("count", 0) > 0]
                log(f"Matrix: {', '.join(f'{c}:{n}' for c, n, _ in cells)}")
            except Exception as e:
                st.error(f"Hess Matrix failed: {e}")
                st.stop()

        # Search exemplars
        with st.spinner("Searching question banks..."):
            log("Searching exemplars...")
            exemplar = ""
            try:
                exemplar = generate_with_search("Research Agent",
                    f"Find 6-10 real assessment questions for: \"{skill}\" ({meta.get('subject','')}, Grade {meta.get('grade','')})."
                    " Search: NCERT Exemplar, CBSE, DIKSHA, Khan Academy. UK English. Grade-appropriate.",
                    json.dumps({"skill": skill, "lo": lo}))[:1500]
                log("Found exemplar questions." if len(exemplar) > 50 else "No exemplars found.")
            except:
                log("Exemplar search failed.")

        # Generate questions
        all_qs = []
        for cell, cell_count, cell_def in cells:
            types = prompts.TYPE_ROTATION.get(cell, ["mcq"])
            for qi in range(cell_count):
                qtype = types[qi % len(types)]
                qid = f"{cell}-{len(all_qs)+1}"
                progress.info(f"Generating {qid} ({qtype})...")

                # Avoid repetition
                already = [q["stem"][:40] for q in all_qs[-5:]]
                avoid = ("\nALREADY GENERATED (do NOT repeat):\n" + "\n".join(f'- "{s}..."' for s in already)) if already else ""

                try:
                    prompt = f"""{prompts.GENERATION}
{prompts.CELL_RULES.get(cell, '')}
Cell: {cell_def}
Generate 1 "{qtype}". {prompts.TYPE_INSTRUCTIONS.get(qtype, prompts.TYPE_INSTRUCTIONS['mcq'])}
Content: {(content or lo)[:500]}
Skill: {skill}. Grade: {meta.get('grade','')}.
UK English. Indian names. Grade-appropriate.{avoid}
{f'EXEMPLAR QUESTIONS:{chr(10)}{exemplar[:400]}' if exemplar else ''}"""

                    q = generate_agent_response("Generation Agent", prompt,
                        json.dumps({"id": qid, "type": qtype, "cell": cell}),
                        schemas.GENERATION, cacheable=False)
                    all_qs.append({**q, "cell": cell, "type": qtype, "id": qid})
                    log(f"{qid}: {qtype} ✓")
                except Exception as e:
                    log(f"{qid}: failed — {str(e)[:40]}")

        st.session_state.questions = all_qs
        progress.success(f"Done! {len(all_qs)} questions generated.")

    # --- Display Results ---
    with col_results:
        questions = st.session_state.questions
        if questions:
            st.markdown(f"**{len(questions)} questions generated**")

            # Export
            excel = export_to_excel(questions, {"lo": lo, "skill": skill, **meta})
            st.download_button("📥 Download Excel", excel, file_name="questions.xlsx",
                             mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            # Feedback
            with st.expander("💬 Feedback & Refine", expanded=False):
                feedback = st.text_area("Describe what to change:", placeholder="e.g., Make easier, more scenarios, avoid jargon...")
                if st.button("🔄 Refine All") and feedback:
                    with st.spinner("Refining..."):
                        refined = []
                        for q in questions:
                            try:
                                r = generate_agent_response("Generation Agent",
                                    f"{prompts.GENERATION}\nRefine this question based on feedback: \"{feedback}\"\n"
                                    f"Original: {q['stem']}\nKeep type={q['type']}, cell={q['cell']}, id={q['id']}.\n"
                                    f"{prompts.TYPE_INSTRUCTIONS.get(q['type'], '')}",
                                    json.dumps({"id": q["id"], "type": q["type"], "cell": q["cell"]}),
                                    schemas.GENERATION, cacheable=False)
                                refined.append({**r, "cell": q["cell"], "type": q["type"], "id": q["id"]})
                            except:
                                refined.append(q)
                        st.session_state.questions = refined
                        st.rerun()

            # Question cards
            for q in questions:
                qtype = q.get("type", "mcq")
                needs_img = q.get("needs_image", False)
                color = "#E3F2FD" if needs_img else "#F2F1EF"

                with st.container():
                    # Header
                    cols = st.columns([1, 8, 2])
                    cols[0].markdown(f"**`{q['id']}`**")
                    cols[1].markdown(f"**{qtype.upper().replace('_',' ')}** · {q.get('cell','')}")
                    if needs_img:
                        cols[2].markdown("🖼️ **IMG**")
                    else:
                        cols[2].caption("Text Only")

                    # Stem
                    st.code(q.get("stem", ""), language=None)

                    # MCQ options
                    if qtype == "mcq" and q.get("options"):
                        for opt in q["options"]:
                            label = opt.get("label", "?")
                            is_correct = opt.get("correct", False)
                            icon = "✅" if is_correct else "⬜"
                            st.markdown(f"{icon} **{label}.** {opt.get('text', '')}")
                            if not is_correct and opt.get("why_wrong"):
                                st.caption(f"    ↳ {opt['why_wrong']}")

                    # Fill blank
                    if qtype == "fill_blank":
                        st.success(f"**Answer:** {q.get('answer', '')}")

                    # Error analysis
                    if qtype == "error_analysis" and q.get("steps"):
                        for i, step in enumerate(q["steps"]):
                            if step.get("correct"):
                                st.markdown(f"**Step {i+1}:** {step['text']}  ✅")
                            else:
                                st.error(f"**Step {i+1}:** ~~{step['text']}~~  ❌")
                                if step.get("fix"):
                                    st.success(f"    ↳ Correct: {step['fix']}")

                    # Match
                    if qtype == "match" and q.get("pairs"):
                        import pandas as pd
                        pairs_data = []
                        for p in q["pairs"]:
                            if isinstance(p, str) and "→" in p:
                                l, r = p.split("→", 1)
                                pairs_data.append({"Left": l.strip(), "Right": r.strip()})
                        if pairs_data:
                            st.table(pd.DataFrame(pairs_data))

                    # Arrange
                    if qtype == "arrange" and q.get("items"):
                        for i, item in enumerate(q["items"]):
                            st.markdown(f"**{i+1}.** {item}")

                    # Rationale
                    if q.get("rationale"):
                        st.caption(f"💡 {q['rationale']}")

                    st.divider()

        # Logs
        if st.session_state.logs:
            with st.expander("📋 Logs", expanded=False):
                for log_msg in st.session_state.logs:
                    st.text(log_msg)

# ============================================================
# FULL PIPELINE
# ============================================================
elif mode == "🔬 Full Pipeline":
    st.title("🔬 Full Pipeline")
    st.caption("4-gate pipeline with SME review at each stage.")

    # Init state
    for key in ["pipe_step", "pipe_lo", "pipe_skill", "pipe_count", "pipe_content",
                 "pipe_meta", "pipe_construct", "pipe_subskills", "pipe_selected_subskills",
                 "pipe_content_scope", "pipe_selected_scope", "pipe_cg_plan", "pipe_cell_data",
                 "pipe_misconceptions", "pipe_questions", "pipe_logs", "pipe_cell_queue",
                 "pipe_current_cell", "pipe_cell_questions"]:
        if key not in st.session_state:
            st.session_state[key] = None if key != "pipe_step" else "input"

    step = st.session_state.pipe_step

    # --- Step: Input ---
    if step == "input":
        st.subheader("📝 New Generation Task")

        for k, v in [("p_lo", ""), ("p_skill", ""), ("p_tsv", "")]:
            if k not in st.session_state: st.session_state[k] = v

        tsv = st.text_area("Quick Paste (TSV Row)", height=60, key="p_tsv")

        # TSV auto-parse
        if tsv and tsv.strip():
            try:
                row = tsv.strip().split("\n")[-1].split("\t")
                if len(row) >= 6:
                    if not st.session_state.p_skill: st.session_state.p_skill = row[5]
                    if len(row) > 15 and not st.session_state.p_lo: st.session_state.p_lo = row[15]
                    st.session_state.pipe_meta = {"grade": row[1], "subject": row[0], "skill_code": row[3] if len(row) > 3 else ""}
            except: pass

        lo = st.text_area("Learning Objective", height=80, key="p_lo")
        skill = st.text_input("Skill Description", key="p_skill")
        count = st.number_input("Number of Questions", 1, 30, 15)
        uploaded = st.file_uploader("Upload Content", type=["pdf", "docx", "xlsx"], key="p_upload")
        content = st.text_area("Or paste chapter text", height=120)

        if uploaded:
            try:
                text = parse_file(uploaded.name, uploaded.read())
                content = (content or "") + "\n\n" + text
                st.success(f"Extracted {len(text)} chars")
            except Exception as e:
                st.error(str(e))

        if st.button("🚀 Initialize Pipeline", type="primary", disabled=not lo or not skill):
            st.session_state.pipe_lo = lo
            st.session_state.pipe_skill = skill
            st.session_state.pipe_count = count
            st.session_state.pipe_content = content
            st.session_state.pipe_logs = []

            with st.spinner("Running Intake → Construct → Subskill..."):
                meta = st.session_state.pipe_meta or {}
                # Intake
                intake = generate_agent_response("Intake Agent", prompts.INTAKE, json.dumps({
                    "learning_objective": lo, "skill": skill, "target_question_count": count,
                    "chapter_content": (content or "")[:3000], **meta,
                }), schemas.INTAKE)

                # Construct
                construct = generate_agent_response("Construct Agent", prompts.CONSTRUCT,
                    json.dumps(intake), schemas.CONSTRUCT)
                st.session_state.pipe_construct = construct.get("construct_statement", "")

                # Subskill
                subskills = generate_agent_response("Subskill Agent", prompts.SUBSKILL, json.dumps({
                    "construct": construct, "skill_description": skill, "learning_objective": lo,
                    "instruction": f"FOCUS ON THE SKILL: \"{skill}\".",
                }), schemas.SUBSKILL)
                st.session_state.pipe_subskills = [s.get("subskill_description", "") for s in subskills]
                st.session_state.pipe_selected_subskills = [True] * len(subskills)

            st.session_state.pipe_step = "gate1"
            st.rerun()

    # --- Gate 1: Subskills ---
    elif step == "gate1":
        st.subheader("Gate 1: Construct & Subskills")
        st.info(st.session_state.pipe_construct)

        subskills = st.session_state.pipe_subskills
        selected = st.session_state.pipe_selected_subskills

        for i, sub in enumerate(subskills):
            selected[i] = st.checkbox(sub, value=selected[i], key=f"sub_{i}")
        st.session_state.pipe_selected_subskills = selected

        if st.button("✅ Approve & Continue", type="primary"):
            approved = [s for s, sel in zip(subskills, selected) if sel]
            if not approved:
                st.error("Select at least one subskill.")
            else:
                with st.spinner("Scoping content..."):
                    meta = st.session_state.pipe_meta or {}
                    all_scope = []
                    for sub in approved:
                        try:
                            points = generate_agent_response("Content Scoping Agent", prompts.CONTENT_SCOPING, json.dumps({
                                "subskill": sub, "learning_objective": st.session_state.pipe_lo,
                                "skill": st.session_state.pipe_skill,
                                "chapter_content": (st.session_state.pipe_content or "")[:2000],
                                "grade": meta.get("grade", ""), "subject": meta.get("subject", ""),
                            }), schemas.CONTENT_SCOPE)
                            all_scope.extend(points)
                        except: pass
                    st.session_state.pipe_content_scope = all_scope
                    st.session_state.pipe_selected_scope = [s.get("scope_type") != "advanced" for s in all_scope]
                st.session_state.pipe_step = "gate2"
                st.rerun()

    # --- Gate 2: Content Scope ---
    elif step == "gate2":
        st.subheader("Gate 2: Content Scope")
        scope = st.session_state.pipe_content_scope
        selected = st.session_state.pipe_selected_scope

        if not scope:
            st.warning("No content scope extracted. Proceeding with skill only.")
            if st.button("Continue"):
                st.session_state.pipe_step = "gate3_build"
                st.rerun()
        else:
            categories = sorted(set(s.get("category", "Other") for s in scope))
            for cat in categories:
                st.markdown(f"**{cat}**")
                items = [(i, s) for i, s in enumerate(scope) if s.get("category", "Other") == cat]
                for idx, s in items:
                    label = s.get("knowledge_point", "")
                    badge = s.get("scope_type", "core")
                    selected[idx] = st.checkbox(f"{label}  `{badge}`", value=selected[idx], key=f"scope_{idx}")
            st.session_state.pipe_selected_scope = selected

            if st.button("✅ Approve & Build Hess Matrix", type="primary"):
                st.session_state.pipe_step = "gate3_build"
                st.rerun()

    # --- Build Hess Matrix + Misconceptions ---
    elif step == "gate3_build":
        with st.spinner("Building Hess Matrix + Misconceptions..."):
            meta = st.session_state.pipe_meta or {}
            scope = st.session_state.pipe_content_scope or []
            selected = st.session_state.pipe_selected_scope or []
            approved_scope = [s for s, sel in zip(scope, selected) if sel]
            knowledge = "\n".join(s.get("knowledge_point", "") for s in approved_scope)

            # Hess Matrix
            matrix = generate_agent_response("Custom Hess Matrix Agent", prompts.CG_MAPPER, json.dumps({
                "construct": st.session_state.pipe_construct,
                "subskills": [s for s, sel in zip(st.session_state.pipe_subskills, st.session_state.pipe_selected_subskills) if sel],
                "target_questions": st.session_state.pipe_count,
                "grade": meta.get("grade", ""), "subject": meta.get("subject", ""),
                "learning_objective": st.session_state.pipe_lo,
                "skill": st.session_state.pipe_skill,
                "approved_knowledge_points": knowledge[:2000],
            }), schemas.CG_MAPPER)

            cg = matrix.get("matrix", {})
            st.session_state.pipe_cg_plan = {c: d.get("count", 0) for c, d in cg.items()}
            st.session_state.pipe_cell_data = cg

            # Misconceptions (simplified)
            st.session_state.pipe_misconceptions = []
            try:
                with open("knowledge_base/misconceptions.json") as f:
                    catalog = json.load(f)
                subject = meta.get("subject", "").lower()
                keywords = (st.session_state.pipe_lo + " " + st.session_state.pipe_skill).lower().split()
                keywords = [w for w in keywords if len(w) > 3]
                matches = [m for m in catalog if any(kw in (m.get("MISCONCEPTION","")+" "+m.get("TOPIC","")).lower() for kw in keywords)]
                st.session_state.pipe_misconceptions = matches[:8]
            except: pass

        st.session_state.pipe_step = "gate3"
        st.rerun()

    # --- Gate 3: Hess Matrix ---
    elif step == "gate3":
        st.subheader("Gate 3: Hess Matrix & Misconceptions")

        cg = st.session_state.pipe_cell_data or {}
        st.markdown("**CG Matrix Allocation**")

        cols = st.columns(4)
        cols[0].markdown("**Bloom's**")
        cols[1].markdown("**DOK 1**")
        cols[2].markdown("**DOK 2**")
        cols[3].markdown("**DOK 3**")

        grid = [
            ("Remember", ["R1", None, None]),
            ("Understand", ["U1", "U2", None]),
            ("Apply", [None, "A2", "A3"]),
            ("Analyse", [None, "AN2", "AN3"]),
        ]
        plan = st.session_state.pipe_cg_plan or {}

        for label, cells_row in grid:
            cols = st.columns(4)
            cols[0].markdown(f"**{label}**")
            for ci, cell_key in enumerate(cells_row):
                if cell_key and cell_key in cg:
                    d = cg[cell_key]
                    count_val = plan.get(cell_key, d.get("count", 0))
                    plan[cell_key] = cols[ci+1].number_input(cell_key, 0, 20, count_val, key=f"cg_{cell_key}")
                    cols[ci+1].caption(d.get("definition", "")[:60])
                elif cell_key:
                    cols[ci+1].markdown("—")
                else:
                    cols[ci+1].markdown("—")

        st.session_state.pipe_cg_plan = plan
        total = sum(plan.values())
        st.metric("Total Questions", total)

        # Misconceptions
        miscon = st.session_state.pipe_misconceptions
        if miscon:
            st.markdown(f"**Misconceptions ({len(miscon)})**")
            for m in miscon[:5]:
                st.caption(f"• {m.get('MISCONCEPTION','')}")
        else:
            st.warning("No misconceptions found for this topic.")

        if st.button("✅ Approve & Generate Questions", type="primary"):
            st.session_state.pipe_step = "generate"
            st.rerun()

    # --- Generate Questions ---
    elif step == "generate":
        st.subheader("Generating Questions...")
        meta = st.session_state.pipe_meta or {}
        plan = st.session_state.pipe_cg_plan or {}
        cell_data = st.session_state.pipe_cell_data or {}
        scope = st.session_state.pipe_content_scope or []
        selected_scope = st.session_state.pipe_selected_scope or []
        approved = [s for s, sel in zip(scope, selected_scope) if sel]
        content = st.session_state.pipe_content or ""

        # Exemplar search
        exemplar = ""
        with st.spinner("Searching exemplars..."):
            try:
                exemplar = generate_with_search("Research Agent",
                    f"Find 6-10 real questions for \"{st.session_state.pipe_skill}\" "
                    f"({meta.get('subject','')}, Grade {meta.get('grade','')}).",
                    json.dumps({"skill": st.session_state.pipe_skill}))[:1500]
            except: pass

        cells = [(c, n) for c, n in plan.items() if n > 0]
        all_qs = []
        progress = st.progress(0)
        status = st.empty()
        total_qs = sum(n for _, n in cells)
        done = 0

        for cell, cell_count in cells:
            types = prompts.TYPE_ROTATION.get(cell, ["mcq"])
            cell_def = cell_data.get(cell, {}).get("definition", cell)

            for qi in range(cell_count):
                qtype = types[qi % len(types)]
                qid = f"{cell}-{len(all_qs)+1}"
                status.info(f"Generating {qid} ({qtype})...")

                already = [q["stem"][:40] for q in all_qs[-5:]]
                avoid = ("\nALREADY GENERATED:\n" + "\n".join(f'- "{s}"' for s in already)) if already else ""

                try:
                    prompt = f"""{prompts.GENERATION}
{prompts.CELL_RULES.get(cell, '')}
Cell: {cell_def}
Generate 1 "{qtype}". {prompts.TYPE_INSTRUCTIONS.get(qtype, '')}
Content: {content[:500] if content else st.session_state.pipe_lo}
Skill: {st.session_state.pipe_skill}. Grade: {meta.get('grade','')}.
UK English. Indian names. Grade-appropriate.{avoid}
{f'EXEMPLARS:{chr(10)}{exemplar[:400]}' if exemplar else ''}"""

                    q = generate_agent_response("Generation Agent", prompt,
                        json.dumps({"id": qid, "type": qtype, "cell": cell}),
                        schemas.GENERATION, cacheable=False)
                    all_qs.append({**q, "cell": cell, "type": qtype, "id": qid})
                except Exception as e:
                    st.warning(f"{qid} failed: {str(e)[:40]}")

                done += 1
                progress.progress(done / total_qs)

        st.session_state.pipe_questions = all_qs
        st.session_state.pipe_step = "gate4"
        st.rerun()

    # --- Gate 4: Review & Export ---
    elif step == "gate4":
        st.subheader("Gate 4: Review & Export")
        questions = st.session_state.pipe_questions or []
        st.success(f"✅ {len(questions)} questions generated!")

        # Export
        meta = st.session_state.pipe_meta or {}
        excel = export_to_excel(questions, {
            "lo": st.session_state.pipe_lo, "skill": st.session_state.pipe_skill, **meta
        })
        st.download_button("📥 Download Excel", excel, file_name="questions.xlsx",
                         mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")

        # Feedback
        with st.expander("💬 Feedback & Refine"):
            feedback = st.text_area("What to change?", key="pipe_feedback")
            if st.button("🔄 Refine All", key="pipe_refine") and feedback:
                with st.spinner("Refining..."):
                    refined = []
                    for q in questions:
                        try:
                            r = generate_agent_response("Generation Agent",
                                f"{prompts.GENERATION}\nRefine based on: \"{feedback}\"\nOriginal: {q['stem']}\n"
                                f"Keep type={q['type']}, cell={q['cell']}.\n{prompts.TYPE_INSTRUCTIONS.get(q['type'],'')}",
                                json.dumps({"id": q["id"], "type": q["type"], "cell": q["cell"]}),
                                schemas.GENERATION, cacheable=False)
                            refined.append({**r, "cell": q["cell"], "type": q["type"], "id": q["id"]})
                        except:
                            refined.append(q)
                    st.session_state.pipe_questions = refined
                    st.rerun()

        # Display questions
        for q in questions:
            qtype = q.get("type", "mcq")
            needs_img = q.get("needs_image", False)

            with st.container():
                c1, c2, c3 = st.columns([1, 8, 2])
                c1.markdown(f"**`{q['id']}`**")
                c2.markdown(f"**{qtype.upper().replace('_',' ')}** · {q.get('cell','')}")
                c3.markdown("🖼️ **IMG**" if needs_img else "Text Only")

                st.code(q.get("stem", ""), language=None)

                if qtype == "mcq" and q.get("options"):
                    for opt in q["options"]:
                        icon = "✅" if opt.get("correct") else "⬜"
                        st.markdown(f"{icon} **{opt.get('label','?')}.** {opt.get('text','')}")

                if qtype == "fill_blank":
                    st.success(f"**Answer:** {q.get('answer', '')}")

                if qtype == "error_analysis" and q.get("steps"):
                    for i, s in enumerate(q["steps"]):
                        if s.get("correct"):
                            st.markdown(f"Step {i+1}: {s['text']}  ✅")
                        else:
                            st.error(f"Step {i+1}: ~~{s['text']}~~  ❌")
                            if s.get("fix"):
                                st.success(f"  ↳ {s['fix']}")

                if qtype == "match" and q.get("pairs"):
                    import pandas as pd
                    data = []
                    for p in q["pairs"]:
                        if "→" in str(p):
                            l, r = str(p).split("→", 1)
                            data.append({"Left": l.strip(), "Right": r.strip()})
                    if data: st.table(pd.DataFrame(data))

                if qtype == "arrange" and q.get("items"):
                    for i, item in enumerate(q["items"]):
                        st.markdown(f"**{i+1}.** {item}")

                if q.get("rationale"):
                    st.caption(f"💡 {q['rationale']}")

                st.divider()

        # Start over
        if st.button("🔄 Start New Pipeline"):
            for key in list(st.session_state.keys()):
                if key.startswith("pipe_"):
                    del st.session_state[key]
            st.rerun()
