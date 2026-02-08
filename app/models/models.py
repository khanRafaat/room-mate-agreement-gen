"""
Roommate Agreement Generator - SQLAlchemy Models
Compatible with MySQL database
"""
import uuid
import secrets
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy import (
    Column, String, Text, Boolean, Integer, BigInteger,
    Date, DateTime, ForeignKey, LargeBinary, JSON
)
from sqlalchemy.orm import relationship

from app.database import Base


def generate_uuid():
    return str(uuid.uuid4())


def generate_invite_token():
    return secrets.token_urlsafe(32)


class AppUser(Base):
    """User accounts with local authentication."""
    __tablename__ = "app_user"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    b2c_sub = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=True)  # For local auth
    name = Column(String(255), nullable=True)  # Display name
    phone = Column(String(50), nullable=True)
    is_verified = Column(Boolean, default=False)  # ID.me verification status
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    id_verifications = relationship("IdVerification", back_populates="user")
    file_assets = relationship("FileAsset", back_populates="owner")
    agreements = relationship("Agreement", back_populates="initiator")
    notifications = relationship("Notification", back_populates="user")
    feedback_given = relationship("Feedback", foreign_keys="Feedback.from_user_id", back_populates="from_user")
    feedback_received = relationship("Feedback", foreign_keys="Feedback.to_user_id", back_populates="to_user")


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


class Country(Base):
    """Countries worldwide for agreement location selection."""
    __tablename__ = "country"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    code = Column(String(3), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    states = relationship("State", back_populates="country", cascade="all, delete-orphan")


class State(Base):
    """States/Provinces/Divisions within a country."""
    __tablename__ = "state"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    country_id = Column(String(36), ForeignKey("country.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(10), nullable=True)
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    country = relationship("Country", back_populates="states")
    cities = relationship("City", back_populates="state", cascade="all, delete-orphan")


class City(Base):
    """Cities within a state."""
    __tablename__ = "city"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    state_id = Column(String(36), ForeignKey("state.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    state = relationship("State", back_populates="cities")
    base_agreements = relationship("BaseAgreement", back_populates="city", cascade="all, delete-orphan")


class BaseAgreement(Base):
    """City-specific base agreement templates (20-30 pages)."""
    __tablename__ = "base_agreement"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    city_id = Column(String(36), ForeignKey("city.id", ondelete="SET NULL"), nullable=True)  # Now nullable for custom cities
    city_name = Column(String(100), nullable=True)  # Free-form city name when not using FK
    title = Column(String(255), nullable=False)
    version = Column(String(20), default="1.0.0")
    content = Column(Text, nullable=True)  # Large text content for agreement
    applicable_for = Column(String(50), default="both")  # 'landlord', 'tenant', 'both'
    is_active = Column(Boolean, default=True)
    effective_date = Column(Date, nullable=True)
    
    # PDF file storage (Azure Blob)
    pdf_container = Column(String(100), nullable=True)  # Blob container name
    pdf_blob_name = Column(String(500), nullable=True)  # Blob path
    pdf_filename = Column(String(255), nullable=True)   # Original filename
    pdf_size_bytes = Column(BigInteger, nullable=True)  # File size
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    city = relationship("City", back_populates="base_agreements")
    agreements = relationship("Agreement", back_populates="base_agreement")


class Agreement(Base):
    """Main agreement entity."""
    __tablename__ = "agreement"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    initiator_id = Column(String(36), ForeignKey("app_user.id"), nullable=False)
    base_agreement_id = Column(String(36), ForeignKey("base_agreement.id"), nullable=True)
    title = Column(String(255), default="Roommate Agreement")
    owner_name = Column(String(255), nullable=True)  # Landlord/Owner name
    tenant_name = Column(String(255), nullable=True)  # Tenant name (auto-filled after acceptance)
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(100), nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    rent_total_cents = Column(Integer, nullable=False)
    status = Column(String(50), default="draft")  # 'draft', 'awaiting_payment', 'paid', 'inviting', 'signing', 'completed', 'void'
    content = Column(Text, nullable=True)  # Written agreement text (owner to tenant)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    initiator = relationship("AppUser", back_populates="agreements")
    base_agreement = relationship("BaseAgreement", back_populates="agreements")
    parties = relationship("AgreementParty", back_populates="agreement", cascade="all, delete-orphan")
    terms = relationship("AgreementTerms", back_populates="agreement", uselist=False, cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="agreement", cascade="all, delete-orphan")
    envelopes = relationship("SignatureEnvelope", back_populates="agreement", cascade="all, delete-orphan")
    invite_tokens = relationship("InviteToken", back_populates="agreement", cascade="all, delete-orphan")
    feedback = relationship("Feedback", back_populates="agreement", cascade="all, delete-orphan")


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
    requires_id_verification = Column(Boolean, default=False)  # Owner wants tenant to verify
    id_verified = Column(Boolean, default=False)  # Tenant has verified their ID
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


class InviteToken(Base):
    """Secure invite tokens for roommate invitations."""
    __tablename__ = "invite_token"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    agreement_id = Column(String(36), ForeignKey("agreement.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(255), nullable=False)
    token = Column(String(64), unique=True, nullable=False, default=generate_invite_token, index=True)
    is_used = Column(Boolean, default=False)
    used_by_user_id = Column(String(36), ForeignKey("app_user.id"), nullable=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    agreement = relationship("Agreement", back_populates="invite_tokens")


class Feedback(Base):
    """Roommate feedback and ratings."""
    __tablename__ = "feedback"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    agreement_id = Column(String(36), ForeignKey("agreement.id", ondelete="CASCADE"), nullable=False)
    from_user_id = Column(String(36), ForeignKey("app_user.id"), nullable=False)
    to_user_id = Column(String(36), ForeignKey("app_user.id"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5 stars
    comment = Column(Text, nullable=True)
    categories = Column(JSON, nullable=True)  # {"cleanliness": 4, "communication": 5, "respect": 4}
    is_anonymous = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    agreement = relationship("Agreement", back_populates="feedback")
    from_user = relationship("AppUser", foreign_keys=[from_user_id], back_populates="feedback_given")
    to_user = relationship("AppUser", foreign_keys=[to_user_id], back_populates="feedback_received")


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
