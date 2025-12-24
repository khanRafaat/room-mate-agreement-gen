"""
Roommate Agreement Generator - FastAPI Application
Main application entry point with all routers and middleware
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.database import init_db
from app.routers import agreements, webhooks, files, users
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
    - Card and crypto payments (Stripe, Coinbase Commerce)
    - E-signatures via DocuSign
    - Email/SMS notifications via Azure Communication Services
    - ID verification (ID.me, Onfido, Persona)
    - Secure file storage on Azure Blob
    
    ### Authentication
    Use Azure AD B2C JWT tokens in the Authorization header:
    ```
    Authorization: Bearer <your-token>
    ```
    
    For development/testing, set `DEBUG=true` in your .env file to skip token validation.
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
app.include_router(agreements.router, prefix="/api")
app.include_router(webhooks.router, prefix="/api")
app.include_router(files.router, prefix="/api")
app.include_router(users.router, prefix="/api")


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
        "endpoints": {
            "agreements": "/api/agreements",
            "users": "/api/users",
            "files": "/api/upload-sas",
            "webhooks": {
                "stripe": "/api/webhooks/stripe",
                "coinbase": "/api/webhooks/coinbase",
                "docusign": "/api/webhooks/docusign"
            }
        }
    }
