from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class UploadFile(Base):
    __tablename__ = "upload_files"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(500), nullable=False)  # Original filename
    stored_filename = Column(String(500), nullable=False, unique=True, index=True)  # Unique filename on server
    file_type = Column(String(100), nullable=False)  # MIME type
    file_size = Column(Integer, nullable=False)  # File size in bytes
    file_path = Column(String(1000), nullable=False)  # Full storage path
    url = Column(String(1000), nullable=False)  # Access URL
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", backref="uploaded_files")
    organization = relationship("Organization", backref="uploaded_files")

