import uuid

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey,
    Integer, String, Text, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


def uuid_pk():
    return Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def now_col():
    return Column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = "users"
    id = uuid_pk()
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="owner")
    created_at = now_col()
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = uuid_pk()
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = now_col()


class Session(Base):
    __tablename__ = "sessions"
    id = uuid_pk()
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    started_at = now_col()
    ended_at = Column(DateTime(timezone=True), nullable=True)
    surface = Column(String, nullable=False)


class Conversation(Base):
    __tablename__ = "conversations"
    id = uuid_pk()
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = now_col()
    messages = relationship("Message", back_populates="conversation")


class Message(Base):
    __tablename__ = "messages"
    id = uuid_pk()
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    tool_call_id = Column(String, nullable=True)
    created_at = now_col()
    conversation = relationship("Conversation", back_populates="messages")


class Memory(Base):
    __tablename__ = "memory"
    id = uuid_pk()
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    key = Column(String, nullable=False)
    value = Column(JSON, nullable=False)
    category = Column(String, nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class ToolCall(Base):
    __tablename__ = "tool_calls"
    id = uuid_pk()
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=True)
    tool_name = Column(String, nullable=False)
    inputs = Column(JSON, nullable=False)
    outputs = Column(JSON, nullable=True)
    status = Column(String, nullable=False)
    confirmed = Column(Boolean, default=False)
    duration_ms = Column(Integer, nullable=True)
    created_at = now_col()


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = uuid_pk()
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    resource_type = Column(String, nullable=True)
    resource_id = Column(String, nullable=True)
    meta = Column(JSON, nullable=True)
    ip_address = Column(String, nullable=True)
    created_at = now_col()


class Lead(Base):
    __tablename__ = "leads"
    id = uuid_pk()
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    message = Column(Text, nullable=True)
    source = Column(String, nullable=True)
    status = Column(String, default="new")
    classification = Column(String, nullable=True)
    meta = Column(JSON, nullable=True)
    created_at = now_col()
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class Appointment(Base):
    __tablename__ = "appointments"
    id = uuid_pk()
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, default="pending")
    notes = Column(Text, nullable=True)
    created_at = now_col()


class ContentItem(Base):
    __tablename__ = "content_items"
    id = uuid_pk()
    slug = Column(String, unique=True, nullable=False)
    type = Column(String, nullable=False)
    title = Column(String, nullable=True)
    body = Column(JSON, nullable=False)
    published = Column(Boolean, default=False)
    created_at = now_col()
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    versions = relationship("ContentVersion", back_populates="content_item")


class ContentVersion(Base):
    __tablename__ = "content_versions"
    id = uuid_pk()
    content_id = Column(UUID(as_uuid=True), ForeignKey("content_items.id"), nullable=False)
    version = Column(Integer, nullable=False)
    body = Column(JSON, nullable=False)
    published = Column(Boolean, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = now_col()
    content_item = relationship("ContentItem", back_populates="versions")


class DeployEvent(Base):
    __tablename__ = "deploy_events"
    id = uuid_pk()
    trigger = Column(String, nullable=False)
    triggered_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    provider = Column(String, nullable=False)
    status = Column(String, nullable=False)
    commit_sha = Column(String, nullable=True)
    deploy_url = Column(String, nullable=True)
    logs = Column(Text, nullable=True)
    started_at = now_col()
    completed_at = Column(DateTime(timezone=True), nullable=True)


class RollbackEvent(Base):
    __tablename__ = "rollback_events"
    id = uuid_pk()
    deploy_event_id = Column(UUID(as_uuid=True), ForeignKey("deploy_events.id"), nullable=False)
    rolled_back_to = Column(UUID(as_uuid=True), ForeignKey("deploy_events.id"), nullable=True)
    triggered_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    confirmed = Column(Boolean, default=False)
    reason = Column(Text, nullable=True)
    status = Column(String, nullable=False)
    created_at = now_col()


class Notification(Base):
    __tablename__ = "notifications"
    id = uuid_pk()
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    type = Column(String, nullable=False)
    channel = Column(String, nullable=True)
    subject = Column(String, nullable=True)
    body = Column(Text, nullable=False)
    status = Column(String, default="pending")
    meta = Column(JSON, nullable=True)
    created_at = now_col()
    sent_at = Column(DateTime(timezone=True), nullable=True)


class HealthCheck(Base):
    __tablename__ = "health_checks"
    id = uuid_pk()
    url = Column(String, nullable=False)
    status_code = Column(Integer, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    ssl_expiry_days = Column(Integer, nullable=True)
    is_up = Column(Boolean, nullable=False)
    error_message = Column(Text, nullable=True)
    checked_at = now_col()