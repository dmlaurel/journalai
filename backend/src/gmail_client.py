import os
import smtplib
import logging
import requests
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from socket import timeout

logger = logging.getLogger(__name__)

def send_email(to_email, subject, body):
    """
    Send an email using Gmail API, SendGrid API, or SMTP (in that order).
    Gmail API is free and works on cloud platforms like Render.com.
    """
    # Try Gmail API first (free, works on Render.com via HTTPS)
    gmail_client_id = os.getenv('GMAIL_CLIENT_ID')
    gmail_client_secret = os.getenv('GMAIL_CLIENT_SECRET')
    gmail_refresh_token = os.getenv('GMAIL_REFRESH_TOKEN')
    gmail_user_email = os.getenv('GMAIL_USER_EMAIL')
    
    if gmail_client_id and gmail_client_secret and gmail_refresh_token and gmail_user_email:
        try:
            logger.info("Using Gmail API to send email")
            return send_email_gmail_api(to_email, subject, body, gmail_client_id, gmail_client_secret, gmail_refresh_token, gmail_user_email)
        except Exception as e:
            logger.error(f"Gmail API failed: {str(e)}")
            logger.info("Falling back to SendGrid")
    
    # Try SendGrid API second (works on Render.com and other cloud platforms)
    sendgrid_api_key = os.getenv('SENDGRID_API_KEY')
    sendgrid_from_email = os.getenv('SENDGRID_FROM_EMAIL')
    
    if sendgrid_api_key:
        try:
            logger.info("Using SendGrid API to send email")
            return send_email_sendgrid(to_email, subject, body, sendgrid_api_key, sendgrid_from_email)
        except Exception as e:
            logger.error(f"SendGrid API failed: {str(e)}")
            logger.info("Falling back to SMTP")
    
    # Fall back to SMTP (for local development only)
    try:
        logger.info("Using SMTP to send email")
        return send_email_smtp(to_email, subject, body)
    except Exception as e:
        logger.error(f"SMTP failed: {str(e)}")
        raise Exception(f"All email methods failed. Last error: {str(e)}")


def send_email_gmail_api(to_email, subject, body, client_id, client_secret, refresh_token, user_email):
    """Send an email using Gmail API (free, works on Render.com via HTTPS)"""
    logger.info(f"Gmail API: Sending email from {user_email} to {to_email}")
    
    # First, get an access token using the refresh token
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }
    
    logger.info("Gmail API: Getting access token")
    token_response = requests.post(token_url, data=token_data, timeout=10)
    
    if token_response.status_code != 200:
        error_msg = f"Gmail API token error: {token_response.status_code} - {token_response.text}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    access_token = token_response.json()["access_token"]
    
    # Create the email message
    message = MIMEMultipart()
    message['From'] = user_email
    message['To'] = to_email
    message['Subject'] = subject
    message.attach(MIMEText(body, 'plain'))
    
    # Encode the message in base64url format
    raw_message = base64.urlsafe_b64encode(message.as_string().encode('utf-8')).decode('utf-8')
    
    # Send the email using Gmail API
    api_url = f"https://gmail.googleapis.com/gmail/v1/users/{user_email}/messages/send"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "raw": raw_message
    }
    
    logger.info(f"Gmail API: Making API request to {api_url}")
    response = requests.post(api_url, json=payload, headers=headers, timeout=10)
    
    if response.status_code == 200:
        logger.info("Gmail API: Email sent successfully")
        return {'success': True}
    else:
        error_msg = f"Gmail API error: {response.status_code} - {response.text}"
        logger.error(error_msg)
        raise Exception(error_msg)


def send_email_sendgrid(to_email, subject, body, api_key, from_email=None):
    """Send an email using SendGrid API"""
    if not from_email:
        from_email = os.getenv('SENDGRID_FROM_EMAIL') or os.getenv('SMTP_USERNAME') or 'noreply@journie.ai'
    
    logger.info(f"SendGrid: Sending email from {from_email} to {to_email}")
    
    url = "https://api.sendgrid.com/v3/mail/send"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "personalizations": [
            {
                "to": [{"email": to_email}],
                "subject": subject
            }
        ],
        "from": {"email": from_email},
        "content": [
            {
                "type": "text/plain",
                "value": body
            }
        ]
    }
    
    logger.info(f"SendGrid: Making API request to {url}")
    response = requests.post(url, json=payload, headers=headers, timeout=10)
    
    if response.status_code == 202:
        logger.info("SendGrid: Email sent successfully")
        return {'success': True}
    else:
        error_msg = f"SendGrid API error: {response.status_code} - {response.text}"
        logger.error(error_msg)
        raise Exception(error_msg)


def send_email_smtp(to_email, subject, body):
    """Send an email using SMTP (for local development)"""
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

