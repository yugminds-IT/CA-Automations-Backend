from sqlalchemy import Column, Integer, String, Boolean, Text, JSON, DateTime, Date, Time, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.db.base import Base


class ScheduledEmailStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ClientEmailConfig(Base):
    __tablename__ = "client_email_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True, unique=True)
    config_data = Column(JSON, nullable=False)  # Stores the full config object
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    client = relationship("Client", backref="email_config")


class ScheduledEmail(Base):
    __tablename__ = "scheduled_emails"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    template_id = Column(Integer, ForeignKey("email_templates.id", ondelete="SET NULL"), nullable=True, index=True)
    recipient_emails = Column(JSON, nullable=False)  # Array of email addresses
    scheduled_date = Column(Date, nullable=False, index=True)  # Date component
    scheduled_time = Column(Time, nullable=False)  # Time component
    scheduled_datetime = Column(DateTime, nullable=False, index=True)  # Combined datetime for querying
    status = Column(String(20), nullable=False, default="pending", index=True)  # pending, sent, failed, cancelled
    is_recurring = Column(Boolean, nullable=False, default=False, index=True)
    recurrence_end_date = Column(Date, nullable=True)  # End date for recurring emails
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    client = relationship("Client", backref="scheduled_emails")
    template = relationship("EmailTemplate", backref="scheduled_emails")
