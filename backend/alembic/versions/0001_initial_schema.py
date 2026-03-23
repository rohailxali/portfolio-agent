"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2025-01-01 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default="owner"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("surface", sa.String(), nullable=False),
    )

    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("conversations.id"), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tool_call_id", sa.String()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "memory",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value", postgresql.JSON(), nullable=False),
        sa.Column("category", sa.String()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "key", name="uq_memory_user_key"),
    )

    op.create_table(
        "tool_calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("conversations.id")),
        sa.Column("tool_name", sa.String(), nullable=False),
        sa.Column("inputs", postgresql.JSON(), nullable=False),
        sa.Column("outputs", postgresql.JSON()),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("confirmed", sa.Boolean(), server_default="false"),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("resource_type", sa.String()),
        sa.Column("resource_id", sa.String()),
        sa.Column("meta", postgresql.JSON()),
        sa.Column("ip_address", sa.String()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("message", sa.Text()),
        sa.Column("source", sa.String()),
        sa.Column("status", sa.String(), server_default="new"),
        sa.Column("classification", sa.String()),
        sa.Column("meta", postgresql.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "appointments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("leads.id")),
        sa.Column("scheduled_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(), server_default="pending"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "content_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(), unique=True, nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("title", sa.String()),
        sa.Column("body", postgresql.JSON(), nullable=False),
        sa.Column("published", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "content_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("content_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("content_items.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("body", postgresql.JSON(), nullable=False),
        sa.Column("published", sa.Boolean()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "deploy_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("trigger", sa.String(), nullable=False),
        sa.Column("triggered_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("commit_sha", sa.String()),
        sa.Column("deploy_url", sa.String()),
        sa.Column("logs", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "rollback_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("deploy_event_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("deploy_events.id"), nullable=False),
        sa.Column("rolled_back_to", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("deploy_events.id")),
        sa.Column("triggered_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=False),
        sa.Column("confirmed", sa.Boolean(), server_default="false"),
        sa.Column("reason", sa.Text()),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("channel", sa.String()),
        sa.Column("subject", sa.String()),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), server_default="pending"),
        sa.Column("meta", postgresql.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "health_checks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("status_code", sa.Integer()),
        sa.Column("response_time_ms", sa.Integer()),
        sa.Column("ssl_expiry_days", sa.Integer()),
        sa.Column("is_up", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text()),
        sa.Column("checked_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # Indexes for common query patterns
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_audit_logs_action",     "audit_logs", ["action"])
    op.create_index("ix_leads_status",          "leads",      ["status"])
    op.create_index("ix_leads_created_at",      "leads",      ["created_at"])
    op.create_index("ix_deploy_events_status",  "deploy_events", ["status"])
    op.create_index("ix_health_checks_checked_at", "health_checks", ["checked_at"])
    op.create_index("ix_messages_conversation", "messages",   ["conversation_id"])


def downgrade() -> None:
    tables = [
        "health_checks", "notifications", "rollback_events", "deploy_events",
        "content_versions", "content_items", "appointments", "leads",
        "audit_logs", "tool_calls", "memory", "messages", "conversations",
        "sessions", "refresh_tokens", "users",
    ]
    for table in tables:
        op.drop_table(table)