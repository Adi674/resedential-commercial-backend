#routers/leads.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from typing import List, Optional
import uuid
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from app.core.database import get_db
from app.models import tables
# IMPORTANT: Ensure BrochureRequest is imported from schemas
from app.schemas import QueryCreate, QueryResponse, UserResponse, UserCreate, BrochureRequest
from app.core.security import get_current_user
import logging

router = APIRouter()

logger = logging.getLogger(__name__)

VALID_LEAD_STATUSES = ['New', 'Contacted', 'Interested', 'Site Visit Scheduled', 'Converted', 'Lost']

# ==========================================
# 1. PUBLIC: DEDICATED BROCHURE DOWNLOAD
# ==========================================
@router.post("/brochure", response_model=QueryResponse)
def download_brochure(request: BrochureRequest, db: Session = Depends(get_db)):
    """
    Dedicated endpoint for Brochure Downloads with proper transaction handling.
    """
    try:
        # A. Validate Listing & Brochure Availability
        listing = db.query(tables.Listing).filter(
            tables.Listing.listing_id == request.listing_id
        ).first()
        
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        
        if not listing.brochure_url:
            raise HTTPException(status_code=404, detail="No brochure available for this property")

        # B. Check or Create User (Lead)
        user = db.query(tables.User).filter(tables.User.phone == request.phone).first()
        
        if user:
            # Update existing user info
            if request.name and request.name != user.name:
                user.name = request.name
            if request.email and request.email != user.email:
                user.email = request.email
                
            # Upgrade status/temperature
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
            db.flush()  # Get user_id without committing

        # C. Record the Interaction (PropertyQuery)
        new_query = tables.PropertyQuery(
            user_id=user.user_id,
            phone=request.phone,
            listing_id=request.listing_id,
            property_name=listing.title,
            name=request.name,
            source="Brochure Download",
            query_status="New"
        )
        
        db.add(new_query)
        db.commit()  # Single commit at the end
        
        logger.info(f"Brochure download: {request.phone} for listing {request.listing_id}")

        # D. Return the URL
        return QueryResponse(
            success=True,
            message="Brochure sent successfully.",
            brochure_url=listing.brochure_url
        )
        
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error: {e}")
        raise HTTPException(status_code=409, detail="Duplicate entry or constraint violation")
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error in brochure download: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error in brochure download: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")



# ==========================================
# 2. PUBLIC: GENERAL CONTACT / QUERY
# ==========================================
@router.post("/query", response_model=QueryResponse)
def create_query(query_data: QueryCreate, db: Session = Depends(get_db)):
    """
    General endpoint for Contact Forms with proper error handling.
    """
    try:
        # A. Check or Create User (Lead)
        user = db.query(tables.User).filter(tables.User.phone == query_data.phone).first()
        
        if user:
            if query_data.name and query_data.name != user.name:
                user.name = query_data.name
            if query_data.email and query_data.email != user.email:
                user.email = query_data.email
        else:
            user = tables.User(
                phone=query_data.phone,
                name=query_data.name,
                email=query_data.email,
                lead_source=query_data.query_source,
                lead_status="New",
                lead_temperature="Warm"
            )
            db.add(user)
            db.flush()

        # B. Resolve Listing Name (Optional)
        listing_title = "General Inquiry"
        if query_data.listing_id:
            listing = db.query(tables.Listing).filter(
                tables.Listing.listing_id == query_data.listing_id
            ).first()
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
            message=query_data.message,
            budget=query_data.budget,
            property_type=query_data.property_type,
            user_type=query_data.user_type,
            query_status="New"
        )
        
        db.add(new_query)
        db.commit()
        
        logger.info(f"Query created: {query_data.phone} - {query_data.query_source}")

        return QueryResponse(
            success=True,
            message="Thank you! We will contact you soon.",
            brochure_url=None
        )
        
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error: {e}")
        raise HTTPException(status_code=409, detail="Duplicate entry")
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error in query creation: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error in query creation: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")



@router.get("/", response_model=List[UserResponse])
def get_leads(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get lead pool with optional status filter.
    """
    try:
        # Validate status parameter
        if status and status not in VALID_LEAD_STATUSES:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid status. Must be one of: {', '.join(VALID_LEAD_STATUSES)}"
            )
        
        # Validate pagination parameters
        if skip < 0:
            raise HTTPException(status_code=400, detail="Skip must be non-negative")
        if limit <= 0 or limit > 100:
            raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")
        
        query = db.query(tables.User)
        
        if status:
            query = query.filter(tables.User.lead_status == status)
        
        # Prioritize leads with upcoming follow-ups
        query = query.order_by(
            asc(tables.User.next_action_date.is_(None)), 
            asc(tables.User.next_action_date)
        )
        
        leads = query.offset(skip).limit(limit).all()
        
        return leads
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching leads: {e}")
        raise HTTPException(status_code=500, detail="Error fetching leads")

# ==========================================
# 4. TEAM: GET SINGLE LEAD DETAILS
# ==========================================
@router.get("/{user_id}", response_model=UserResponse)
def get_lead_detail(user_id: uuid.UUID, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(tables.User).filter(tables.User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Lead not found")
    return user