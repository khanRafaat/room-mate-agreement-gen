"""
Roommate Agreement Generator - FastAPI Application
Main application entry point with all routers and middleware
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.database import init_db
from app.routers import agreements, webhooks, files, users, auth, feedback, invites, locations, base_agreements
from app.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown events."""
    # Startup: Initialize database tables
    print("[START] Starting Roommate Agreement Generator API...")
    init_db()
    print("[OK] Database tables created/verified")
    yield
    # Shutdown
    print("[STOP] Shutting down...")


app = FastAPI(
    title=settings.app_name,
    description="""
    ## Roommate Agreement Generator API
    
    Create, sign, and manage roommate agreements with:
    - User registration and JWT authentication
    - ID verification via ID.me (required before creating agreements)
    - Card and crypto payments (Stripe, Coinbase Commerce)
    - Invite roommates via secure email links
    - E-signatures via DocuSign
    - Roommate feedback and ratings
    - Email/SMS notifications via Azure Communication Services
    - Secure file storage on Azure Blob
    
    ### User Flow
    1. **Register** - `POST /api/auth/register`
    2. **Verify ID** - `POST /api/users/verify` (ID.me)
    3. **Create Agreement** - `POST /api/agreements` (requires verification)
    4. **Finalize Draft** - `POST /api/agreements/{id}/finalize`
    5. **Pay** - `POST /api/agreements/{id}/pay`
    6. **Invite Roommates** - `POST /api/agreements/{id}/invite` (sends email)
    7. **Roommates Accept** - `POST /api/invites/accept/{token}` (requires verification)
    8. **Sign via DocuSign** - `POST /api/agreements/{id}/docusign/envelope`
    9. **Complete** - Agreement saved, roommates can rate each other
    
    ### Authentication
    Use the returned JWT token in the Authorization header:
    ```
    Authorization: Bearer <your-token>
    ```
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(agreements.router, prefix="/api")
app.include_router(invites.router, prefix="/api")  # Invite management
app.include_router(feedback.router, prefix="/api")  # Roommate ratings
app.include_router(webhooks.router, prefix="/api")
app.include_router(files.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(locations.router, prefix="/api")  # Country/State/City dropdowns
app.include_router(base_agreements.router, prefix="/api")  # Base agreement templates


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/healthz"
    }


@app.get("/healthz")
async def health():
    """Health check endpoint."""
    return {"ok": True, "status": "healthy"}


@app.get("/api")
async def api_info():
    """API information endpoint."""
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "flow": [
            "1. POST /api/auth/register - Register account",
            "2. POST /api/auth/login - Login",
            "3. POST /api/users/verify - Start ID.me verification",
            "4. POST /api/agreements - Create agreement (requires verification)",
            "5. POST /api/agreements/{id}/finalize - Finalize draft",
            "6. POST /api/agreements/{id}/pay - Pay for agreement",
            "7. POST /api/agreements/{id}/invite - Invite roommates",
            "8. POST /api/invites/accept/{token} - Roommate accepts invite",
            "9. POST /api/agreements/{id}/docusign/envelope - Create signing envelope",
            "10. POST /api/feedback/{id} - Rate roommates after completion"
        ],
        "endpoints": {
            "auth": "/api/auth",
            "agreements": "/api/agreements",
            "invites": "/api/invites",
            "feedback": "/api/feedback",
            "users": "/api/users",
            "files": "/api/upload-sas"
        }
    }
