from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.db.base import Base


class UserRole(str, enum.Enum):
    MASTER_ADMIN = "master_admin"
    ADMIN = "admin"
    EMPLOYEE = "employee"
    CLIENT = "client"


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    encrypted_plain_password = Column(String, nullable=True)  # Encrypted plain password (for client accounts, cleared when password is changed)
    full_name = Column(String, nullable=True)
    phone = Column(String, nullable=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    role = Column(Enum(UserRole, native_enum=False, length=20), nullable=False, default=UserRole.EMPLOYEE, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    organization = relationship("Organization", backref="users")

