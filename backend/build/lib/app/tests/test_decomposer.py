from app.services.decomposer import TaskDecomposer


def test_decomposer_outputs_micro_tasks_with_bounds():
    tasks = TaskDecomposer().decompose(
        "Write a launch plan",
        "Collect constraints and draft the first outline",
        complexity=3,
        context="Tired mode, keep it simple",
    )

    assert len(tasks) >= 3
    assert tasks[0].estimated_seconds >= 30
    assert all(30 <= task.estimated_seconds <= 180 for task in tasks)
    assert all(task.order_index == index for index, task in enumerate(tasks))
    assert all(task.clarity_score >= 4 for task in tasks)
