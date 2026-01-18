# app/routers/logs.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
import uuid
from sqlalchemy import desc, asc
from app.core.database import get_db
from app.models import tables
from app.schemas import CallLogCreate, CallLogResponse
from app.core.security import get_current_user

router = APIRouter()

# ==========================================
# 1. TEAM: LOG AN ACTIVITY (Call, Visit, etc.)
# ==========================================
@router.post("/", response_model=CallLogResponse)
def create_log(
    log_data: CallLogCreate, 
    current_user = Depends(get_current_user), # Logged in Staff
    db: Session = Depends(get_db)
):
    # 1. Find the Lead
    user = db.query(tables.User).filter(tables.User.phone == log_data.phone).first()
    if not user:
        raise HTTPException(status_code=404, detail="User with this phone not found. Create lead first.")

    # 2. Create the Log
    new_log = tables.CallLog(
        phone=log_data.phone,
        user_id=user.user_id,
        caller_id=current_user.user_id, # Automatically link to logged-in staff
        interaction_type=log_data.interaction_type,
        notes=log_data.notes,
        next_action=log_data.next_action,
        next_follow_up_date=log_data.next_follow_up_date,
        site_visit_status=log_data.site_visit_status
    )
    db.add(new_log)
    
    # 3. AUTOMATION: Update the Lead's Main Profile
    # "Shared Pool" logic: The lead is now 'touched' by this staff member.
    user.last_contact_date = func.current_date()
    
    # If a follow-up date is set, update the main profile so it shows up in the "To Do" list
    if log_data.next_follow_up_date:
        user.next_action_date = log_data.next_follow_up_date
        
    # Smart Status Update (Optional but recommended)
    if log_data.interaction_type == "Site Visit" and user.lead_status == "New":
        user.lead_status = "Site Visit Scheduled"
    elif user.lead_status == "New":
        user.lead_status = "Contacted"

    db.commit()
    db.refresh(new_log)
    
    return new_log

# ==========================================
# 2. TEAM: GET HISTORY FOR A LEAD
# ==========================================
@router.get("/{user_id}", response_model=List[CallLogResponse])
def get_logs_for_lead(
    user_id: uuid.UUID, 
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    # Fetch logs, newest first
    logs = db.query(tables.CallLog)\
        .filter(tables.CallLog.user_id == user_id)\
        .order_by(desc(tables.CallLog.created_at))\
        .all()
        
    return logs