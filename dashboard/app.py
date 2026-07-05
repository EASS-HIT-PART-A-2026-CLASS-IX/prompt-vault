import httpx
import pandas as pd
import streamlit as st

API_URL = "http://localhost:8000"

CATEGORIES = ["coding", "writing", "debugging", "learning", "other"]


def fetch_prompts() -> list[dict]:
    resp = httpx.get(f"{API_URL}/prompts", params={"limit": 1000}, timeout=5)
    resp.raise_for_status()
    return resp.json()


def create_prompt(payload: dict) -> dict:
    resp = httpx.post(f"{API_URL}/prompts", json=payload, timeout=5)
    resp.raise_for_status()
    return resp.json()


def analyze_prompt(prompt_id: int) -> dict:
    resp = httpx.post(f"{API_URL}/prompts/{prompt_id}/analyze", timeout=30)
    resp.raise_for_status()
    return resp.json()


def delete_prompt(prompt_id: int, token: str) -> None:
    resp = httpx.delete(
        f"{API_URL}/prompts/{prompt_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=5,
    )
    resp.raise_for_status()


def get_token(username: str, password: str) -> str:
    resp = httpx.post(
        f"{API_URL}/token",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=5,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def main() -> None:
    st.set_page_config(page_title="Prompt Vault", layout="wide")
    st.title("Prompt Vault")
    st.caption("Your personal library of AI prompts that actually work.")

    tab_browse, tab_add, tab_analytics = st.tabs(
        ["Browse Prompts", "Add Prompt", "Analytics"]
    )

    # ── Browse ────────────────────────────────────────────────────────────────
    with tab_browse:
        st.subheader("Browse Prompts")

        col_cat, col_tag = st.columns([1, 2])
        with col_cat:
            category_filter = st.selectbox(
                "Filter by category",
                ["All"] + CATEGORIES,
                help="Show only prompts from this category.",
            )
        with col_tag:
            tag_filter = st.text_input(
                "Filter by tag",
                placeholder="e.g. python",
                help="Type a single tag to narrow results.",
            )

        try:
            prompts = fetch_prompts()
        except Exception as exc:
            st.error(
                f"Cannot reach the API at {API_URL}. Is the backend running?\n\n`{exc}`"
            )
            st.stop()

        if category_filter != "All":
            prompts = [p for p in prompts if p["category"] == category_filter]
        tag = tag_filter.strip().lower()
        if tag:
            prompts = [
                p for p in prompts if tag in [t.strip() for t in p.get("tags", "").split(",")]
            ]

        if not prompts:
            st.info("No prompts match your filters. Try clearing the filters or add a new prompt.")
        else:
            cols = ["id", "title", "category", "effectiveness", "tags", "model", "task_type"]
            st.dataframe(pd.DataFrame(prompts)[cols], use_container_width=True, hide_index=True)
            st.caption(f"{len(prompts)} prompt(s) shown.")

            chosen_id = st.selectbox(
                "Expand a prompt to read its full text",
                [None] + [p["id"] for p in prompts],
                format_func=lambda x: "— select —" if x is None else f"#{x}  {next(p['title'] for p in prompts if p['id'] == x)}",
            )
            if chosen_id is not None:
                p = next(p for p in prompts if p["id"] == chosen_id)
                st.markdown(f"**Title:** {p['title']}")
                st.code(p["text"], language=None)
                if p.get("notes"):
                    st.markdown(f"**Notes:** {p['notes']}")

                col_analyze, col_delete = st.columns([2, 1])

                with col_analyze:
                    if st.button("Analyze with AI", key=f"analyze_{chosen_id}"):
                        with st.spinner("Calling analyzer…"):
                            try:
                                analysis = analyze_prompt(chosen_id)
                                st.markdown(f"**Suggested effectiveness:** {analysis['suggested_effectiveness']}/5")
                                st.markdown("**Suggestions:**")
                                for s in analysis["suggestions"]:
                                    st.markdown(f"- {s}")
                                st.markdown(f"**Summary:** {analysis['summary']}")
                            except Exception as exc:
                                st.warning(
                                    f"Analyzer unavailable — start it with:\n\n"
                                    f"`uv run uvicorn analyzer.main:app --port 8001 --reload`\n\n`{exc}`"
                                )

                with col_delete:
                    if st.button("Delete prompt", key=f"delete_{chosen_id}", type="secondary"):
                        st.session_state[f"confirm_delete_{chosen_id}"] = True

                if st.session_state.get(f"confirm_delete_{chosen_id}"):
                    st.warning(f"Delete **#{chosen_id}: {p['title']}**? This cannot be undone.")
                    col_yes, col_no = st.columns(2)
                    with col_yes:
                        if st.button("Yes, delete", key=f"yes_{chosen_id}", type="primary"):
                            try:
                                token = get_token("admin", "vault-admin")
                                delete_prompt(chosen_id, token)
                                st.success("Prompt deleted.")
                                st.session_state.pop(f"confirm_delete_{chosen_id}", None)
                                st.rerun()
                            except Exception as exc:
                                st.error(f"Delete failed: {exc}")
                    with col_no:
                        if st.button("Cancel", key=f"no_{chosen_id}"):
                            st.session_state.pop(f"confirm_delete_{chosen_id}", None)
                            st.rerun()

    # ── Add ───────────────────────────────────────────────────────────────────
    with tab_add:
        st.subheader("Add a New Prompt")
        st.markdown(
            "Fill in the fields below and click **Save Prompt**. "
            "Fields marked with \\* are required."
        )

        with st.form("add_prompt_form", clear_on_submit=True):
            title = st.text_input("Title *", max_chars=100, help="1–100 characters.")
            text = st.text_area("Prompt text *", help="The full prompt body.")

            col_l, col_r = st.columns(2)
            with col_l:
                category = st.selectbox("Category *", CATEGORIES)
                model = st.text_input(
                    "Model *",
                    value="claude-sonnet-4-6",
                    help="e.g. claude-sonnet-4-6, gpt-4o",
                )
                effectiveness = st.slider(
                    "Effectiveness *",
                    min_value=1,
                    max_value=5,
                    value=3,
                    help="1 = poor, 5 = excellent.",
                )
            with col_r:
                task_type = st.text_input(
                    "Task type *", help="e.g. explain concept, code review, summarise"
                )
                tags = st.text_input(
                    "Tags",
                    placeholder="python, fastapi",
                    help="Comma-separated. Auto-lowercased.",
                )
                token_count = st.number_input(
                    "Token count",
                    min_value=1,
                    value=None,
                    placeholder="optional",
                    help="Approximate number of tokens consumed.",
                )

            notes = st.text_area("Notes", help="Extra context or observations (optional).")
            submitted = st.form_submit_button("Save Prompt", type="primary")

        if submitted:
            errors = []
            if not title.strip():
                errors.append("Title is required.")
            if not text.strip():
                errors.append("Prompt text is required.")
            if not task_type.strip():
                errors.append("Task type is required.")
            if not model.strip():
                errors.append("Model is required.")

            if errors:
                for err in errors:
                    st.error(err)
            else:
                payload: dict = {
                    "title": title.strip(),
                    "text": text.strip(),
                    "model": model.strip(),
                    "category": category,
                    "task_type": task_type.strip(),
                    "effectiveness": effectiveness,
                    "tags": tags.strip(),
                    "notes": notes.strip() or None,
                    "token_count": int(token_count) if token_count else None,
                }
                try:
                    created = create_prompt(payload)
                    st.success(f"Saved prompt **#{created['id']}: {created['title']}**")
                except Exception as exc:
                    st.error(f"Failed to save prompt.\n\n`{exc}`")

    # ── Analytics ─────────────────────────────────────────────────────────────
    with tab_analytics:
        st.subheader("Average Effectiveness by Category")
        st.markdown(
            "See which categories contain your highest-rated prompts at a glance."
        )

        try:
            all_prompts = fetch_prompts()
        except Exception:
            st.error(f"Cannot reach the API at {API_URL}.")
            st.stop()

        if not all_prompts:
            st.info("No prompts yet. Add some via the **Add Prompt** tab.")
        else:
            df = pd.DataFrame(all_prompts)
            avg = (
                df.groupby("category")["effectiveness"]
                .mean()
                .reset_index()
                .rename(columns={"category": "Category", "effectiveness": "Avg Effectiveness"})
                .sort_values("Avg Effectiveness", ascending=False)
            )

            st.bar_chart(avg.set_index("Category")["Avg Effectiveness"])
            st.dataframe(avg.round(2), use_container_width=True, hide_index=True)
            st.caption(f"Based on {len(all_prompts)} total prompt(s).")


if __name__ == "__main__":
    main()
