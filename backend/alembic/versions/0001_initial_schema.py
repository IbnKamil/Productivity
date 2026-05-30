"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-30
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

role = sa.Enum("user", "admin", "operator", name="role")
goal_status = sa.Enum("active", "paused", "completed", "archived", name="goalstatus")
task_status = sa.Enum("pending", "current", "completed", "skipped", "paused", name="taskstatus")
session_status = sa.Enum("active", "paused", "ended", name="sessionstatus")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(512), nullable=False),
        sa.Column("role", role, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "user_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("display_name", sa.String(120)),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("energy_mode", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_user_profiles_user_id", "user_profiles", ["user_id"])

    op.create_table(
        "goals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("due_date", sa.Date()),
        sa.Column("complexity", sa.Integer(), nullable=False),
        sa.Column("context", sa.Text()),
        sa.Column("status", goal_status, nullable=False),
        sa.Column("current_task_id", sa.String(36)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_goals_user_id", "goals", ["user_id"])
    op.create_index("ix_goals_status", "goals", ["status"])
    op.create_index("ix_goals_current_task_id", "goals", ["current_task_id"])
    op.create_index("ix_goals_completed_at", "goals", ["completed_at"])

    op.create_table(
        "micro_tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("goal_id", sa.String(36), sa.ForeignKey("goals.id", ondelete="CASCADE")),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("parent_task_id", sa.String(36), sa.ForeignKey("micro_tasks.id", ondelete="SET NULL")),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("estimated_seconds", sa.Integer(), nullable=False),
        sa.Column("difficulty_score", sa.Integer(), nullable=False),
        sa.Column("value_score", sa.Integer(), nullable=False),
        sa.Column("clarity_score", sa.Integer(), nullable=False),
        sa.Column("energy_fit_score", sa.Integer(), nullable=False),
        sa.Column("momentum_score", sa.Integer(), nullable=False),
        sa.Column("status", task_status, nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("goal_id", "order_index", name="uq_micro_tasks_goal_order"),
    )
    op.create_index("ix_micro_tasks_user_id", "micro_tasks", ["user_id"])
    op.create_index("ix_micro_tasks_goal_id", "micro_tasks", ["goal_id"])
    op.create_index("ix_micro_tasks_status", "micro_tasks", ["status"])
    op.create_index("ix_micro_tasks_completed_at", "micro_tasks", ["completed_at"])
    op.create_index("ix_micro_tasks_goal_status_order", "micro_tasks", ["goal_id", "status", "order_index"])
    op.create_foreign_key("fk_goals_current_task_id", "goals", "micro_tasks", ["current_task_id"], ["id"])

    op.create_table(
        "task_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("goal_id", sa.String(36), sa.ForeignKey("goals.id", ondelete="SET NULL")),
        sa.Column("current_task_id", sa.String(36), sa.ForeignKey("micro_tasks.id", ondelete="SET NULL")),
        sa.Column("status", session_status, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_task_sessions_user_id", "task_sessions", ["user_id"])
    op.create_index("ix_task_sessions_goal_id", "task_sessions", ["goal_id"])
    op.create_index("ix_task_sessions_current_task_id", "task_sessions", ["current_task_id"])
    op.create_index("ix_task_sessions_started_at", "task_sessions", ["started_at"])

    op.create_table(
        "task_completions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("micro_tasks.id", ondelete="CASCADE")),
        sa.Column("goal_id", sa.String(36), sa.ForeignKey("goals.id", ondelete="CASCADE")),
        sa.Column("reward_points", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "task_id", name="uq_task_completion_user_task"),
    )
    op.create_index("ix_task_completions_user_id", "task_completions", ["user_id"])
    op.create_index("ix_task_completions_task_id", "task_completions", ["task_id"])
    op.create_index("ix_task_completions_goal_id", "task_completions", ["goal_id"])
    op.create_index("ix_task_completions_completed_at", "task_completions", ["completed_at"])

    op.create_table(
        "user_stats",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), unique=True),
        sa.Column("completed_tasks", sa.Integer(), nullable=False),
        sa.Column("completed_goals", sa.Integer(), nullable=False),
        sa.Column("reward_points", sa.Integer(), nullable=False),
        sa.Column("streak_days", sa.Integer(), nullable=False),
        sa.Column("last_completion_date", sa.Date()),
        sa.Column("total_focus_seconds", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_user_stats_user_id", "user_stats", ["user_id"])

    op.create_table(
        "events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_events_user_id", "events", ["user_id"])
    op.create_index("ix_events_event_type", "events", ["event_type"])
    op.create_index("ix_events_created_at", "events", ["created_at"])

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("token_id", sa.String(64), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_token_id", "refresh_tokens", ["token_id"], unique=True)
    op.create_index("ix_refresh_tokens_expires_at", "refresh_tokens", ["expires_at"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("request_id", sa.String(64)),
        sa.Column("ip_address", sa.String(64)),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_request_id", "audit_logs", ["request_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    op.create_table(
        "settings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), unique=True),
        sa.Column("energy_mode", sa.String(32), nullable=False),
        sa.Column("task_density", sa.String(32), nullable=False),
        sa.Column("notifications_enabled", sa.Boolean(), nullable=False),
        sa.Column("sounds_enabled", sa.Boolean(), nullable=False),
        sa.Column("theme", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_settings_user_id", "settings", ["user_id"])

    for table in [
        "user_profiles",
        "goals",
        "micro_tasks",
        "task_sessions",
        "task_completions",
        "user_stats",
        "events",
        "refresh_tokens",
        "audit_logs",
        "settings",
    ]:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY {table}_user_isolation ON {table}
            USING (user_id::text = current_setting('app.user_id', true))
            WITH CHECK (user_id::text = current_setting('app.user_id', true))
            """
        )


def downgrade() -> None:
    for table in [
        "settings",
        "audit_logs",
        "refresh_tokens",
        "events",
        "user_stats",
        "task_completions",
        "task_sessions",
        "micro_tasks",
        "goals",
        "user_profiles",
        "users",
    ]:
        op.drop_table(table)
    role.drop(op.get_bind(), checkfirst=True)
    goal_status.drop(op.get_bind(), checkfirst=True)
    task_status.drop(op.get_bind(), checkfirst=True)
    session_status.drop(op.get_bind(), checkfirst=True)
