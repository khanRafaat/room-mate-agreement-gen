"""
Roommate Agreement Generator - Auth Service
JWT token generation and password hashing
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
import bcrypt


from app.config import get_settings

settings = get_settings()

# Password hashing context


class AuthService:
    """Authentication service for password hashing and JWT tokens."""
    
    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password
        """
        # Convert password to bytes and generate salt and hash
        pwd_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(pwd_bytes, salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            plain_password: Plain text password
            hashed_password: Hashed password to compare against
            
        Returns:
            True if password matches
        """
        # Check if the plain password matches the hashed password
        pwd_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
    
    def create_access_token(
        self,
        user_id: str,
        email: str,
        expires_delta: Optional[timedelta] = None
    ) -> tuple[str, int]:
        """
        Create a JWT access token.
        
        Args:
            user_id: User ID to encode in token
            email: User email to encode in token
            expires_delta: Optional custom expiry time
            
        Returns:
            Tuple of (token string, expires_in seconds)
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
            expires_in = int(expires_delta.total_seconds())
        else:
            expires_in = settings.jwt_expire_minutes * 60
            expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
        
        to_encode = {
            "sub": user_id,
            "email": email,
            "exp": expire,
            "iat": datetime.utcnow()
        }
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm
        )
        
        return encoded_jwt, expires_in
    
    def decode_token(self, token: str) -> Optional[dict]:
        """
        Decode and validate a JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded payload or None if invalid
        """
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm]
            )
            return payload
        except JWTError:
            return None
    
    def get_user_id_from_token(self, token: str) -> Optional[str]:
        """
        Extract user ID from a JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            User ID or None if invalid
        """
        payload = self.decode_token(token)
        if payload:
            return payload.get("sub")
        return None


# Singleton instance
auth_service = AuthService()
