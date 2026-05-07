"""
Email Service for MediFlow System

This service handles all email communications including:
- Password reset emails
- Email verification emails
- Welcome emails
- Notification emails
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, Dict, Any
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class EmailService:
    """Service for sending emails via SMTP."""
    
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.from_email = os.getenv("FROM_EMAIL", "noreply@mediflow.com")
        self.from_name = os.getenv("FROM_NAME", "MediFlow Team")
        
        # Validate configuration
        if not all([self.smtp_username, self.smtp_password]):
            logger.warning("Email service not fully configured - using demo mode")
            self.demo_mode = True
        else:
            self.demo_mode = False
    
    async def send_password_reset(self, email: str, token: str, user_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Send password reset email.
        
        Args:
            email: Recipient email address
            token: Password reset token
            user_name: Optional user's first name
            
        Returns:
            Dict with email delivery status
        """
        reset_link = f"https://app.mediflow.com/reset-password?token={token}"
        
        # Personalize greeting
        greeting = f"Hello {user_name}," if user_name else "Hello,"
        
        subject = "Reset Your MediFlow Password"
        
        # HTML email template
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Reset Your MediFlow Password</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f8f9fa;
                }}
                .container {{
                    background-color: #ffffff;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                }}
                .logo {{
                    font-size: 28px;
                    font-weight: bold;
                    color: #6366f1;
                    margin-bottom: 10px;
                }}
                .button {{
                    display: inline-block;
                    background-color: #6366f1;
                    color: white;
                    padding: 12px 30px;
                    text-decoration: none;
                    border-radius: 5px;
                    font-weight: bold;
                    margin: 20px 0;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #eee;
                    font-size: 12px;
                    color: #666;
                    text-align: center;
                }}
                .security {{
                    background-color: #fff3cd;
                    border: 1px solid #ffeaa7;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">🏥 MediFlow</div>
                    <h2>Reset Your Password</h2>
                </div>
                
                <p>{greeting}</p>
                
                <p>We received a request to reset your password for your MediFlow account. If you didn't make this request, you can safely ignore this email.</p>
                
                <div class="security">
                    <strong>🔒 Security Notice:</strong> This link will expire in <strong>1 hour</strong> for your security.
                </div>
                
                <p style="text-align: center;">
                    <a href="{reset_link}" class="button">Reset Password</a>
                </p>
                
                <p>If the button above doesn't work, you can copy and paste this link into your browser:</p>
                <p style="word-break: break-all; background-color: #f8f9fa; padding: 10px; border-radius: 5px;">
                    {reset_link}
                </p>
                
                <div class="footer">
                    <p>This is an automated message from MediFlow Healthcare Platform.</p>
                    <p>© 2024 MediFlow. All rights reserved.</p>
                    <p>If you have questions, contact our support team at support@mediflow.com</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text version
        text_body = f"""
        Reset Your MediFlow Password
        
        {greeting}
        
        We received a request to reset your password for your MediFlow account. If you didn't make this request, you can safely ignore this email.
        
        SECURITY NOTICE: This link will expire in 1 hour for your security.
        
        Reset your password here: {reset_link}
        
        If the link doesn't work, copy and paste it into your browser.
        
        This is an automated message from MediFlow Healthcare Platform.
        © 2024 MediFlow. All rights reserved.
        """
        
        return await self._send_email(email, subject, html_body, text_body)
    
    async def send_email_verification(self, email: str, token: str, user_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Send email verification email.
        
        Args:
            email: Recipient email address
            token: Email verification token
            user_name: Optional user's first name
            
        Returns:
            Dict with email delivery status
        """
        verification_link = f"https://app.mediflow.com/verify-email?token={token}"
        
        greeting = f"Hello {user_name}," if user_name else "Hello,"
        
        subject = "Verify Your MediFlow Email"
        
        # HTML email template
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Verify Your MediFlow Email</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f8f9fa;
                }}
                .container {{
                    background-color: #ffffff;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                }}
                .logo {{
                    font-size: 28px;
                    font-weight: bold;
                    color: #6366f1;
                    margin-bottom: 10px;
                }}
                .button {{
                    display: inline-block;
                    background-color: #10b981;
                    color: white;
                    padding: 12px 30px;
                    text-decoration: none;
                    border-radius: 5px;
                    font-weight: bold;
                    margin: 20px 0;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #eee;
                    font-size: 12px;
                    color: #666;
                    text-align: center;
                }}
                .benefits {{
                    background-color: #e8f5e8;
                    border: 1px solid #10b981;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">🏥 MediFlow</div>
                    <h2>Verify Your Email Address</h2>
                </div>
                
                <p>{greeting}</p>
                
                <p>Thank you for registering with MediFlow! Please verify your email address to complete your registration and unlock all features.</p>
                
                <div class="benefits">
                    <strong>✅ Benefits of verification:</strong>
                    <ul>
                        <li>Access to all MediFlow features</li>
                        <li>Enhanced security for your account</li>
                        <li>Priority support from our team</li>
                        <li>Important healthcare notifications</li>
                    </ul>
                </div>
                
                <p style="text-align: center;">
                    <a href="{verification_link}" class="button">Verify Email</a>
                </p>
                
                <p>If the button above doesn't work, you can copy and paste this link into your browser:</p>
                <p style="word-break: break-all; background-color: #f8f9fa; padding: 10px; border-radius: 5px;">
                    {verification_link}
                </p>
                
                <p><strong>Note:</strong> This verification link will expire in 24 hours.</p>
                
                <div class="footer">
                    <p>This is an automated message from MediFlow Healthcare Platform.</p>
                    <p>© 2024 MediFlow. All rights reserved.</p>
                    <p>If you have questions, contact our support team at support@mediflow.com</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text version
        text_body = f"""
        Verify Your MediFlow Email
        
        {greeting}
        
        Thank you for registering with MediFlow! Please verify your email address to complete your registration.
        
        Benefits of verification:
        - Access to all MediFlow features
        - Enhanced security for your account
        - Priority support from our team
        - Important healthcare notifications
        
        Verify your email here: {verification_link}
        
        If the link doesn't work, copy and paste it into your browser.
        
        Note: This verification link will expire in 24 hours.
        
        This is an automated message from MediFlow Healthcare Platform.
        © 2024 MediFlow. All rights reserved.
        """
        
        return await self._send_email(email, subject, html_body, text_body)
    
    async def send_welcome_email(self, email: str, user_name: str, facility_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Send welcome email to new users.
        
        Args:
            email: Recipient email address
            user_name: User's first name
            facility_name: Optional facility name
            
        Returns:
            Dict with email delivery status
        """
        subject = "Welcome to MediFlow Healthcare Platform"
        
        greeting = f"Hello {user_name},"
        
        facility_text = f"at {facility_name}" if facility_name else ""
        
        # HTML email template
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Welcome to MediFlow</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f8f9fa;
                }}
                .container {{
                    background-color: #ffffff;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                }}
                .logo {{
                    font-size: 28px;
                    font-weight: bold;
                    color: #6366f1;
                    margin-bottom: 10px;
                }}
                .button {{
                    display: inline-block;
                    background-color: #6366f1;
                    color: white;
                    padding: 12px 30px;
                    text-decoration: none;
                    border-radius: 5px;
                    font-weight: bold;
                    margin: 20px 0;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #eee;
                    font-size: 12px;
                    color: #666;
                    text-align: center;
                }}
                .features {{
                    background-color: #f0f9ff;
                    border: 1px solid #0ea5e9;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">🏥 MediFlow</div>
                    <h2>Welcome to MediFlow!</h2>
                </div>
                
                <p>{greeting}</p>
                
                <p>Welcome to MediFlow Healthcare Platform {facility_text}! We're excited to have you join our community of healthcare professionals.</p>
                
                <div class="features">
                    <strong>🚀 What you can do with MediFlow:</strong>
                    <ul>
                        <li>Create and manage patient referrals efficiently</li>
                        <li>Use AI-powered medical document processing</li>
                        <li>Record and transcribe voice notes automatically</li>
                        <li>Collaborate with healthcare facilities worldwide</li>
                        <li>Access comprehensive audit trails and compliance tools</li>
                    </ul>
                </div>
                
                <p style="text-align: center;">
                    <a href="https://app.mediflow.com/login" class="button">Get Started</a>
                </p>
                
                <p><strong>Next Steps:</strong></p>
                <ol>
                    <li>Log in to your account</li>
                    <li>Complete your profile setup</li>
                    <li>Explore the dashboard features</li>
                    <li>Start your first referral</li>
                </ol>
                
                <div class="footer">
                    <p>This is an automated message from MediFlow Healthcare Platform.</p>
                    <p>© 2024 MediFlow. All rights reserved.</p>
                    <p>Need help? Contact our support team at support@mediflow.com</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text version
        text_body = f"""
        Welcome to MediFlow Healthcare Platform
        
        {greeting}
        
        Welcome to MediFlow Healthcare Platform {facility_text}! We're excited to have you join our community of healthcare professionals.
        
        What you can do with MediFlow:
        - Create and manage patient referrals efficiently
        - Use AI-powered medical document processing
        - Record and transcribe voice notes automatically
        - Collaborate with healthcare facilities worldwide
        - Access comprehensive audit trails and compliance tools
        
        Get started here: https://app.mediflow.com/login
        
        Next Steps:
        1. Log in to your account
        2. Complete your profile setup
        3. Explore the dashboard features
        4. Start your first referral
        
        This is an automated message from MediFlow Healthcare Platform.
        © 2024 MediFlow. All rights reserved.
        """
        
        return await self._send_email(email, subject, html_body, text_body)
    
    async def _send_email(self, to_email: str, subject: str, html_body: str, text_body: str) -> Dict[str, Any]:
        """
        Send email using SMTP.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body
            
        Returns:
            Dict with email delivery status
        """
        start_time = datetime.utcnow()
        
        try:
            # Demo mode - log email instead of sending
            if self.demo_mode:
                logger.info(f"DEMO MODE - Email to {to_email}: {subject}")
                logger.info(f"HTML body preview: {html_body[:200]}...")
                return {
                    "success": True,
                    "message": "Email logged in demo mode",
                    "to_email": to_email,
                    "subject": subject,
                    "sent_at": start_time.isoformat(),
                    "demo_mode": True
                }
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Attach both plain text and HTML versions
            text_part = MIMEText(text_body, 'plain', 'utf-8')
            html_part = MIMEText(html_body, 'html', 'utf-8')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(f"Email sent successfully to {to_email} in {duration:.2f}s")
            
            return {
                "success": True,
                "message": "Email sent successfully",
                "to_email": to_email,
                "subject": subject,
                "sent_at": start_time.isoformat(),
                "duration_seconds": duration,
                "demo_mode": False
            }
            
        except Exception as e:
            error_msg = f"Failed to send email to {to_email}: {str(e)}"
            logger.error(error_msg)
            
            return {
                "success": False,
                "message": error_msg,
                "to_email": to_email,
                "subject": subject,
                "attempted_at": start_time.isoformat(),
                "error": str(e),
                "demo_mode": self.demo_mode
            }
    
    def test_email_configuration(self) -> Dict[str, Any]:
        """
        Test email service configuration.
        
        Returns:
            Dict with configuration test results
        """
        results = {
            "configured": not self.demo_mode,
            "smtp_server": self.smtp_server,
            "smtp_port": self.smtp_port,
            "smtp_username": self.smtp_username,
            "from_email": self.from_email,
            "from_name": self.from_name,
            "demo_mode": self.demo_mode
        }
        
        if self.demo_mode:
            results["message"] = "Email service is in demo mode - configure SMTP credentials to enable sending"
        else:
            results["message"] = "Email service is configured and ready to send emails"
        
        return results
