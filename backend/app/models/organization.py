from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True)
    short_name = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    sites = relationship("Site", back_populates="organization")
    users = relationship("User", back_populates="organization")


class Site(Base):
    __tablename__ = "sites"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    name = Column(String(200), nullable=False)
    code = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    organization = relationship("Organization", back_populates="sites")
    users = relationship("User", back_populates="site")
    assets = relationship("Asset", back_populates="site")
    projects = relationship("ValidationProject", back_populates="site")
