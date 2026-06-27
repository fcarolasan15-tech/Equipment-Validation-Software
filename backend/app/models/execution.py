import enum
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class ItemStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    PASS = "PASS"
    FAIL = "FAIL"
    NA = "NA"


class DeviationSeverityEnum(str, enum.Enum):
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    OBSERVATION = "OBSERVATION"


class DeviationStatusEnum(str, enum.Enum):
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    CLOSED = "CLOSED"


class ExecutionItem(Base):
    __tablename__ = "execution_items"

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(Integer, ForeignKey("validation_records.id"), nullable=False)
    step_number = Column(String(20), nullable=False)
    description = Column(Text, nullable=False)
    acceptance_criteria = Column(Text, nullable=True)
    actual_result = Column(Text, nullable=True)
    status = Column(Enum(ItemStatusEnum), default=ItemStatusEnum.PENDING)
    executed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    executed_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    record = relationship("ValidationRecord", back_populates="execution_items")
    executed_by = relationship("User", foreign_keys=[executed_by_id])
    deviations = relationship("Deviation", back_populates="execution_item")


class Deviation(Base):
    __tablename__ = "deviations"

    id = Column(Integer, primary_key=True, index=True)
    execution_item_id = Column(Integer, ForeignKey("execution_items.id"), nullable=True)
    record_id = Column(Integer, ForeignKey("validation_records.id"), nullable=False)
    deviation_number = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(Enum(DeviationSeverityEnum), nullable=False)
    status = Column(Enum(DeviationStatusEnum), default=DeviationStatusEnum.OPEN)
    root_cause = Column(Text, nullable=True)
    corrective_action = Column(Text, nullable=True)
    raised_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    closed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    raised_at = Column(DateTime(timezone=True), server_default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)
    is_blocking = Column(Boolean, default=False)

    execution_item = relationship("ExecutionItem", back_populates="deviations")
    raised_by = relationship("User", foreign_keys=[raised_by_id])
    closed_by = relationship("User", foreign_keys=[closed_by_id])
