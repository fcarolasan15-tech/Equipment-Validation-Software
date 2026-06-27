import enum
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class SignatureRoleEnum(str, enum.Enum):
    PREPARED_BY = "PREPARED_BY"
    REVIEWED_BY = "REVIEWED_BY"
    APPROVED_BY = "APPROVED_BY"


class Signature(Base):
    __tablename__ = "signatures"

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(Integer, ForeignKey("validation_records.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(Enum(SignatureRoleEnum), nullable=False)
    meaning = Column(Text, nullable=True)
    signed_at = Column(DateTime(timezone=True), server_default=func.now())
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    password_verified = Column(String(1), default="Y")

    record = relationship("ValidationRecord", back_populates="signatures")
    user = relationship("User", back_populates="signatures")
