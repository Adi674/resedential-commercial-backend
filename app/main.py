from fastapi.middleware.cors import CORSMiddleware
from app.core.database import engine, Base
from app.routers import auth, listings, leads, logs
from fastapi.exceptions import RequestValidationError
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from app.core.logging_config import setup_logging
import logging
import os

setup_logging()
logger = logging.getLogger(__name__)

# ==========================================
# 1. INITIALIZE DATABASE
# ==========================================
# This creates the tables (users, listings, etc.) if they don't exist yet.
logger.info("Initializing database tables...")
Base.metadata.create_all(bind=engine)
logger.info("Database tables initialized successfully")

# ==========================================
# 2. SETUP APPLICATION
# ==========================================
app = FastAPI(
    title="Real Estate CRM API",
    description="Backend for Property Management & Lead Tracking System",
    version="1.0.0"
)

# ==========================================
# 3. CONFIGURE CORS (Security)
# ==========================================
# This allows your Frontend (running on localhost:5173 or :3000) 
# to talk to this Backend.
origins = [
    "http://localhost:5173", # Vite Default
    "http://localhost:3000", # React Default
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    # Add your production domain here later, e.g., "https://my-real-estate.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # Who can call this API
    allow_credentials=True,      # Allow cookies/auth headers
    allow_methods=["*"],         # Allow GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],         # Allow all headers
)

@app.on_event("startup")
async def startup_event():
    """Log application startup"""
    logger.info("=" * 50)
    logger.info("🚀 Real Estate CRM API Starting Up")
    logger.info("=" * 50)
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"Database: {os.getenv('DATABASE_URL', 'Not Set')[:50]}...")
    logger.info(f"JWT Expiration: {os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', 'Not Set')} minutes")
    logger.info("=" * 50)

@app.on_event("shutdown")
async def shutdown_event():
    """Log application shutdown"""
    logger.info("=" * 50)
    logger.info("🛑 Real Estate CRM API Shutting Down")
    logger.info("=" * 50)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Get the first error message from the list
    error_message = exc.errors()[0].get("msg").replace("Value error, ", "")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": error_message,
            "brochure_url": None
        },
    )
# ==========================================
# 4. REGISTER ROUTERS
# ==========================================
# We attach the separate router files here to keep code organized.

# A. Authentication (Login & Staff Info)
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# B. Properties (Public & Admin Management)
app.include_router(listings.router, prefix="/listings", tags=["Properties"])

# C. Leads & Queries (Public Forms & Team Dashboard)
app.include_router(leads.router, prefix="/leads", tags=["Leads & Queries"])

# D. Logs (Staff Call History & Automation)
app.include_router(logs.router, prefix="/logs", tags=["Call Logs"])

# ==========================================
# 5. HEALTH CHECK
# ==========================================
@app.get("/", tags=["Health"])
def read_root():
    return {
        "status": "active", 
        "message": "Real Estate CRM API is running successfully."
    }