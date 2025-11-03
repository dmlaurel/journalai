import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from socket import timeout

logger = logging.getLogger(__name__)

def send_email(to_email, subject, body):
    """Send an email using SMTP"""
    try:
        # Get SMTP configuration from environment variables
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_username = os.getenv('SMTP_USERNAME')
        smtp_password = os.getenv('SMTP_PASSWORD')
        
        logger.info(f"SMTP configuration: server={smtp_server}, port={smtp_port}, username={'*' * (len(smtp_username) if smtp_username else 0)}")
        
        if not smtp_username or not smtp_password:
            raise ValueError("SMTP_USERNAME and SMTP_PASSWORD must be set in environment variables")
        
        # Create message
        logger.info("Creating email message")
        msg = MIMEMultipart()
        msg['From'] = smtp_username
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect to SMTP server and send email with timeout
        logger.info(f"Connecting to SMTP server {smtp_server}:{smtp_port}")
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
        
        try:
            logger.info("Starting TLS")
            server.starttls()  # Enable TLS encryption
            
            logger.info("Logging in to SMTP server")
            server.login(smtp_username, smtp_password)
            
            logger.info("Sending email message")
            server.send_message(msg)
            logger.info("Email sent successfully")
            
            return {'success': True}
        finally:
            logger.info("Closing SMTP connection")
            server.quit()
            
    except timeout as e:
        logger.error(f"SMTP connection timeout: {str(e)}")
        raise Exception(f"SMTP connection timed out: {str(e)}")
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error: {str(e)}")
        raise Exception(f"SMTP error: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}", exc_info=True)
        raise Exception(f"Failed to send email: {str(e)}")

