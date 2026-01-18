# app/schemas.py
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import date, datetime, time
from uuid import UUID
from enum import Enum

# =======================
# 1. SHARED / AUTH MODELS
# =======================

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

# =======================
# 2. SYSTEM USER (Staff)
# =======================

class SystemUserBase(BaseModel):
    username: str
    full_name: str
    role: str  # 'admin' or 'team'
    phone: Optional[str] = None

class SystemUserCreate(SystemUserBase):
    password: str

class SystemUserResponse(SystemUserBase):
    user_id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# =======================
# 3. VALIDATORS MIXIN (Shared Logic)
# =======================

class ValidatorMixin:
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str):
        if v is None: return v
        clean_phone = v.replace(" ", "").replace("-", "").replace("+", "")
        if not clean_phone.isdigit():
            raise ValueError('Phone number must contain only digits')
        if len(clean_phone) < 10 or len(clean_phone) > 15:
             raise ValueError('Phone number must be between 10 and 15 digits')
        return clean_phone

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str):
        if not v or len(v.strip()) < 2:
            raise ValueError('Name must be at least 2 characters long')
        return v.title()

    @field_validator('email', check_fields=False)
    @classmethod
    def validate_email(cls, v: Optional[str]):
        if v is None or v == "" or v == "string":  # ✅ FIX: Allow empty/None/placeholder
            return None
        # Only validate if actually provided
        v = v.strip()
        if '@' not in v or '.' not in v.split('@')[-1]:
            raise ValueError('Invalid email format')
        return v.lower()

# Separate mixin for text fields
class TextValidatorMixin:
    @field_validator('message', 'notes', check_fields=False)  # Add check_fields=False
    @classmethod
    def validate_text_fields(cls, v: Optional[str]):
        if v is None:
            return v
        cleaned = v.strip()
        if len(cleaned) > 2000:
            raise ValueError('Text too long (max 2000 characters)')
        return cleaned

# =======================
# 4. PUBLIC FORMS (Leads)
# =======================

class BrochureRequest(BaseModel, ValidatorMixin):
    name: str
    phone: str
    listing_id: UUID 
    email: Optional[str] = None

class QueryCreate(BaseModel, ValidatorMixin, TextValidatorMixin):
    name: str
    phone: str
    query_source: str = "Website"
    listing_id: Optional[UUID] = None
    
    # Optional fields
    email: Optional[str] = None
    message: Optional[str] = None
    budget: Optional[str] = None
    property_type: Optional[str] = None
    user_type: Optional[str] = None
    preferred_time: Optional[str] = None

    @field_validator('listing_id', mode='before')
    @classmethod
    def validate_listing_id(cls, v):
        """Convert empty string to None for optional UUID field"""
        if v == "" or v == "string":
            return None
        return v

    @field_validator('budget', 'property_type', 'user_type', 'preferred_time', mode='before')
    @classmethod
    def clean_string_fields(cls, v):
        """Remove placeholder 'string' values"""
        if v == "string" or v == "":
            return None
        return v

    

class QueryResponse(BaseModel):
    success: bool = True
    message: str
    brochure_url: Optional[str] = None

# =======================
# 5. LISTINGS (Properties)
# =======================

class PropertyType(str, Enum):
    RESIDENTIAL = "Residential"
    COMMERCIAL = "Commercial"
    PLOT = "Plot"
    VILLA = "Villa"

# NOTE: Removed ValidatorMixin from here because ListingBase has no phone/name
class ListingBase(BaseModel):
    title: str
    price: Optional[str] = None      # "₹5.5 Cr"
    location: Optional[str] = None
    size: Optional[str] = None       # "500 Sq. Yd."
    property_type: PropertyType        
    listing_category: str = "Standard" 
    status: str = "Active"

class ListingCreate(ListingBase):
    description: Optional[str] = None
    images: List[str] = []           
    brochure_url: Optional[str] = None

class ListingCard(ListingBase):
    listing_id: UUID
    image: Optional[str] = None 
    class Config:
        from_attributes = True

class ListingDetail(ListingBase):
    listing_id: UUID
    description: Optional[str] = None
    images: List[str] = []           
    created_at: datetime
    class Config:
        from_attributes = True

# =======================
# 6. CRM / CUSTOMER DATA
# =======================

class UserBase(BaseModel):
    phone: str
    name: Optional[str] = None
    email: Optional[str] = None
    lead_source: Optional[str] = "Website"

class UserCreate(UserBase):
    notes: Optional[str] = None

class UserResponse(UserBase):
    user_id: UUID
    lead_status: str
    lead_temperature: str
    last_contact_date: Optional[date]
    next_action_date: Optional[date]
    created_at: datetime
    class Config:
        from_attributes = True

# =======================
# 7. CALL LOGS
# =======================

class CallLogCreate(BaseModel):
    phone: str 
    interaction_type: str = "Call" 
    notes: str
    next_action: Optional[str] = None
    next_follow_up_date: Optional[date] = None
    site_visit_status: Optional[str] = None

class CallLogResponse(CallLogCreate):
    call_id: UUID
    caller_id: int 
    contact_date: date
    created_at: datetime
    class Config:
        from_attributes = True