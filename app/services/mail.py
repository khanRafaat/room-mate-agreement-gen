"""
Roommate Agreement Generator - Mail Service
SMTP-based email service using Mailtrap or other SMTP providers
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Dict, Any
import logging

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class MailService:
    """SMTP-based mail service for sending emails."""
    
    def __init__(self):
        """Initialize the mail service with SMTP configuration."""
        self.host = settings.mail_host
        self.port = settings.mail_port
        self.username = settings.mail_username
        self.password = settings.mail_password
        self.encryption = settings.mail_encryption
        self.from_address = settings.mail_from_address
        self.from_name = settings.mail_from_name
    
    def _create_smtp_connection(self) -> smtplib.SMTP:
        """Create and configure SMTP connection."""
        if self.encryption == "ssl":
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(self.host, self.port, context=context)
        else:
            server = smtplib.SMTP(self.host, self.port)
            if self.encryption == "tls":
                server.starttls()
        
        if self.username and self.password:
            server.login(self.username, self.password)
        
        return server
    
    def send_email(
        self,
        to: List[str],
        subject: str,
        body_html: str,
        body_plain: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        reply_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send an email using SMTP.
        
        Args:
            to: List of recipient email addresses
            subject: Email subject
            body_html: HTML body content
            body_plain: Plain text body content (optional)
            cc: List of CC recipients (optional)
            bcc: List of BCC recipients (optional)
            reply_to: Reply-to email address (optional)
            
        Returns:
            Dict with success status and message details
        """
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.from_address}>"
            message["To"] = ", ".join(to)
            
            if cc:
                message["Cc"] = ", ".join(cc)
            
            if reply_to:
                message["Reply-To"] = reply_to
            
            # Attach plain text version (fallback)
            if body_plain:
                part_plain = MIMEText(body_plain, "plain")
                message.attach(part_plain)
            
            # Attach HTML version
            part_html = MIMEText(body_html, "html")
            message.attach(part_html)
            
            # Collect all recipients
            all_recipients = list(to)
            if cc:
                all_recipients.extend(cc)
            if bcc:
                all_recipients.extend(bcc)
            
            # Send email
            with self._create_smtp_connection() as server:
                server.sendmail(
                    self.from_address,
                    all_recipients,
                    message.as_string()
                )
            
            logger.info(f"Email sent successfully to {', '.join(to)}")
            
            return {
                "success": True,
                "message": "Email sent successfully",
                "recipients": to
            }
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            return {
                "success": False,
                "error": "SMTP authentication failed",
                "details": str(e)
            }
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return {
                "success": False,
                "error": "SMTP error occurred",
                "details": str(e)
            }
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return {
                "success": False,
                "error": "Failed to send email",
                "details": str(e)
            }
    
    def send_invite_email(
        self,
        to_email: str,
        inviter_name: str,
        agreement_title: str,
        invite_link: str
    ) -> Dict[str, Any]:
        """
        Send an agreement invite email.
        
        Args:
            to_email: Recipient email
            inviter_name: Name of the person who sent the invite
            agreement_title: Title of the agreement
            invite_link: Link to view/sign the agreement
            
        Returns:
            Dict with success status and message details
        """
        subject = f"{inviter_name} has invited you to sign a Roommate Agreement"
        
        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50;">You've Been Invited to Sign a Roommate Agreement</h2>
                <p><strong>{inviter_name}</strong> has invited you to review and sign: <em>{agreement_title}</em></p>
                <p>Please click the button below to view the agreement and complete your signature:</p>
                <p style="text-align: center; margin: 30px 0;">
                    <a href="{invite_link}" style="background-color: #4CAF50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">View Agreement</a>
                </p>
                <p style="color: #666;">This link will expire in 7 days.</p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #999; font-size: 12px;">
                    This email was sent by Roommate Agreement Generator. 
                    If you did not expect this email, please ignore it.
                </p>
            </div>
        </body>
        </html>
        """
        
        body_plain = f"""
You've Been Invited to Sign a Roommate Agreement

{inviter_name} has invited you to review and sign: {agreement_title}

Please visit the following link to view the agreement and complete your signature:
{invite_link}

This link will expire in 7 days.

---
This email was sent by Roommate Agreement Generator.
If you did not expect this email, please ignore it.
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
    ) -> Dict[str, Any]:
        """
        Send an agreement expiry reminder email.
        
        Args:
            to_email: Recipient email
            agreement_title: Title of the agreement
            days_until_expiry: Days until the agreement expires
            agreement_link: Link to view the agreement
            
        Returns:
            Dict with success status and message details
        """
        subject = f"Reminder: Your Roommate Agreement expires in {days_until_expiry} days"
        
        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #e67e22;">⏰ Agreement Expiry Reminder</h2>
                <p>Your roommate agreement <em>{agreement_title}</em> will expire in <strong>{days_until_expiry} days</strong>.</p>
                <p>Consider renewing your agreement to maintain clear terms with your roommates.</p>
                <p style="text-align: center; margin: 30px 0;">
                    <a href="{agreement_link}" style="background-color: #2196F3; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">View Agreement</a>
                </p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #999; font-size: 12px;">
                    This is an automated reminder from Roommate Agreement Generator.
                </p>
            </div>
        </body>
        </html>
        """
        
        body_plain = f"""
Agreement Expiry Reminder

Your roommate agreement "{agreement_title}" will expire in {days_until_expiry} days.

Consider renewing your agreement to maintain clear terms with your roommates.

View your agreement: {agreement_link}

---
This is an automated reminder from Roommate Agreement Generator.
        """
        
        return self.send_email(
            to=[to_email],
            subject=subject,
            body_html=body_html,
            body_plain=body_plain
        )
    
    def send_completion_email(
        self,
        to_emails: List[str],
        agreement_title: str,
        download_link: str
    ) -> Dict[str, Any]:
        """
        Send an agreement completion notification email.
        
        Args:
            to_emails: List of recipient emails
            agreement_title: Title of the agreement
            download_link: Link to download the signed agreement
            
        Returns:
            Dict with success status and message details
        """
        subject = "Your Roommate Agreement is Complete!"
        
        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #27ae60;">🎉 Agreement Signed Successfully!</h2>
                <p>Great news! All parties have signed the roommate agreement: <em>{agreement_title}</em></p>
                <p>You can download your signed agreement using the button below:</p>
                <p style="text-align: center; margin: 30px 0;">
                    <a href="{download_link}" style="background-color: #4CAF50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">Download Signed Agreement</a>
                </p>
                <p>Keep this document in a safe place for your records.</p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #999; font-size: 12px;">
                    Thank you for using Roommate Agreement Generator.
                </p>
            </div>
        </body>
        </html>
        """
        
        body_plain = f"""
🎉 Agreement Signed Successfully!

Great news! All parties have signed the roommate agreement: {agreement_title}

You can download your signed agreement here:
{download_link}

Keep this document in a safe place for your records.

---
Thank you for using Roommate Agreement Generator.
        """
        
        return self.send_email(
            to=to_emails,
            subject=subject,
            body_html=body_html,
            body_plain=body_plain
        )
    
    def send_verification_code(
        self,
        to_email: str,
        code: str,
        purpose: str = "verify your email"
    ) -> Dict[str, Any]:
        """
        Send a verification code email.
        
        Args:
            to_email: Recipient email
            code: Verification code
            purpose: Purpose of the verification (e.g., "verify your email", "reset your password")
            
        Returns:
            Dict with success status and message details
        """
        subject = f"Your Verification Code - {code}"
        
        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #3498db;">Verification Code</h2>
                <p>Use the following code to {purpose}:</p>
                <p style="text-align: center; margin: 30px 0;">
                    <span style="font-size: 32px; font-weight: bold; letter-spacing: 8px; background-color: #f8f9fa; padding: 15px 30px; border-radius: 8px; display: inline-block;">{code}</span>
                </p>
                <p style="color: #666;">This code will expire in 15 minutes.</p>
                <p style="color: #666;">If you didn't request this code, please ignore this email.</p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #999; font-size: 12px;">
                    This email was sent by Roommate Agreement Generator.
                </p>
            </div>
        </body>
        </html>
        """
        
        body_plain = f"""
Verification Code

Use the following code to {purpose}:

{code}

This code will expire in 15 minutes.

If you didn't request this code, please ignore this email.

---
This email was sent by Roommate Agreement Generator.
        """
        
        return self.send_email(
            to=[to_email],
            subject=subject,
            body_html=body_html,
            body_plain=body_plain
        )


# Singleton instance
mail_service = MailService()
