from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from typing import List, Optional
import uuid

from app.core.database import get_db
from app.models import tables
# IMPORTANT: Ensure BrochureRequest is imported from schemas
from app.schemas import QueryCreate, QueryResponse, UserResponse, UserCreate, BrochureRequest
from app.core.security import get_current_user

router = APIRouter()

# ==========================================
# 1. PUBLIC: DEDICATED BROCHURE DOWNLOAD
# ==========================================
@router.post("/brochure", response_model=QueryResponse)
def download_brochure(request: BrochureRequest, db: Session = Depends(get_db)):
    """
    Dedicated endpoint for Brochure Downloads.
    - Validates listing exists & has a brochure.
    - Auto-sets source to "Brochure Download".
    - Returns the PDF URL immediately.
    """
    
    # A. Validate Listing & Brochure Availability
    listing = db.query(tables.Listing).filter(tables.Listing.listing_id == request.listing_id).first()
    
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    if not listing.brochure_url:
        raise HTTPException(status_code=404, detail="No brochure available for this property")

    # B. Check or Create User (Lead)
    # We treat brochure downloads as "Hot" leads immediately.
    user = db.query(tables.User).filter(tables.User.phone == request.phone).first()
    
    if user:
        # Update existing user info
        if request.name:
            user.name = request.name
        if request.email: # Update email if provided
            user.email = request.email
            
        # Upgrade status/temperature because they want a brochure
        user.lead_temperature = "Hot"
        if user.lead_status == "New":
            user.lead_status = "Interested"
    else:
        # Create new user
        user = tables.User(
            phone=request.phone,
            name=request.name,
            email=request.email,
            lead_source="Brochure Download",
            lead_status="New",
            lead_temperature="Hot"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # C. Record the Interaction (PropertyQuery)
    new_query = tables.PropertyQuery(
        user_id=user.user_id,
        phone=request.phone,
        listing_id=request.listing_id,
        property_name=listing.title,
        name=request.name,
        source="Brochure Download", # Hardcoded Source
        query_status="New"
        # property_type, budget, preferred_time are skipped for brochures
    )
    
    db.add(new_query)
    db.commit()

    # D. Return the URL
    return QueryResponse(
        success=True,
        message="Brochure sent successfully.",
        brochure_url=listing.brochure_url
    )


# ==========================================
# 2. PUBLIC: GENERAL CONTACT / QUERY
# ==========================================
@router.post("/query", response_model=QueryResponse)
def create_query(query_data: QueryCreate, db: Session = Depends(get_db)):
    """
    General endpoint for Contact Forms, CTAs, etc.
    """
    
    # A. Check or Create User (Lead)
    user = db.query(tables.User).filter(tables.User.phone == query_data.phone).first()
    
    if user:
        if query_data.name:
            user.name = query_data.name
        # General queries are usually "Warm" unless specified otherwise
    else:
        user = tables.User(
            phone=query_data.phone,
            name=query_data.name,
            lead_source=query_data.query_source,
            lead_status="New",
            lead_temperature="Warm"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # B. Resolve Listing Name (Optional)
    listing_title = "General Inquiry"
    if query_data.listing_id:
        listing = db.query(tables.Listing).filter(tables.Listing.listing_id == query_data.listing_id).first()
        if listing:
            listing_title = listing.title

    # C. Record the Interaction
    new_query = tables.PropertyQuery(
        user_id=user.user_id,
        phone=query_data.phone,
        listing_id=query_data.listing_id,
        property_name=listing_title,
        name=query_data.name,
        source=query_data.query_source,
        message=query_data.message, # Capture message if available
        query_status="New"
    )
    
    db.add(new_query)
    db.commit()

    return QueryResponse(
        success=True,
        message="Thank you! We will contact you soon.",
        brochure_url=None
    )


# ==========================================
# 3. TEAM: GET LEAD POOL (Dashboard)
# ==========================================
@router.get("/", response_model=List[UserResponse])
def get_leads(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user = Depends(get_current_user), # PROTECTED
    db: Session = Depends(get_db)
):
    query = db.query(tables.User)
    
    if status:
        query = query.filter(tables.User.lead_status == status)
    
    # Logic: Show leads with urgent 'next_action_date' first. 
    # Null dates (no action planned) go to the bottom.
    query = query.order_by(asc(tables.User.next_action_date.is_(None)), asc(tables.User.next_action_date))
    
    return query.offset(skip).limit(limit).all()


# ==========================================
# 4. TEAM: GET SINGLE LEAD DETAILS
# ==========================================
@router.get("/{user_id}", response_model=UserResponse)
def get_lead_detail(user_id: uuid.UUID, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(tables.User).filter(tables.User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Lead not found")
    return user