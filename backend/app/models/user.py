import enum
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class RoleEnum(str, enum.Enum):
    ADMIN = "ADMIN"
    FSQR_MANAGER = "FSQR_MANAGER"
    VALIDATION_ENGINEER = "VALIDATION_ENGINEER"
    REVIEWER = "REVIEWER"
    APPROVER = "APPROVER"
    READ_ONLY = "READ_ONLY"


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    name = Column(Enum(RoleEnum), nullable=False, unique=True)

    user_roles = relationship("UserRole", back_populates="role")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=True)
    email = Column(String(200), unique=True, nullable=False, index=True)
    full_name = Column(String(200), nullable=False)
    department = Column(String(100), nullable=True)
    department_code = Column(String(10), nullable=True)
    position = Column(String(200), nullable=True)
    hashed_password = Column(String(200), nullable=False)
    is_active = Column(Boolean, default=True)
    must_change_password = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

    organization = relationship("Organization", back_populates="users")
    site = relationship("Site", back_populates="users")
    user_roles = relationship("UserRole", back_populates="user")
    signatures = relationship("Signature", back_populates="user")


class UserRole(Base):
    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)

    user = relationship("User", back_populates="user_roles")
    role = relationship("Role", back_populates="user_roles")
