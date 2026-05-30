from app.core.database import SessionLocal
from app.models import Goal
from app.services.tasks import generate_for_goal


def generate_goal_tasks(goal_id: str) -> int:
    """Worker-friendly task decomposer entrypoint for RQ/Celery integration."""
    with SessionLocal() as db:
        goal = db.get(Goal, goal_id)
        if not goal:
            return 0
        result = generate_for_goal(db, goal)
        db.commit()
        return result.generated_count
