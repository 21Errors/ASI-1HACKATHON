"""
EmailSender - Send emails via Gmail SMTP with open tracking
"""
import smtplib
import os
import json
import traceback
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()


class EmailSender:
    """Send pitch emails via Gmail SMTP with open tracking"""
    
    def __init__(self):
        self.gmail_address = os.getenv("GMAIL_ADDRESS", "")
        self.gmail_app_password = os.getenv("GMAIL_APP_PASSWORD", "")
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
    
    def validate_credentials(self) -> Dict:
        """
        Validate Gmail credentials by testing SMTP connection
        
        Returns:
            { valid: bool, email: str, error: str (optional) }
        """
        if not self.gmail_address or not self.gmail_app_password:
            return {
                "valid": False,
                "email": "",
                "error": "GMAIL_ADDRESS or GMAIL_APP_PASSWORD not configured"
            }
        
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10) as server:
                server.starttls()
                server.login(self.gmail_address, self.gmail_app_password)
            
            return {
                "valid": True,
                "email": self.gmail_address
            }
        
        except smtplib.SMTPAuthenticationError:
            return {
                "valid": False,
                "email": self.gmail_address,
                "error": "Authentication failed - check GMAIL_APP_PASSWORD"
            }
        
        except smtplib.SMTPException as e:
            return {
                "valid": False,
                "email": self.gmail_address,
                "error": f"SMTP error: {str(e)}"
            }
        
        except Exception as e:
            return {
                "valid": False,
                "email": self.gmail_address,
                "error": f"Connection error: {str(e)}"
            }
    
    def send_pitch_email(
        self, 
        to_email: str, 
        subject: str, 
        body: str,
        lead_id: str,
        business_name: str
    ) -> Dict:
        """
        Send pitch email via Gmail with open tracking
        
        Args:
            to_email: Recipient email address
            subject: Email subject line
            body: Email body text (plain text, will be wrapped in HTML)
            lead_id: Unique identifier for this lead (for tracking)
            business_name: Name of the business being pitched to
        
        Returns:
            {
                success: bool,
                message_id: str (if successful),
                sent_at: ISO timestamp,
                error: str (if failed)
            }
        """
        
        print(f"[emailer] send_pitch_email() called for {business_name} → {to_email}")
        print(f"[emailer] Gmail configured: {bool(self.gmail_address)}")
        print(f"[emailer] Gmail address: {self.gmail_address if self.gmail_address else 'NOT SET'}")
        
        if not self.gmail_address or not self.gmail_app_password:
            error_msg = "Gmail credentials not configured"
            print(f"[emailer] ✗ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
        
        if not to_email or "@" not in to_email:
            error_msg = "Invalid recipient email address"
            print(f"[emailer] ✗ {error_msg}: {to_email}")
            return {
                "success": False,
                "error": error_msg
            }
        
        try:
            # Create multipart message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.gmail_address
            msg["To"] = to_email
            
            print(f"[emailer] Message created - Subject: {subject[:50]}")
            
            # Create HTML email body with tracking pixel
            html_body = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.5; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto;">
                        {self._escape_html(body)}
                    </div>
                    <img src="http://localhost:8000/api/track/open/{lead_id}" 
                         width="1" height="1" style="display:none;" 
                         alt="" border="0" />
                </body>
            </html>
            """
            
            # Attach HTML part
            html_part = MIMEText(html_body, "html")
            msg.attach(html_part)
            
            print(f"[emailer] Connecting to SMTP server {self.smtp_server}:{self.smtp_port}...")
            
            # Connect to Gmail SMTP and send
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10) as server:
                server.starttls()
                print(f"[emailer] STARTTLS successful, attempting login...")
                server.login(self.gmail_address, self.gmail_app_password)
                print(f"[emailer] ✓ Logged in to Gmail SMTP")
                
                # Send email
                result = server.sendmail(self.gmail_address, to_email, msg.as_string())
                print(f"[emailer] ✓ Email sent successfully (sendmail result: {result})")
            
            # Generate message ID (use timestamp + lead_id)
            message_id = f"{lead_id}_{int(datetime.now().timestamp())}"
            sent_at = datetime.utcnow().isoformat() + "Z"
            
            return {
                "success": True,
                "message_id": message_id,
                "sent_at": sent_at,
                "to_email": to_email,
                "business_name": business_name
            }
        
        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"Gmail authentication failed - check GMAIL_APP_PASSWORD: {str(e)}"
            print(f"[emailer] ✗ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
        
        except smtplib.SMTPException as e:
            error_msg = f"SMTP error: {str(e)}"
            print(f"[emailer] ✗ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
        
        except Exception as e:
            error_msg = f"Failed to send email: {str(e)}"
            print(f"[emailer] ✗ {error_msg}")
            print(f"[emailer] Exception traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": error_msg
            }
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters in text"""
        replacements = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;"
        }
        for char, escaped in replacements.items():
            text = text.replace(char, escaped)
        return text
    
    def format_pitch_email(
        self,
        business_name: str,
        industry: str,
        city: str,
        service: str,
        email_subject: str,
        email_body: str
    ) -> str:
        """
        Format a complete pitch email body
        
        Args:
            business_name: Business being pitched
            industry: Business industry type
            city: Business location
            service: Service being offered
            email_subject: Subject line from ASI-1
            email_body: Body from ASI-1
        
        Returns:
            Formatted HTML email body
        """
        
        return f"""
        <div style="padding: 20px; background-color: #f9f9f9;">
            <h2 style="color: #333; margin-bottom: 5px;">Hello,</h2>
            
            <p style="margin: 15px 0; color: #555;">
                {self._escape_html(email_body)}
            </p>
            
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #888;">
                <p><strong>Business Research Summary:</strong></p>
                <ul style="margin: 5px 0; padding-left: 20px;">
                    <li>Business: {self._escape_html(business_name)}</li>
                    <li>Industry: {self._escape_html(industry)}</li>
                    <li>Location: {self._escape_html(city)}</li>
                    <li>Service Offered: {self._escape_html(service)}</li>
                </ul>
                <p style="margin-top: 15px; color: #999;">
                    This email was generated by Vendly AI with personalized research.
                </p>
            </div>
        </div>
        """
