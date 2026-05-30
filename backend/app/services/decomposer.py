from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class DecomposedTask:
    title: str
    description: str
    estimated_seconds: int
    difficulty_score: int
    value_score: int
    clarity_score: int
    energy_fit_score: int
    momentum_score: int
    order_index: int


class TaskDecomposer:
    """Deterministic MVP decomposer that produces immediate, single-action steps."""

    _splitter = re.compile(r"[.;\n]|(?:\s+и\s+)|(?:\s+then\s+)|(?:\s+and\s+)", re.IGNORECASE)

    def decompose(
        self,
        title: str,
        description: str | None,
        complexity: int,
        context: str | None = None,
    ) -> list[DecomposedTask]:
        text = " ".join(part for part in [title, description, context] if part)
        fragments = [self._clean(fragment) for fragment in self._splitter.split(text)]
        fragments = [fragment for fragment in fragments if len(fragment) >= 4]

        if not fragments:
            fragments = [title]

        planned = self._build_sequence(title, fragments, complexity)
        return [
            DecomposedTask(
                title=task_title,
                description=description,
                estimated_seconds=estimated,
                difficulty_score=difficulty,
                value_score=min(5, 3 + (index % 2)),
                clarity_score=5 if len(task_title.split()) <= 9 else 4,
                energy_fit_score=max(1, 5 - difficulty + 1),
                momentum_score=5 if index == 0 else 4,
                order_index=index,
            )
            for index, (task_title, description, estimated, difficulty) in enumerate(planned)
        ]

    def _build_sequence(
        self, title: str, fragments: list[str], complexity: int
    ) -> list[tuple[str, str, int, int]]:
        core = fragments[: max(3, min(8, complexity + 3))]
        steps: list[tuple[str, str, int, int]] = [
            (
                f"Open a clean place for: {self._short(title)}",
                "Prepare the app, document, tool, or workspace needed for the goal. Do not solve anything yet.",
                45,
                1,
            )
        ]

        for fragment in core:
            action = self._as_action(fragment)
            steps.append(
                (
                    self._short(action),
                    f"Do only this one action: {action}. Stop after this small step.",
                    self._estimate_seconds(action, complexity),
                    min(5, max(1, complexity - 1)),
                )
            )

        steps.append(
            (
                "Mark the next visible checkpoint",
                "Write one sentence about what changed and get ready for the next micro-step.",
                60,
                1,
            )
        )
        return steps[:10]

    @staticmethod
    def _clean(value: str) -> str:
        return re.sub(r"\s+", " ", value.strip(" -:,."))

    @staticmethod
    def _short(value: str, limit: int = 96) -> str:
        if len(value) <= limit:
            return value
        return value[: limit - 1].rstrip() + "..."

    @staticmethod
    def _as_action(fragment: str) -> str:
        lower = fragment.lower()
        if lower.startswith(("open ", "write ", "create ", "check ", "choose ", "read ", "send ")):
            return fragment
        return f"Write down the smallest next step for: {fragment}"

    @staticmethod
    def _estimate_seconds(action: str, complexity: int) -> int:
        base = 45 + min(90, len(action.split()) * 5)
        return max(30, min(180, base + complexity * 10))
