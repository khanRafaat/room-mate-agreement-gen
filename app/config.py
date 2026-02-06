"""
Roommate Agreement Generator - Configuration
Environment configuration using Pydantic Settings
"""
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_name: str = "Roommate Agreement Generator"
    debug: bool = True
    demo_mode: bool = False  # Set to True to bypass ID verification and payments
    
    # Database (MySQL)
    database_url: str = "mysql+pymysql://root:@localhost:3306/roomate"
    
    # JWT Authentication
    jwt_secret_key: str = "your-super-secret-jwt-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days
    
    # Azure Storage
    azure_storage_connection_string: Optional[str] = None
    azure_storage_account_name: Optional[str] = None
    azure_storage_account_key: Optional[str] = None
    
    # Azure AD B2C (optional, for enterprise SSO)
    azure_ad_b2c_tenant: Optional[str] = None
    azure_ad_b2c_client_id: Optional[str] = None
    azure_ad_b2c_policy: str = "B2C_1_signupsignin"
    
    # Stripe
    stripe_secret_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    stripe_publishable_key: Optional[str] = None
    stripe_price_cents: int = 250  # $2.50
    
    # Coinbase Commerce
    coinbase_commerce_key: Optional[str] = None
    coinbase_commerce_webhook_secret: Optional[str] = None
    coinbase_price_usd: str = "2.00"
    
    # Persona Identity Verification
    persona_template_id: Optional[str] = None       # itmpl_xxx
    persona_environment_id: Optional[str] = None    # env_xxx
    persona_api_key: Optional[str] = None
    persona_webhook_secret: Optional[str] = None
    
    # DocuSign
    docusign_base_url: str = "https://demo.docusign.net/restapi"
    docusign_access_token: Optional[str] = None
    docusign_account_id: Optional[str] = None
    
    # Azure Communication Services
    acs_connection_string: Optional[str] = None
    acs_sender_email: str = "noreply@example.com"
    
    # SMTP Mail Configuration (Mailtrap/SMTP)
    mail_mailer: str = "smtp"
    mail_host: str = "sandbox.smtp.mailtrap.io"
    mail_port: int = 2525
    mail_username: Optional[str] = "cef494278211a7"
    mail_password: Optional[str] = "****eb28"
    mail_encryption: str = "tls"
    mail_from_address: str = "noreply@roommate-agreement.com"
    mail_from_name: str = "Roommate Agreement Generator"
    
    # Frontend URLs (for redirects)
    frontend_url: str = "http://localhost:3000"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
