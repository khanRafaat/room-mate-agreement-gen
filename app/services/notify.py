"""
Roommate Agreement Generator - Notification Service
Azure Communication Services for email and SMS
"""
from typing import Optional, List

from app.config import get_settings

settings = get_settings()

# Conditional import for Azure Communication Services
try:
    from azure.communication.email import EmailClient
    ACS_EMAIL_AVAILABLE = True
except ImportError:
    ACS_EMAIL_AVAILABLE = False


class NotificationService:
    """Notification service using Azure Communication Services."""
    
    def __init__(self):
        """Initialize the notification service."""
        self._email_client: Optional[object] = None
    
    @property
    def email_client(self):
        """Get or create the ACS Email client."""
        if not ACS_EMAIL_AVAILABLE:
            raise ImportError("azure-communication-email package is not installed")
        
        if self._email_client is None:
            if not settings.acs_connection_string:
                raise ValueError("ACS connection string not configured")
            
            self._email_client = EmailClient.from_connection_string(
                settings.acs_connection_string
            )
        
        return self._email_client
    
    def send_email(
        self,
        to: List[str],
        subject: str,
        body_html: str,
        body_plain: Optional[str] = None
    ) -> dict:
        """
        Send an email using Azure Communication Services.
        
        Args:
            to: List of recipient email addresses
            subject: Email subject
            body_html: HTML body content
            body_plain: Plain text body content (optional)
            
        Returns:
            Dict with message_id and status
        """
        if not ACS_EMAIL_AVAILABLE:
            raise ImportError("azure-communication-email package is not installed")
        
        message = {
            "senderAddress": settings.acs_sender_email,
            "recipients": {
                "to": [{"address": email} for email in to]
            },
            "content": {
                "subject": subject,
                "html": body_html
            }
        }
        
        if body_plain:
            message["content"]["plainText"] = body_plain
        
        poller = self.email_client.begin_send(message)
        result = poller.result()
        
        return {
            "message_id": result.get("id"),
            "status": result.get("status")
        }
    
    def send_invite_email(
        self,
        to_email: str,
        inviter_name: str,
        agreement_title: str,
        invite_link: str
    ) -> dict:
        """
        Send an agreement invite email.
        
        Args:
            to_email: Recipient email
            inviter_name: Name of the person who sent the invite
            agreement_title: Title of the agreement
            invite_link: Link to view/sign the agreement
            
        Returns:
            Dict with message_id and status
        """
        subject = f"{inviter_name} has invited you to sign a Roommate Agreement"
        
        body_html = f"""
        <html>
        <body>
            <h2>You've Been Invited to Sign a Roommate Agreement</h2>
            <p><strong>{inviter_name}</strong> has invited you to review and sign: <em>{agreement_title}</em></p>
            <p>Please click the link below to view the agreement and complete your signature:</p>
            <p><a href="{invite_link}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">View Agreement</a></p>
            <p>This link will expire in 7 days.</p>
            <hr>
            <p style="color: #666; font-size: 12px;">
                This email was sent by Roommate Agreement Generator. 
                If you did not expect this email, please ignore it.
            </p>
        </body>
        </html>
        """
        
        body_plain = f"""
        You've Been Invited to Sign a Roommate Agreement
        
        {inviter_name} has invited you to review and sign: {agreement_title}
        
        Please visit the following link to view the agreement and complete your signature:
        {invite_link}
        
        This link will expire in 7 days.
        """
        
        return self.send_email(
            to=[to_email],
            subject=subject,
            body_html=body_html,
            body_plain=body_plain
        )
    
    def send_reminder_email(
        self,
        to_email: str,
        agreement_title: str,
        days_until_expiry: int,
        agreement_link: str
    ) -> dict:
        """
        Send an agreement expiry reminder email.
        
        Args:
            to_email: Recipient email
            agreement_title: Title of the agreement
            days_until_expiry: Days until the agreement expires
            agreement_link: Link to view the agreement
            
        Returns:
            Dict with message_id and status
        """
        subject = f"Reminder: Your Roommate Agreement expires in {days_until_expiry} days"
        
        body_html = f"""
        <html>
        <body>
            <h2>Agreement Expiry Reminder</h2>
            <p>Your roommate agreement <em>{agreement_title}</em> will expire in <strong>{days_until_expiry} days</strong>.</p>
            <p>Consider renewing your agreement to maintain clear terms with your roommates.</p>
            <p><a href="{agreement_link}" style="background-color: #2196F3; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">View Agreement</a></p>
            <hr>
            <p style="color: #666; font-size: 12px;">
                This is an automated reminder from Roommate Agreement Generator.
            </p>
        </body>
        </html>
        """
        
        return self.send_email(
            to=[to_email],
            subject=subject,
            body_html=body_html
        )
    
    def send_completion_email(
        self,
        to_emails: List[str],
        agreement_title: str,
        download_link: str
    ) -> dict:
        """
        Send an agreement completion notification email.
        
        Args:
            to_emails: List of recipient emails
            agreement_title: Title of the agreement
            download_link: Link to download the signed agreement
            
        Returns:
            Dict with message_id and status
        """
        subject = f"Your Roommate Agreement is Complete!"
        
        body_html = f"""
        <html>
        <body>
            <h2>🎉 Agreement Signed Successfully!</h2>
            <p>Great news! All parties have signed the roommate agreement: <em>{agreement_title}</em></p>
            <p>You can download your signed agreement using the link below:</p>
            <p><a href="{download_link}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Download Signed Agreement</a></p>
            <p>Keep this document in a safe place for your records.</p>
            <hr>
            <p style="color: #666; font-size: 12px;">
                Thank you for using Roommate Agreement Generator.
            </p>
        </body>
        </html>
        """
        
        return self.send_email(
            to=to_emails,
            subject=subject,
            body_html=body_html
        )


# Singleton instance
notification_service = NotificationService()
