from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.db.base import Base


class EmailTemplateCategory(str, enum.Enum):
    SERVICE = "service"
    LOGIN = "login"
    NOTIFICATION = "notification"
    FOLLOW_UP = "follow_up"
    REMINDER = "reminder"


class EmailTemplateType(str, enum.Enum):
    GST_FILING = "gst_filing"
    INCOME_TAX_RETURN = "income_tax_return"
    TDS = "tds"
    AUDIT = "audit"
    COMPANY_REGISTRATION = "company_registration"
    TAX_PLANNING = "tax_planning"
    COMPLIANCES = "compliances"
    LOGIN_CREDENTIALS = "login_credentials"
    # Add more types as needed
    OTHER = "other"


class EmailTemplate(Base):
    __tablename__ = "email_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    category = Column(Enum(EmailTemplateCategory, native_enum=False, length=50), nullable=False, index=True)
    type = Column(Enum(EmailTemplateType, native_enum=False, length=50), nullable=False, index=True)
    subject = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    master_template_id = Column(Integer, ForeignKey("email_templates.id", ondelete="SET NULL"), nullable=True, index=True)
    variables = Column(JSON, nullable=True)  # List of available variables like ["client_name", "service_name"]
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Relationships
    organization = relationship("Organization", backref="email_templates")
    master_template = relationship("EmailTemplate", remote_side=[id], backref="customized_templates")
    creator = relationship("User", foreign_keys=[created_by], backref="created_email_templates")

