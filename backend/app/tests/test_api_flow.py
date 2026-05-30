def _register(client):
    response = client.post(
        "/auth/register",
        json={"email": "user@example.com", "password": "password123", "display_name": "User"},
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    return data["tokens"]["access_token"]


def test_goal_to_current_task_completion_flow(client):
    token = _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    create_goal = client.post(
        "/goals",
        headers=headers,
        json={
            "title": "Prepare a weekly report",
            "description": "Open notes. Summarize wins. Send draft.",
            "priority": 4,
            "complexity": 2,
            "context": "I only have low energy.",
        },
    )
    assert create_goal.status_code == 200, create_goal.text
    assert create_goal.json()["data"]["generated"]["generated_count"] >= 3

    current = client.get("/tasks/current", headers=headers)
    assert current.status_code == 200
    current_payload = current.json()["data"]
    assert current_payload["task"] is not None
    first_task_id = current_payload["task"]["id"]

    complete = client.post(f"/tasks/{first_task_id}/complete", headers=headers)
    assert complete.status_code == 200, complete.text
    completion_payload = complete.json()["data"]
    assert completion_payload["reward_points"] > 0
    assert completion_payload["next_task"] is not None
    assert completion_payload["next_task"]["id"] != first_task_id

    stats = client.get("/stats/summary", headers=headers)
    assert stats.status_code == 200
    assert stats.json()["data"]["completed_tasks"] == 1


def test_user_cannot_complete_another_users_task(client):
    token_a = _register(client)
    headers_a = {"Authorization": f"Bearer {token_a}"}
    goal = client.post(
        "/goals",
        headers=headers_a,
        json={"title": "Clean desk", "priority": 3, "complexity": 1},
    ).json()["data"]
    task_id = goal["generated"]["current_task"]["id"]

    response = client.post(
        "/auth/register",
        json={"email": "other@example.com", "password": "password123"},
    )
    token_b = response.json()["data"]["tokens"]["access_token"]

    forbidden = client.post(
        f"/tasks/{task_id}/complete",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert forbidden.status_code == 404
