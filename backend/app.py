from flask import Flask, request, jsonify, session
from flask_cors import CORS
import os
import argparse
import logging
import threading
from dotenv import load_dotenv
from src.gmail_client import send_email
from src.auth import request_login_code, verify_login_code, get_user_by_email

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24).hex())

# Configure CORS to allow requests from any origin when deployed (for GitHub Pages)
# Use simpler configuration that Flask-CORS handles automatically
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=False)

@app.route('/api/signup', methods=['POST'])
def handle_signup():
    logger.info(f"POST request received from {request.remote_addr}")
    logger.info(f"Headers: {dict(request.headers)}")
    
    try:
        data = request.get_json()
        logger.info(f"Request data: {data}")
        
        if not data:
            logger.warning("No data provided in request")
            return jsonify({'error': 'No data provided'}), 400
        
        email = data.get('email')
        message = data.get('message')
        
        if not email or not message:
            logger.warning(f"Missing required fields - email: {bool(email)}, message: {bool(message)}")
            return jsonify({'error': 'Email and message are required'}), 400
        
        logger.info(f"Processing signup for email: {email}")
        
        # Destination email
        recipient = os.getenv('RECIPIENT_EMAIL', 'hello@zenbul.com')
        
        # Create email content
        subject = f"New Journie Sign Up: {email}"
        body = f"""New sign up for Journie:

Email: {email}

How/Why they want to use Journie:
{message}
"""
        
        # Send email via Gmail API asynchronously to avoid blocking the response
        def send_email_async():
            try:
                logger.info(f"Attempting to send email to {recipient}")
                send_email(recipient, subject, body)
                logger.info("Email sent successfully")
            except Exception as e:
                logger.error(f"Failed to send email asynchronously: {str(e)}", exc_info=True)
        
        # Start email sending in background thread
        email_thread = threading.Thread(target=send_email_async)
        email_thread.daemon = True
        email_thread.start()
        
        # Return success immediately (don't wait for email)
        return jsonify({'success': True, 'message': 'Sign up submitted successfully'}), 200
    
    except FileNotFoundError as e:
        logger.error(f"Gmail credentials not configured: {str(e)}")
        return jsonify({'error': f'Gmail credentials not configured: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"Failed to submit sign up: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to submit sign up: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'}), 200

@app.route('/api/login/request-code', methods=['POST'])
def handle_request_login_code():
    """Request a login code for a user"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        # Normalize email (lowercase)
        email = email.lower().strip()
        
        success, message = request_login_code(email)
        
        if success:
            return jsonify({'success': True, 'message': message}), 200
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        logger.error(f"Failed to request login code: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to request login code: {str(e)}'}), 500

@app.route('/api/login/verify-code', methods=['POST'])
def handle_verify_login_code():
    """Verify a login code for a user"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        email = data.get('email')
        code = data.get('code')
        
        if not email or not code:
            return jsonify({'error': 'Email and code are required'}), 400
        
        # Normalize email (lowercase)
        email = email.lower().strip()
        
        success, user_data = verify_login_code(email, code)
        
        if success and user_data:
            # Store user info in session (for server-side session management if needed)
            session['user_id'] = user_data['id']
            session['user_email'] = user_data['email']
            
            return jsonify({
                'success': True,
                'user': user_data
            }), 200
        else:
            return jsonify({'error': 'Invalid or expired code'}), 401
            
    except Exception as e:
        logger.error(f"Failed to verify login code: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to verify login code: {str(e)}'}), 500

@app.route('/api/user/profile', methods=['GET'])
def handle_get_profile():
    """Get current user profile"""
    try:
        user_id = session.get('user_id')
        user_email = session.get('user_email')
        
        if not user_id or not user_email:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_data = get_user_by_email(user_email)
        
        if not user_data:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({'user': user_data}), 200
        
    except Exception as e:
        logger.error(f"Failed to get profile: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to get profile: {str(e)}'}), 500

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run Journie Flask server')
    parser.add_argument('--local', action='store_true', help='Run in local mode (localhost:5000)')
    args = parser.parse_args()
    
    # Check if running on Render.com (PORT env var is set) or explicitly in local mode
    is_production = os.environ.get('PORT') is not None
    is_local = args.local and not is_production
    
    if is_local:
        # Local development mode
        app.run(debug=True, host='127.0.0.1', port=5000)
    else:
        # Production mode for Render.com
        port = int(os.environ.get('PORT', 5000))
        app.run(debug=False, host='0.0.0.0', port=port)

