from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import httpx
import structlog

from app.core.config import get_settings

logger = structlog.get_logger()


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
    """Generates Russian micro-tasks, using an AI model when configured.

    The main product invariant stays the same: many steps may be generated, but
    only the current one is exposed by the user-facing current-task endpoint.
    """

    _splitter = re.compile(r"[.;!?\n]+|(?:\s+и\s+)|(?:\s+затем\s+)|(?:\s+потом\s+)", re.IGNORECASE)
    _json_object = re.compile(r"\{.*\}", re.DOTALL)

    def decompose(
        self,
        title: str,
        description: str | None,
        complexity: int,
        context: str | None = None,
    ) -> list[DecomposedTask]:
        settings = get_settings()
        target_count = self._target_count(title, description, complexity, context)

        if settings.task_decomposer_mode in {"auto", "ai"} and settings.openai_api_key:
            try:
                tasks = self._decompose_with_ai(title, description, complexity, context, target_count)
                if len(tasks) >= max(3, min(settings.min_micro_tasks, target_count)):
                    return self._normalize_order(tasks[: settings.max_micro_tasks])
                logger.warning("decomposer.ai_too_few_tasks", count=len(tasks), target_count=target_count)
            except Exception as exc:  # noqa: BLE001 - AI generation must not break goal creation in auto mode.
                logger.warning("decomposer.ai_failed", error=str(exc))
                if settings.task_decomposer_mode == "ai":
                    raise

        return self._decompose_locally(title, description, complexity, context, target_count)

    def _decompose_with_ai(
        self,
        title: str,
        description: str | None,
        complexity: int,
        context: str | None,
        target_count: int,
    ) -> list[DecomposedTask]:
        settings = get_settings()
        url = f"{settings.openai_base_url.rstrip('/')}/chat/completions"
        prompt = self._ai_prompt(title, description, complexity, context, target_count)
        response = httpx.post(
            url,
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={
                "model": settings.openai_model,
                "temperature": 0.25,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Ты продуктовый AI-планировщик. Делишь цели на конкретные микро-задачи "
                            "по 30-180 секунд. Отвечай только валидным JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=45,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        data = self._parse_json(content)
        raw_tasks = data.get("micro_tasks", [])
        return [self._task_from_mapping(item, index) for index, item in enumerate(raw_tasks)]

    def _ai_prompt(
        self,
        title: str,
        description: str | None,
        complexity: int,
        context: str | None,
        target_count: int,
    ) -> str:
        return f"""
Разбей цель пользователя на последовательность микро-задач.

Цель: {title}
Описание: {description or 'не указано'}
Контекст выполнения: {context or 'не указан'}
Сложность от 1 до 5: {complexity}
Нужное количество микро-задач: примерно {target_count}, допустимо от 10 до 150 если цель реально большая.

Правила:
- каждая микро-задача занимает 30-180 секунд;
- одна задача = одно конкретное действие;
- формулировки на русском языке;
- не показывай пользователю будущий список, но сгенерируй полный внутренний план;
- не объединяй независимые действия через "и";
- первые задачи должны помогать начать даже в усталом состоянии;
- порядок должен вести к достижению цели;
- избегай абстрактных фраз вроде "проработать вопрос" без конкретного действия.

Верни строго JSON такого вида:
{{
  "micro_tasks": [
    {{
      "title": "Короткое действие",
      "description": "Что именно сделать за один короткий подход",
      "estimated_seconds": 90,
      "difficulty_score": 1,
      "value_score": 4,
      "clarity_score": 5,
      "energy_fit_score": 4,
      "momentum_score": 5
    }}
  ]
}}
""".strip()

    def _decompose_locally(
        self,
        title: str,
        description: str | None,
        complexity: int,
        context: str | None,
        target_count: int,
    ) -> list[DecomposedTask]:
        fragments = self._extract_fragments(title, description, context)
        phases = self._phase_templates(title, fragments)
        raw_steps: list[tuple[str, str, int]] = []

        for phase_index, phase in enumerate(phases):
            raw_steps.extend(self._micro_steps_for_phase(phase, phase_index))
            if len(raw_steps) >= target_count:
                break

        fragment_index = 0
        while len(raw_steps) < target_count:
            fragment = fragments[fragment_index % len(fragments)]
            raw_steps.append(
                (
                    f"Сделать маленький шаг по пункту: {self._short(fragment, 68)}",
                    f"Выбери один самый простой фрагмент из пункта «{fragment}» и выполни только его.",
                    90,
                )
            )
            fragment_index += 1

        tasks = [
            DecomposedTask(
                title=self._short(title_item, 110),
                description=self._short(description_item, 360),
                estimated_seconds=max(30, min(180, seconds)),
                difficulty_score=self._score_difficulty(index, complexity),
                value_score=5 if index in {0, len(raw_steps) - 1} else min(5, 3 + complexity // 2),
                clarity_score=5 if len(title_item.split()) <= 10 else 4,
                energy_fit_score=max(1, 5 - self._score_difficulty(index, complexity) + 1),
                momentum_score=5 if index < 3 else 4,
                order_index=index,
            )
            for index, (title_item, description_item, seconds) in enumerate(raw_steps[:target_count])
        ]
        return self._normalize_order(tasks)

    def _extract_fragments(self, title: str, description: str | None, context: str | None) -> list[str]:
        text = " ".join(part for part in [title, description, context] if part)
        fragments = [self._clean(fragment) for fragment in self._splitter.split(text)]
        fragments = [fragment for fragment in fragments if len(fragment) >= 4]
        return fragments or [title]

    def _phase_templates(self, title: str, fragments: list[str]) -> list[str]:
        base = [
            f"Подготовить рабочее место для цели: {title}",
            "Зафиксировать конечный результат одним предложением",
            "Уточнить первый видимый критерий готовности",
            "Собрать доступные материалы и ограничения",
        ]
        middle = []
        for fragment in fragments:
            middle.extend(
                [
                    f"Разобрать пункт: {fragment}",
                    f"Сделать первый практический шаг по пункту: {fragment}",
                    f"Проверить результат по пункту: {fragment}",
                ]
            )
        closing = [
            "Сверить выполненное с целью",
            "Записать, что уже продвинулось",
            "Подготовить следующий короткий подход",
            "Отметить завершение текущего этапа",
        ]
        return base + middle + closing

    def _micro_steps_for_phase(self, phase: str, phase_index: int) -> list[tuple[str, str, int]]:
        return [
            (
                f"Открыть этап: {self._short(phase, 72)}",
                f"Открой нужный документ, инструмент или заметку для этапа «{phase}». Пока ничего не усложняй.",
                45,
            ),
            (
                f"Записать один конкретный шаг для этапа",
                f"Одной строкой напиши, какое действие продвинет этап «{phase}» прямо сейчас.",
                60,
            ),
            (
                f"Выполнить минимальное действие по этапу",
                f"Сделай только минимальное действие для этапа «{phase}» и остановись после него.",
                90 + min(60, phase_index * 5),
            ),
        ]

    def _target_count(
        self, title: str, description: str | None, complexity: int, context: str | None
    ) -> int:
        settings = get_settings()
        text = " ".join(part for part in [title, description, context] if part)
        words = len(re.findall(r"\w+", text, flags=re.UNICODE))
        sentence_count = max(1, len([item for item in re.split(r"[.!?;\n]+", text) if item.strip()]))
        # Short goals still get a useful 10-step entry ramp; large descriptions can scale up to 150.
        estimated = 8 + complexity * 6 + words // 6 + sentence_count * 2
        if words > 180 or sentence_count > 18:
            estimated += min(60, words // 5)
        return max(settings.min_micro_tasks, min(settings.max_micro_tasks, estimated))

    def _task_from_mapping(self, item: dict[str, Any], index: int) -> DecomposedTask:
        return DecomposedTask(
            title=self._short(str(item.get("title") or f"Микро-задача {index + 1}"), 110),
            description=self._short(str(item.get("description") or "Выполни один короткий конкретный шаг."), 360),
            estimated_seconds=self._int_between(item.get("estimated_seconds"), 30, 180, 90),
            difficulty_score=self._int_between(item.get("difficulty_score"), 1, 5, 2),
            value_score=self._int_between(item.get("value_score"), 1, 5, 3),
            clarity_score=self._int_between(item.get("clarity_score"), 1, 5, 4),
            energy_fit_score=self._int_between(item.get("energy_fit_score"), 1, 5, 4),
            momentum_score=self._int_between(item.get("momentum_score"), 1, 5, 4),
            order_index=index,
        )

    def _parse_json(self, content: str) -> dict[str, Any]:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            match = self._json_object.search(content)
            if not match:
                raise
            return json.loads(match.group(0))

    def _normalize_order(self, tasks: list[DecomposedTask]) -> list[DecomposedTask]:
        return [
            DecomposedTask(
                title=task.title,
                description=task.description,
                estimated_seconds=task.estimated_seconds,
                difficulty_score=task.difficulty_score,
                value_score=task.value_score,
                clarity_score=task.clarity_score,
                energy_fit_score=task.energy_fit_score,
                momentum_score=task.momentum_score,
                order_index=index,
            )
            for index, task in enumerate(tasks)
        ]

    @staticmethod
    def _score_difficulty(index: int, complexity: int) -> int:
        if index < 3:
            return 1
        return max(1, min(5, complexity))

    @staticmethod
    def _int_between(value: Any, minimum: int, maximum: int, default: int) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = default
        return max(minimum, min(maximum, parsed))

    @staticmethod
    def _clean(value: str) -> str:
        return re.sub(r"\s+", " ", value.strip(" -:,."))

    @staticmethod
    def _short(value: str, limit: int = 96) -> str:
        value = re.sub(r"\s+", " ", value.strip())
        if len(value) <= limit:
            return value
        return value[: limit - 1].rstrip() + "..."
