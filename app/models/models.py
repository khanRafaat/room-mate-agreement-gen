"""
Roommate Agreement Generator - SQLAlchemy Models
Compatible with MySQL database
"""
import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, String, Text, Boolean, Integer, BigInteger,
    Date, DateTime, ForeignKey, LargeBinary, JSON
)
from sqlalchemy.orm import relationship

from app.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class AppUser(Base):
    """User accounts linked to Azure AD B2C."""
    __tablename__ = "app_user"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    b2c_sub = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    id_verifications = relationship("IdVerification", back_populates="user")
    file_assets = relationship("FileAsset", back_populates="owner")
    agreements = relationship("Agreement", back_populates="initiator")
    notifications = relationship("Notification", back_populates="user")


class IdVerification(Base):
    """ID verification records - stores only minimal metadata."""
    __tablename__ = "id_verification"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("app_user.id"), nullable=False)
    provider = Column(String(50), nullable=False)  # 'idme', 'onfido', 'persona'
    status = Column(String(50), nullable=False, default="pending")  # 'pending', 'approved', 'rejected'
    reference_id = Column(String(255), nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("AppUser", back_populates="id_verifications")


class FileAsset(Base):
    """Blob storage file references."""
    __tablename__ = "file_asset"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    owner_id = Column(String(36), ForeignKey("app_user.id"), nullable=False)
    kind = Column(String(50), nullable=False)  # 'lease_first_page', 'govt_id', 'agreement_pdf', 'signed_pdf'
    container = Column(String(100), nullable=False)
    blob_name = Column(String(500), nullable=False)
    sha256 = Column(LargeBinary, nullable=True)
    size_bytes = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    owner = relationship("AppUser", back_populates="file_assets")


class Agreement(Base):
    """Main agreement entity."""
    __tablename__ = "agreement"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    initiator_id = Column(String(36), ForeignKey("app_user.id"), nullable=False)
    title = Column(String(255), default="Roommate Agreement")
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(100), nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    rent_total_cents = Column(Integer, nullable=False)
    status = Column(String(50), default="draft")  # 'draft', 'awaiting_payment', 'inviting', 'signing', 'completed', 'void'
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    initiator = relationship("AppUser", back_populates="agreements")
    parties = relationship("AgreementParty", back_populates="agreement", cascade="all, delete-orphan")
    terms = relationship("AgreementTerms", back_populates="agreement", uselist=False, cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="agreement", cascade="all, delete-orphan")
    envelopes = relationship("SignatureEnvelope", back_populates="agreement", cascade="all, delete-orphan")


class AgreementParty(Base):
    """Roommates/participants in an agreement."""
    __tablename__ = "agreement_party"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    agreement_id = Column(String(36), ForeignKey("agreement.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("app_user.id"), nullable=True)
    role = Column(String(50), nullable=False)  # 'initiator', 'roommate'
    email = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    rent_share_cents = Column(Integer, nullable=True)
    utilities = Column(JSON, nullable=True)  # {"electricity": 50, "internet": 50, ...}
    chores = Column(JSON, nullable=True)
    signed = Column(Boolean, default=False)
    signed_at = Column(DateTime, nullable=True)
    
    # Relationships
    agreement = relationship("Agreement", back_populates="parties")


class AgreementTerms(Base):
    """Agreement terms - quiet hours, rules, deposit, etc."""
    __tablename__ = "agreement_terms"
    
    agreement_id = Column(String(36), ForeignKey("agreement.id", ondelete="CASCADE"), primary_key=True)
    quiet_hours = Column(JSON, nullable=True)  # {"start": "22:00", "end": "07:00"}
    guest_rules = Column(JSON, nullable=True)  # {"max_consecutive_nights": 3, "notice_hours": 24}
    pet_rules = Column(JSON, nullable=True)  # {"allowed": true, "notes": "small dog"}
    deposit_cents = Column(Integer, nullable=True)
    deposit_forfeit_reasons = Column(JSON, nullable=True)  # Array stored as JSON
    additional_rules = Column(Text, nullable=True)
    no_offensive_clause_ack = Column(Boolean, default=False)
    
    # Relationships
    agreement = relationship("Agreement", back_populates="terms")


class Payment(Base):
    """Payment records for agreements."""
    __tablename__ = "payment"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    agreement_id = Column(String(36), ForeignKey("agreement.id", ondelete="CASCADE"), nullable=False)
    method = Column(String(50), nullable=False)  # 'solana', 'card'
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String(10), default="USD")
    status = Column(String(50), default="pending")  # 'pending', 'succeeded', 'failed', 'refunded'
    provider_ref = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    agreement = relationship("Agreement", back_populates="payments")


class SignatureEnvelope(Base):
    """DocuSign envelope tracking."""
    __tablename__ = "signature_envelope"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    agreement_id = Column(String(36), ForeignKey("agreement.id", ondelete="CASCADE"), nullable=False)
    docusign_envelope_id = Column(String(255), nullable=True)
    status = Column(String(50), nullable=True)  # 'sent', 'completed', 'voided'
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    agreement = relationship("Agreement", back_populates="envelopes")


class Notification(Base):
    """Sent notifications log."""
    __tablename__ = "notification"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("app_user.id"), nullable=False)
    channel = Column(String(20), nullable=False)  # 'email', 'sms'
    template = Column(String(100), nullable=True)
    payload = Column(JSON, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("AppUser", back_populates="notifications")


class AuditLog(Base):
    """Audit trail for security and compliance."""
    __tablename__ = "audit_log"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    actor_user_id = Column(String(36), nullable=True)
    action = Column(String(100), nullable=False)
    target = Column(String(255), nullable=True)
    meta = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
