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
