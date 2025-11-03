from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import argparse
import logging
from dotenv import load_dotenv
from src.gmail_client import send_email

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
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
        
        # Send email via Gmail API
        logger.info(f"Attempting to send email to {recipient}")
        send_email(recipient, subject, body)
        logger.info("Email sent successfully")
        
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

