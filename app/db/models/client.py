from sqlalchemy import Column, Integer, String, Date, Text, Enum, ForeignKey, Table, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.db.base import Base


class BusinessType(str, enum.Enum):
    INDIVIDUAL = "individual"
    PRIVATE_LIMITED = "private Limited"
    LLP = "LLP"
    PARTNERSHIP = "partnership"


class ClientStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    TERMINATED = "terminated"


class ServiceType(str, enum.Enum):
    INCOME_TAX_FILLING = "income tax filling"
    GST_FILLING = "gst filling"
    TDS_RETURNS = "TDS returns"
    COMPANY_REGISTRATION = "company registration"
    AUDIT_SERVICE = "audit service"
    TAX_PLANNING = "tax planning"
    COMPLIANCES = "compliances"


# Association table for many-to-many relationship between clients and services
client_service_association = Table(
    'client_services',
    Base.metadata,
    Column('client_id', Integer, ForeignKey('clients.id', ondelete='CASCADE'), primary_key=True),
    Column('service_id', Integer, ForeignKey('services.id', ondelete='CASCADE'), primary_key=True)
)


class Client(Base):
    __tablename__ = "clients"
    
    id = Column(Integer, primary_key=True, index=True)
    client_name = Column(String, nullable=False, index=True)
    email = Column(String, nullable=True, index=True)
    phone_number = Column(String, nullable=False, index=True)
    company_name = Column(String, nullable=False, index=True)
    business_type = Column(Enum(BusinessType, native_enum=False, length=50), nullable=False)
    pan_number = Column(String, nullable=True)
    gst_number = Column(String, nullable=True)
    status = Column(Enum(ClientStatus, native_enum=False, length=20), nullable=False, default=ClientStatus.ACTIVE)
    address = Column(Text, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    country = Column(String, nullable=True)
    pin_code = Column(String, nullable=True)
    onboard_date = Column(Date, nullable=False, server_default=func.current_date())
    follow_date = Column(Date, nullable=True)
    additional_notes = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    services = relationship("Service", secondary=client_service_association, backref="clients")
    directors = relationship("Director", back_populates="client", cascade="all, delete-orphan")
    user = relationship("User", backref="client")
    organization = relationship("Organization", backref="clients")


class Director(Base):
    __tablename__ = "directors"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    director_name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    # NOTE: legacy column name kept for backward compatibility
    resignation = Column(String, nullable=True)
    designation = Column(String, nullable=True)
    din = Column(String, nullable=True)
    pan = Column(String, nullable=True)
    aadhaar = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship
    client = relationship("Client", back_populates="directors")

