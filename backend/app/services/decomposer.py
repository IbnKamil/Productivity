from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Literal

import httpx
import structlog

from app.core.config import get_settings
from app.services.research import GoalResearcher, ResearchContext

logger = structlog.get_logger()
GoalKind = Literal["book_reading", "sport_habit", "student_project", "learning", "generic"]


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
    """Context-aware micro-task generator with optional web research.

    Generation now has three stages:
    1. classify the user's goal type;
    2. collect external context when configured;
    3. ask an AI model with that context or use a domain-specific local fallback.
    """

    _splitter = re.compile(r"[.;!?\n]+|(?:\s+и\s+)|(?:\s+затем\s+)|(?:\s+потом\s+)", re.IGNORECASE)
    _json_object = re.compile(r"\{.*\}", re.DOTALL)

    def __init__(self, researcher: GoalResearcher | None = None) -> None:
        self.researcher = researcher or GoalResearcher()

    def decompose(
        self,
        title: str,
        description: str | None,
        complexity: int,
        context: str | None = None,
    ) -> list[DecomposedTask]:
        settings = get_settings()
        goal_kind = self._classify_goal(title, description, context)
        target_count = self._target_count(title, description, complexity, context, goal_kind)
        research = self.researcher.research(title, description, context)

        if settings.task_decomposer_mode in {"auto", "ai"} and settings.openai_api_key:
            try:
                tasks = self._decompose_with_ai(
                    title=title,
                    description=description,
                    complexity=complexity,
                    context=context,
                    target_count=target_count,
                    goal_kind=goal_kind,
                    research=research,
                )
                if self._has_enough_specificity(tasks, target_count):
                    return self._normalize_order(tasks[: settings.max_micro_tasks])
                logger.warning("decomposer.ai_too_generic", count=len(tasks), target_count=target_count)
            except Exception as exc:  # noqa: BLE001 - in auto mode generation must degrade gracefully.
                logger.warning("decomposer.ai_failed", error=str(exc))
                if settings.task_decomposer_mode == "ai":
                    raise

        return self._decompose_locally(title, description, complexity, context, target_count, goal_kind, research)

    def _decompose_with_ai(
        self,
        title: str,
        description: str | None,
        complexity: int,
        context: str | None,
        target_count: int,
        goal_kind: GoalKind,
        research: ResearchContext,
    ) -> list[DecomposedTask]:
        settings = get_settings()
        url = f"{settings.openai_base_url.rstrip('/')}/chat/completions"
        prompt = self._ai_prompt(title, description, complexity, context, target_count, goal_kind, research)
        response = httpx.post(
            url,
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={
                "model": settings.openai_model,
                "temperature": 0.15,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Ты исследовательский AI-декомпозер целей. Сначала понимаешь предмет цели, "
                            "используешь предоставленный web-контекст, затем создаёшь адаптивные микро-задачи "
                            "по 30-180 секунд. Нельзя выдавать универсальный шаблон. Отвечай только JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=60,
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
        goal_kind: GoalKind,
        research: ResearchContext,
    ) -> str:
        playbook = self._playbook(goal_kind)
        return f"""
Создай адаптивную цепочку микро-задач для цели пользователя.

Цель: {title}
Описание пользователя: {description or 'не указано'}
Контекст выполнения: {context or 'не указан'}
Тип цели: {goal_kind}
Сложность от 1 до 5: {complexity}
Целевое количество микро-задач: {target_count}

Исследовательский контекст:
{research.to_prompt_text()}

Правила качества:
- каждая микро-задача занимает 30-180 секунд;
- одна задача = одно конкретное действие;
- текст на русском языке;
- задачи должны быть предметными, а не шаблонными;
- если источники не дают точных страниц/оглавления, не выдумывай их: создай задачи, где пользователь сам открывает оглавление/абзац/раздел и фиксирует смысл;
- если источники дали темы, авторов, главы или структуру — используй их в формулировках;
- первые 3-5 задач должны снижать барьер старта;
- будущие задачи будут скрыты интерфейсом, но внутренний план должен быть полным;
- не объединяй независимые действия через "и";
- не используй пустые формулировки вроде "проработать вопрос", "заняться темой", "сделать шаг".

Сценарные правила:
{playbook}

Верни строго JSON:
{{
  "goal_type": "{goal_kind}",
  "assumptions": ["что пришлось предположить, если web-контекста недостаточно"],
  "micro_tasks": [
    {{
      "title": "Конкретное действие",
      "description": "Что сделать и какой маленький результат получить",
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

    def _playbook(self, goal_kind: GoalKind) -> str:
        if goal_kind == "book_reading":
            return """
Для чтения книги:
- начни с открытия книги, поиска оглавления, аннотации, автора и структуры;
- если известны главы/темы, создай задачи по конкретным главам/темам;
- дроби чтение на абзацы, страницы или небольшие смысловые блоки;
- после каждого блока добавляй микро-задачу на понимание: "о чём блок?", "какая полезная мысль?", "что непонятно?";
- чередуй чтение и фиксацию смысла, чтобы пользователь не просто листал текст.
""".strip()
        if goal_kind == "sport_habit":
            return """
Для спортивной привычки:
- начинай с подготовки одежды/воды/места;
- первые действия должны быть меньше 2 минут;
- дроби тренировку на разминку, один подход, короткую проверку самочувствия и отметку прогресса;
- не давай медицинских обещаний; адаптируй нагрузку под низкую энергию.
""".strip()
        if goal_kind == "student_project":
            return """
Для учебного проекта:
- начни с требований, темы, критериев оценки и структуры результата;
- разбей работу на исследование, план, черновик, проверку, оформление;
- каждая задача должна создавать проверяемый артефакт: строку плана, один источник, один абзац, один слайд.
""".strip()
        if goal_kind == "learning":
            return """
Для изучения темы:
- сначала выясни базовые понятия и карту темы;
- чередуй чтение, пересказ, мини-проверку и практический пример;
- задачи должны вести от понимания слов к применению.
""".strip()
        return """
Для общей цели:
- сначала уточни результат и ограничения;
- затем создай последовательность маленьких действий с видимым результатом;
- добавляй регулярные проверки смысла и прогресса.
""".strip()

    def _decompose_locally(
        self,
        title: str,
        description: str | None,
        complexity: int,
        context: str | None,
        target_count: int,
        goal_kind: GoalKind,
        research: ResearchContext,
    ) -> list[DecomposedTask]:
        if goal_kind == "book_reading":
            raw_steps = self._book_steps(title, target_count, research)
        elif goal_kind == "sport_habit":
            raw_steps = self._sport_steps(title, target_count)
        elif goal_kind == "student_project":
            raw_steps = self._project_steps(title, description, target_count, research)
        elif goal_kind == "learning":
            raw_steps = self._learning_steps(title, target_count, research)
        else:
            raw_steps = self._generic_steps(title, description, context, target_count)

        tasks = [
            DecomposedTask(
                title=self._short(title_item, 120),
                description=self._short(description_item, 420),
                estimated_seconds=max(30, min(180, seconds)),
                difficulty_score=self._score_difficulty(index, complexity),
                value_score=5 if index in {0, len(raw_steps) - 1} else min(5, 3 + complexity // 2),
                clarity_score=5 if len(title_item.split()) <= 12 else 4,
                energy_fit_score=max(1, 5 - self._score_difficulty(index, complexity) + 1),
                momentum_score=5 if index < 4 else 4,
                order_index=index,
            )
            for index, (title_item, description_item, seconds) in enumerate(raw_steps[:target_count])
        ]
        return self._normalize_order(tasks)

    def _book_steps(self, title: str, target_count: int, research: ResearchContext) -> list[tuple[str, str, int]]:
        book_title = GoalResearcher.extract_quoted_title(title) or self._remove_goal_words(title)
        topics = research.topics[:8]
        source_hint = research.sources[0].title if research.sources else None
        steps: list[tuple[str, str, int]] = [
            (f"Открыть книгу «{book_title}»", "Открой бумажную или электронную версию книги и остановись на первой странице доступа к содержанию.", 45),
            (f"Найти аннотацию книги «{book_title}»", "Прочитай аннотацию или описание книги и сформулируй одной фразой, зачем ты её читаешь.", 120),
            (f"Открыть оглавление книги «{book_title}»", "Перейди к оглавлению и посмотри, из каких крупных частей состоит книга.", 60),
            ("Записать первую видимую главу", "Выпиши название первой главы или первого раздела без анализа всего списка.", 60),
        ]
        if source_hint:
            steps.insert(1, ("Сверить найденную справку о книге", f"Используй подсказку из источника: {source_hint}. Проверь, совпадает ли она с твоей книгой.", 90))
        if topics:
            steps.append(("Отметить ключевые темы книги", f"Запиши 2-3 темы, на которые стоит обращать внимание: {', '.join(topics[:5])}.", 90))

        paragraph = 1
        page = 1
        while len(steps) < target_count:
            steps.extend(
                [
                    (f"Прочитать абзац {paragraph} текущего раздела", f"Прочитай только абзац {paragraph}. Не переходи к следующему заданию, пока не закончишь этот абзац.", 90),
                    (f"Понять смысл абзаца {paragraph}", f"Ответь одним предложением: о чём абзац {paragraph} и есть ли в нём полезная информация для цели чтения?", 75),
                    (f"Выписать одну мысль из абзаца {paragraph}", f"Если мысль полезна, запиши её коротко. Если нет — отметь «пропустить» и двигайся дальше.", 60),
                ]
            )
            paragraph += 1
            if paragraph % 5 == 0:
                steps.append((f"Проверить понимание страницы {page}", f"Сформулируй, что стало понятнее после прочитанных абзацев на странице {page}.", 90))
                page += 1
        return steps

    def _sport_steps(self, title: str, target_count: int) -> list[tuple[str, str, int]]:
        habit = self._remove_goal_words(title)
        base = [
            (f"Назвать минимальную версию привычки: {habit}", "Запиши действие, которое можно выполнить даже в день с низкой энергией.", 60),
            ("Подготовить место", "Освободи маленькое пространство или выбери безопасную точку для движения.", 45),
            ("Подготовить воду", "Поставь воду рядом, чтобы не отвлекаться во время подхода.", 30),
            ("Сделать 30 секунд лёгкой разминки", "Разомни шею, плечи или стопы без рывков и без цели устать.", 45),
        ]
        cycle = [
            ("Сделать один лёгкий подход", "Выполни минимальный подход выбранного упражнения или движения.", 90),
            ("Оценить самочувствие", "Проверь дыхание и напряжение по шкале 1-5.", 45),
            ("Отметить маленькую победу", "Запиши, что именно ты сделал сегодня.", 45),
            ("Выбрать следующий безопасный шаг", "Реши: повторить лёгкий подход или завершить без перегруза.", 45),
        ]
        return self._repeat_to_count(base, cycle, target_count)

    def _project_steps(
        self, title: str, description: str | None, target_count: int, research: ResearchContext
    ) -> list[tuple[str, str, int]]:
        project = self._remove_goal_words(title)
        topics = research.topics[:6]
        base = [
            (f"Открыть файл проекта: {project}", "Создай или открой документ, где будет собираться проект.", 45),
            ("Записать конечный результат проекта", "Одной фразой опиши, что должно быть сдано или показано.", 60),
            ("Записать критерий оценки", "Найди в задании один критерий оценки и выпиши его.", 90),
            ("Составить черновой план из 3 пунктов", "Запиши только три крупных блока: исследование, создание, проверка.", 120),
        ]
        if description:
            base.append(("Выделить требование из описания", f"Из этого описания выпиши одно конкретное требование: {self._short(description, 180)}", 90))
        if topics:
            base.append(("Выбрать исследовательскую тему", f"Выбери одну тему для первого поиска: {', '.join(topics[:4])}.", 90))
        cycle = [
            ("Найти один источник", "Найди один источник по текущему блоку и сохрани ссылку или название.", 120),
            ("Выписать один факт из источника", "Запиши один факт, который можно использовать в проекте.", 90),
            ("Написать один абзац черновика", "Напиши 2-3 предложения только для текущего блока.", 150),
            ("Проверить один абзац", "Проверь, отвечает ли абзац требованию проекта.", 75),
        ]
        return self._repeat_to_count(base, cycle, target_count)

    def _learning_steps(self, title: str, target_count: int, research: ResearchContext) -> list[tuple[str, str, int]]:
        subject = self._remove_goal_words(title)
        topics = research.topics[:8] or [subject]
        base = [
            (f"Открыть заметку по теме: {subject}", "Создай место, куда будешь складывать определения, примеры и вопросы.", 45),
            ("Записать, зачем изучать тему", "Одной фразой напиши практическую причину изучения.", 60),
            ("Выбрать первый термин", f"Выбери один термин из списка тем: {', '.join(topics[:5])}.", 60),
        ]
        cycle = [
            ("Прочитать одно объяснение термина", "Прочитай короткое объяснение выбранного термина.", 120),
            ("Пересказать термин своими словами", "Запиши объяснение так, будто рассказываешь другу.", 90),
            ("Придумать маленький пример", "Придумай один простой пример применения термина.", 90),
            ("Отметить вопрос", "Запиши один вопрос, который остался непонятным.", 45),
        ]
        return self._repeat_to_count(base, cycle, target_count)

    def _generic_steps(
        self, title: str, description: str | None, context: str | None, target_count: int
    ) -> list[tuple[str, str, int]]:
        fragments = self._extract_fragments(title, description, context)
        base = [
            (f"Открыть рабочее место для цели: {self._short(title, 70)}", "Подготовь документ, приложение или место, где будет выполняться цель.", 45),
            ("Записать конечный результат", "Одним предложением опиши, что должно измениться после выполнения цели.", 60),
            ("Выбрать первый фрагмент", f"Выбери самый простой фрагмент из списка: {self._short('; '.join(fragments[:4]), 180)}.", 60),
        ]
        cycle = []
        for fragment in fragments:
            cycle.extend(
                [
                    (f"Сделать действие по пункту: {self._short(fragment, 55)}", f"Выполни только один короткий шаг по пункту «{fragment}».", 90),
                    (f"Проверить пункт: {self._short(fragment, 60)}", "Ответь: стало ли состояние цели лучше после этого шага?", 60),
                ]
            )
        return self._repeat_to_count(base, cycle or base, target_count)

    def _repeat_to_count(
        self, base: list[tuple[str, str, int]], cycle: list[tuple[str, str, int]], target_count: int
    ) -> list[tuple[str, str, int]]:
        steps = list(base)
        index = 0
        while len(steps) < target_count:
            title, description, seconds = cycle[index % len(cycle)]
            round_number = index // len(cycle) + 1
            if round_number > 1:
                title = f"{title} — подход {round_number}"
            steps.append((title, description, seconds))
            index += 1
        return steps[:target_count]

    def _extract_fragments(self, title: str, description: str | None, context: str | None) -> list[str]:
        text = " ".join(part for part in [title, description, context] if part)
        fragments = [self._clean(fragment) for fragment in self._splitter.split(text)]
        fragments = [fragment for fragment in fragments if len(fragment) >= 4]
        return fragments or [title]

    def _target_count(
        self, title: str, description: str | None, complexity: int, context: str | None, goal_kind: GoalKind
    ) -> int:
        settings = get_settings()
        text = " ".join(part for part in [title, description, context] if part)
        words = len(re.findall(r"\w+", text, flags=re.UNICODE))
        sentence_count = max(1, len([item for item in re.split(r"[.!?;\n]+", text) if item.strip()]))
        kind_bonus = {
            "book_reading": 24,
            "sport_habit": 10,
            "student_project": 20,
            "learning": 16,
            "generic": 8,
        }[goal_kind]
        estimated = kind_bonus + complexity * 6 + words // 6 + sentence_count * 2
        if words > 180 or sentence_count > 18:
            estimated += min(60, words // 5)
        return max(settings.min_micro_tasks, min(settings.max_micro_tasks, estimated))

    def _classify_goal(self, title: str, description: str | None, context: str | None) -> GoalKind:
        text = " ".join(part for part in [title, description, context] if part).lower()
        if re.search(r"\b(книг|прочита|читать|роман|учебник|абзац|глава|book|read)\w*", text):
            return "book_reading"
        if re.search(r"\b(спорт|трениров|бег|зал|отжим|присед|йога|зарядк|привычк|fitness|workout)\w*", text):
            return "sport_habit"
        if re.search(r"\b(проект|курсов|диплом|студен|презентац|исследован|лаборатор|project)\w*", text):
            return "student_project"
        if re.search(r"\b(изуч|выуч|обуч|курс|экзамен|тема|научиться|learn|study)\w*", text):
            return "learning"
        return "generic"

    def _has_enough_specificity(self, tasks: list[DecomposedTask], target_count: int) -> bool:
        if len(tasks) < max(3, min(get_settings().min_micro_tasks, target_count)):
            return False
        generic_markers = ["сделать шаг", "проработать", "заняться", "улучшить", "выполнить задачу"]
        generic_count = 0
        for task in tasks[: min(20, len(tasks))]:
            text = f"{task.title} {task.description}".lower()
            if any(marker in text for marker in generic_markers):
                generic_count += 1
        return generic_count <= max(1, len(tasks[:20]) // 5)

    def _task_from_mapping(self, item: dict[str, Any], index: int) -> DecomposedTask:
        return DecomposedTask(
            title=self._short(str(item.get("title") or f"Микро-задача {index + 1}"), 120),
            description=self._short(str(item.get("description") or "Выполни один короткий конкретный шаг."), 420),
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
        if index < 4:
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
    def _remove_goal_words(value: str) -> str:
        cleaned = re.sub(
            r"\b(прочитать|читать|изучить|сделать|создать|подготовить|запустить|начать|книгу|книга)\b",
            "",
            value,
            flags=re.IGNORECASE,
        )
        return TaskDecomposer._short(cleaned.strip(' «"»') or value, 80)

    @staticmethod
    def _clean(value: str) -> str:
        return re.sub(r"\s+", " ", value.strip(" -:,.")).strip()

    @staticmethod
    def _short(value: str, limit: int = 96) -> str:
        value = re.sub(r"\s+", " ", value.strip())
        if len(value) <= limit:
            return value
        return value[: limit - 1].rstrip() + "..."
