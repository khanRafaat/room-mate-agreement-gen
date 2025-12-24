"""
Roommate Agreement Generator - Authentication Dependencies
Azure AD B2C JWT validation and user extraction
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from typing import Optional
import httpx

from app.config import get_settings

settings = get_settings()

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


class TokenData:
    """Extracted token data from JWT."""
    
    def __init__(self, sub: str, email: Optional[str] = None, name: Optional[str] = None):
        self.sub = sub
        self.email = email
        self.name = name


async def get_jwks() -> dict:
    """
    Fetch JWKS (JSON Web Key Set) from Azure AD B2C.
    In production, cache this with appropriate TTL.
    """
    if not settings.azure_ad_b2c_tenant or not settings.azure_ad_b2c_policy:
        return {}
    
    jwks_url = (
        f"https://{settings.azure_ad_b2c_tenant}.b2clogin.com/"
        f"{settings.azure_ad_b2c_tenant}.onmicrosoft.com/"
        f"{settings.azure_ad_b2c_policy}/discovery/v2.0/keys"
    )
    
    async with httpx.AsyncClient() as client:
        response = await client.get(jwks_url)
        if response.status_code == 200:
            return response.json()
    return {}


async def validate_token(token: str) -> TokenData:
    """
    Validate JWT token from Azure AD B2C.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # For development, allow unverified tokens (skip signature validation)
        # In production, validate against JWKS
        if settings.debug:
            payload = jwt.get_unverified_claims(token)
        else:
            jwks = await get_jwks()
            if not jwks:
                raise credentials_exception
            
            # Get the signing key
            header = jwt.get_unverified_header(token)
            key = None
            for k in jwks.get("keys", []):
                if k.get("kid") == header.get("kid"):
                    key = k
                    break
            
            if not key:
                raise credentials_exception
            
            payload = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=settings.azure_ad_b2c_client_id,
            )
        
        sub: str = payload.get("sub")
        if sub is None:
            raise credentials_exception
        
        return TokenData(
            sub=sub,
            email=payload.get("emails", [None])[0] if payload.get("emails") else payload.get("email"),
            name=payload.get("name")
        )
    except JWTError:
        raise credentials_exception


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> TokenData:
    """
    FastAPI dependency to get the current authenticated user.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return await validate_token(credentials.credentials)


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[TokenData]:
    """
    FastAPI dependency for optional authentication.
    Returns None if no token provided.
    """
    if credentials is None:
        return None
    
    try:
        return await validate_token(credentials.credentials)
    except HTTPException:
        return None


# Dependency for protected routes
auth_dependency = Depends(get_current_user)
