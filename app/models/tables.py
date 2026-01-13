# app/models/tables.py
import uuid
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, Date, Time, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base
from sqlalchemy.dialects.postgresql import ARRAY

# We are NOT importing enums here because we will map them as standard Strings
# to match your existing database schema.

# ==========================================
# 1. SYSTEM USERS (Staff/Admins)
# ==========================================
class SystemUser(Base):
    __tablename__ = "system_users"

    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(200), nullable=False)
    phone = Column(String(15))
    
    # Matches SQL: role VARCHAR(20) NOT NULL CHECK (...)
    role = Column(String(20), nullable=False) 
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    call_logs = relationship("CallLog", back_populates="caller")


# ==========================================
# 2. USERS (Leads/Customers)
# ==========================================
class User(Base):
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone = Column(String(15), unique=True, nullable=False, index=True)
    name = Column(String(200))
    email = Column(String(255))
    
    # Classification - Mapped as simple Strings
    lead_source = Column(String(50))
    lead_status = Column(String(50), default='New', index=True)
    lead_temperature = Column(String(10), default='Warm')
    
    # Shared Pool Management
    last_contact_date = Column(Date)
    next_action_date = Column(Date, index=True)
    
    # General Info
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    queries = relationship("PropertyQuery", back_populates="user", cascade="all, delete-orphan")
    logs = relationship("CallLog", back_populates="user")


# ==========================================
# 3. PROPERTY QUERIES (Form Submissions)
# ==========================================
class PropertyQuery(Base):
    __tablename__ = "property_queries"

    query_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone = Column(String(15), nullable=False)
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"))
    
    name = Column(String(200))
    budget = Column(String(100))
    property_type = Column(String(50))
    user_type = Column(String(50))
    source = Column(String(50))
    message = Column(String, nullable=True)
    property_name = Column(String(255))
    
    # Matches SQL: query_status VARCHAR(50) ...
    listing_id = Column(UUID(as_uuid=True), ForeignKey("listings.listing_id", ondelete="SET NULL"), nullable=True)
    query_status = Column(String(50), default='New')
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="queries")
    listing = relationship("Listing", back_populates="queries")


# ==========================================
# 4. CALL LOGS (History)
# ==========================================
class CallLog(Base):
    __tablename__ = "call_logs"

    call_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone = Column(String(15), nullable=False)
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    caller_id = Column(Integer, ForeignKey("system_users.user_id", ondelete="CASCADE"), nullable=False)
    
    # Matches SQL: interaction_type VARCHAR(50) ...
    interaction_type = Column(String(50), default='Call')
    
    contact_date = Column(Date, server_default=func.current_date(), index=True)
    contact_time = Column(Time, server_default=func.current_time())
    
    notes = Column(Text, nullable=False)
    next_action = Column(Text)
    next_follow_up_date = Column(Date)
    
    site_visit_status = Column(String(50), nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="logs")
    caller = relationship("SystemUser", back_populates="call_logs")

class Listing(Base):
    __tablename__ = "listings"

    listing_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    title = Column(String(255), nullable=False)
    description = Column(Text)
    price = Column(String(100))
    location = Column(String(255))
    size = Column(String(100))
    
    property_type = Column(String(50), nullable=False) # Residential, Commercial...
    listing_category = Column(String(50), default='Standard')
    status = Column(String(50), default='Active')
    
    images = Column(ARRAY(String))
    brochure_url = Column(String(500), nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationship to queries (One listing has many queries)
    queries = relationship("PropertyQuery", back_populates="listing")