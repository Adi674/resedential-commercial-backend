from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import json

from app.core.database import get_db
from app.models import tables
from app.schemas import ListingCard, ListingDetail
from app.core.security import get_current_admin
from app.utils.storage import upload_file_to_supabase

router = APIRouter()

# ===========================
# 1. PUBLIC: GET ALL (Cards)
# ===========================
@router.get("/", response_model=List[ListingCard])
def get_listings(
    type: Optional[str] = None, # Filter: Residential/Commercial
    db: Session = Depends(get_db)
):
    query = db.query(tables.Listing).filter(tables.Listing.status == 'Active')
    
    if type:
        query = query.filter(tables.Listing.property_type == type)
        
    listings = query.all()
    
    # Convert to Card Schema (picking first image)
    results = []
    for lst in listings:
        card = ListingCard.model_validate(lst)
        if lst.images and len(lst.images) > 0:
            card.image = lst.images[0] # Set thumbnail
        results.append(card)
        
    return results

# ===========================
# 2. PUBLIC: GET DETAIL
# ===========================
@router.get("/{listing_id}", response_model=ListingDetail)
def get_listing_detail(listing_id: str, db: Session = Depends(get_db)):
    listing = db.query(tables.Listing).filter(tables.Listing.listing_id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing

# ===========================
# 3. ADMIN: CREATE LISTING (With Files)
# ===========================
@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_listing(
    # --- Form Fields ---
    title: str = Form(...),
    description: str = Form(None),
    price: str = Form(None),
    location: str = Form(None),
    size: str = Form(None),
    property_type: str = Form(...), # Residential, Commercial, etc.
    listing_category: str = Form("Standard"),
    
    # --- File Uploads ---
    # We accept a list of images and one optional brochure
    image_files: List[UploadFile] = File(default=[]), 
    brochure_file: UploadFile = File(default=None),
    
    # --- Auth & DB ---
    current_user = Depends(get_current_admin), # Security: Only Admin
    db: Session = Depends(get_db)
):
    
    # 1. Upload Images to Supabase
    uploaded_image_urls = []
    for img in image_files:
        if img.filename: # check if file was actually selected
            url = await upload_file_to_supabase(img, "property-images")
            uploaded_image_urls.append(url)
            
    # 2. Upload Brochure (if exists)
    uploaded_brochure_url = None
    if brochure_file and brochure_file.filename:
        uploaded_brochure_url = await upload_file_to_supabase(brochure_file, "brochures")

    # 3. Create DB Entry
    new_listing = tables.Listing(
        title=title,
        description=description,
        price=price,
        location=location,
        size=size,
        property_type=property_type,
        listing_category=listing_category,
        status="Active",
        images=uploaded_image_urls,     # Save list of URLs
        brochure_url=uploaded_brochure_url # Save single URL
    )
    
    db.add(new_listing)
    db.commit()
    db.refresh(new_listing)
    
    return {"message": "Listing created successfully", "id": new_listing.listing_id}