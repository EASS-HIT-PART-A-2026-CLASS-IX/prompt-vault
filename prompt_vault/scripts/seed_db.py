"""Seed the database with sample prompts."""

from sqlmodel import Session, select

from prompt_vault.app.database import engine, init_db
from prompt_vault.app.models import Prompt, PromptCreate
from prompt_vault.app.repository import PromptRepository


def seed_prompts() -> None:
    init_db()

    with Session(engine) as session:
        existing = session.exec(select(Prompt)).first()
        if existing:
            print("Database already contains prompts. Skipping seed.")
            return

        repo = PromptRepository(session)
        samples = [
            PromptCreate(
                title="Explain a concept simply",
                text="Explain {concept} as if I'm a developer who knows Python but has never studied {topic}. Use a concrete analogy.",
                model="claude-sonnet-4-6",
                category="learning",
                task_type="explain concept",
                effectiveness=5,
                tags="teaching,explain,analogy",
                notes="Works best when you fill in both placeholders explicitly.",
                token_count=95,
            ),
            PromptCreate(
                title="Code review checklist",
                text="Review the following Python code for: (1) correctness, (2) readability, (3) edge cases, (4) performance. Return findings as a numbered list.\n\n```python\n{code}\n```",
                model="claude-sonnet-4-6",
                category="coding",
                task_type="code review",
                effectiveness=4,
                tags="review,python,quality",
                token_count=140,
            ),
            PromptCreate(
                title="Debug with hypothesis",
                text="I have a bug: {bug_description}. My current hypothesis is {hypothesis}. What are three alternative causes I might be missing? For each, suggest a minimal test to confirm or rule it out.",
                model="claude-sonnet-4-6",
                category="debugging",
                task_type="debug assistance",
                effectiveness=4,
                tags="debugging,hypothesis,testing",
                token_count=110,
            ),
            PromptCreate(
                title="Write commit message",
                text="Write a concise git commit message for the following diff. Follow conventional commits format (type: short description). Diff:\n{diff}",
                model="claude-sonnet-4-6",
                category="coding",
                task_type="commit message",
                effectiveness=5,
                tags="git,commit,conventional-commits",
                token_count=75,
            ),
            PromptCreate(
                title="Refactor for readability",
                text="Refactor the following code to be more readable without changing its behaviour. Prefer clarity over cleverness. Add a one-line docstring if missing.\n\n```python\n{code}\n```",
                model="claude-sonnet-4-6",
                category="coding",
                task_type="refactor",
                effectiveness=3,
                tags="refactor,readability,python",
                notes="Lower effectiveness — sometimes over-abstracts. Update after testing.",
                token_count=100,
            ),
        ]

        for prompt_data in samples:
            repo.create(prompt_data)

        print(f"Seeded {len(samples)} prompts successfully.")


if __name__ == "__main__":
    seed_prompts()
