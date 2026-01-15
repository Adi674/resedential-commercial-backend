# app/core/security.py
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.core.database import get_db
from app.models import tables
import os
import logging

logger = logging.getLogger(__name__)

# Configuration - READ FROM .ENV
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-change-this")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # ✅ ADD int() conversion

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # ✅ This will now use 1440 minutes (24 hours) from .env
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security), 
    db: Session = Depends(get_db)
):
    """
    Dependency: Get the current authenticated user from JWT token
    """
    token = credentials.credentials
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode and validate token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        
        if username is None:
            logger.warning("Token missing 'sub' claim")
            raise credentials_exception
            
    except JWTError as e:
        logger.error(f"JWT decode error: {e}")
        raise credentials_exception
    
    # Query database for user with error handling
    try:
        user = db.query(tables.SystemUser).filter(
            tables.SystemUser.username == username
        ).first()
        
        if user is None:
            logger.warning(f"User not found in database: {username}")
            raise credentials_exception
            
        if not user.is_active:
            logger.warning(f"Inactive user attempted access: {username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
            
        return user
        
    except SQLAlchemyError as e:
        logger.error(f"Database error in get_current_user: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection error. Please try again."
        )

def get_current_admin(current_user: tables.SystemUser = Depends(get_current_user)):
    """
    Dependency: Check if user is Admin
    """
    if current_user.role != "admin":
        logger.warning(f"Non-admin user attempted admin access: {current_user.username}")
        raise HTTPException(
            status_code=403, 
            detail="Admin access required"
        )
    return current_user