import os
import secrets
import logging
from datetime import datetime, timedelta
from src.db import get_db_connection
from src.gmail_client import send_email

logger = logging.getLogger(__name__)

def generate_one_time_code():
    """Generate a random 6-digit one-time code"""
    return ''.join([str(secrets.randbelow(10)) for _ in range(6)])

def request_login_code(email):
    """
    Request a login code for a user.
    Returns (success, message) tuple.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if user exists
            cursor.execute("SELECT id, first_name, last_name FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            
            if not user:
                cursor.close()
                return False, "Email not found. Please sign up first."
            
            user_id, first_name, last_name = user
            
            # Generate one-time code
            code = generate_one_time_code()
            expiry = datetime.utcnow() + timedelta(minutes=15)
            
            # Update user with code and expiry
            cursor.execute("""
                UPDATE users 
                SET one_time_code = %s, one_time_code_expiry = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (code, expiry, user_id))
            
            cursor.close()
        
        # Send email with code
        user_name = first_name or "there"
        subject = "Your Journie Login Code"
        body = f"""Hi {user_name},

Your login code for Journie is: {code}

This code will expire in 15 minutes.

If you didn't request this code, please ignore this email.

Best,
The Journie Team
"""
        
        try:
            send_email(email, subject, body)
            logger.info(f"Login code sent to {email}")
            return True, "Login code sent to your email"
        except Exception as e:
            logger.error(f"Failed to send login code email: {str(e)}")
            return False, f"Failed to send email: {str(e)}"
            
    except Exception as e:
        logger.error(f"Error requesting login code: {str(e)}", exc_info=True)
        return False, f"Error: {str(e)}"

def verify_login_code(email, code):
    """
    Verify a login code for a user.
    Returns (success, user_data) tuple where user_data is None if unsuccessful.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if user exists and code matches
            cursor.execute("""
                SELECT id, email, first_name, last_name, phone_number, approved, one_time_code, one_time_code_expiry
                FROM users 
                WHERE email = %s AND one_time_code = %s
            """, (email, code))
            
            user = cursor.fetchone()
            
            if not user:
                cursor.close()
                return False, None
            
            user_id, user_email, first_name, last_name, phone_number, approved, stored_code, expiry = user
            
            # Check if code has expired
            if expiry and datetime.utcnow() > expiry:
                cursor.close()
                return False, None
            
            # Clear the one-time code after successful verification
            cursor.execute("""
                UPDATE users 
                SET one_time_code = NULL, one_time_code_expiry = NULL, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (user_id,))
            
            cursor.close()
            
            # Return user data (without sensitive info)
            user_data = {
                'id': user_id,
                'email': user_email,
                'first_name': first_name,
                'last_name': last_name,
                'phone_number': phone_number,
                'approved': approved
            }
            
            logger.info(f"Login successful for {email}")
            return True, user_data
            
    except Exception as e:
        logger.error(f"Error verifying login code: {str(e)}", exc_info=True)
        return False, None

def get_user_by_email(email):
    """Get user by email (for testing/debugging)"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # First, check what database we're connected to
            cursor.execute("SELECT current_database();")
            db_name = cursor.fetchone()[0]
            
            # Now query the user
            cursor.execute("""
                SELECT id, email, first_name, last_name, phone_number, approved
                FROM users 
                WHERE email = %s
            """, (email,))
            user = cursor.fetchone()
            
            if user:
                user_dict = {
                    'id': user[0],
                    'email': user[1],
                    'first_name': user[2],
                    'last_name': user[3],
                    'phone_number': user[4],
                    'approved': user[5]
                }
                # Log for debugging
                logger.info(f"Querying database '{db_name}' - User {email} approval status: {user[5]} (type: {type(user[5])})")
                cursor.close()
                return user_dict
            cursor.close()
            return None
    except Exception as e:
        logger.error(f"Error getting user: {str(e)}", exc_info=True)
        return None

