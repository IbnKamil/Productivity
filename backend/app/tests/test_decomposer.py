from app.services.decomposer import TaskDecomposer


def test_decomposer_outputs_russian_micro_tasks_with_bounds():
    tasks = TaskDecomposer().decompose(
        "Подготовить запуск продукта",
        "Собрать ограничения. Описать аудиторию. Подготовить план коммуникаций.",
        complexity=3,
        context="У пользователя мало энергии, шаги должны быть простыми",
    )

    assert len(tasks) >= 10
    assert all(30 <= task.estimated_seconds <= 180 for task in tasks)
    assert all(task.order_index == index for index, task in enumerate(tasks))
    assert all(task.clarity_score >= 4 for task in tasks)
    assert any("Открыть" in task.title or "Записать" in task.title for task in tasks)


def test_decomposer_scales_for_large_goal_description():
    description = ". ".join(f"Этап {index}: подготовить отдельный блок работы" for index in range(40))
    tasks = TaskDecomposer().decompose(
        "Запустить большой образовательный курс",
        description,
        complexity=5,
        context="Нужен подробный пошаговый план",
    )

    assert 50 <= len(tasks) <= 150


def test_book_goal_gets_reading_specific_micro_tasks():
    tasks = TaskDecomposer().decompose(
        'Прочитать книгу "Как учится машина"',
        'Хочу понять главные идеи книги и не бросить чтение.',
        complexity=3,
        context='Нужно читать маленькими шагами и проверять понимание',
    )

    titles = [task.title for task in tasks[:12]]
    descriptions = [task.description for task in tasks[:12]]
    assert any('Открыть книгу' in title for title in titles)
    assert any('оглавление' in title.lower() or 'оглавлению' in description.lower() for title, description in zip(titles, descriptions))
    assert any('Прочитать абзац 1' in title for title in titles)
    assert any('Понять смысл абзаца 1' in title for title in titles)


def test_goal_classifier_uses_domain_specific_sport_steps():
    tasks = TaskDecomposer().decompose(
        'Сформировать спортивную привычку',
        'Хочу начать делать лёгкую тренировку утром.',
        complexity=2,
        context='Низкая энергия',
    )

    assert any('размин' in task.title.lower() or 'размин' in task.description.lower() for task in tasks[:8])
    assert any('самочувствие' in task.title.lower() for task in tasks[:12])
