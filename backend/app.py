from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import argparse
from dotenv import load_dotenv
from src.gmail_client import send_email

load_dotenv()

app = Flask(__name__)
# Configure CORS to allow requests from any origin when deployed (for GitHub Pages)
CORS(app, resources={r"/api/*": {"origins": "*"}})

@app.route('/api/signup', methods=['POST'])
def handle_signup():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        email = data.get('email')
        message = data.get('message')
        
        if not email or not message:
            return jsonify({'error': 'Email and message are required'}), 400
        
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
        send_email(recipient, subject, body)
        
        return jsonify({'success': True, 'message': 'Sign up submitted successfully'}), 200
    
    except FileNotFoundError as e:
        return jsonify({'error': f'Gmail credentials not configured: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Failed to submit sign up: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run Journie Flask server')
    parser.add_argument('--local', action='store_true', help='Run in local mode (localhost:5000)')
    args = parser.parse_args()
    
    if args.local:
        # Local development mode
        app.run(debug=True, host='127.0.0.1', port=5000)
    else:
        # Production mode for Render.com
        port = int(os.environ.get('PORT', 5000))
        app.run(debug=False, host='0.0.0.0', port=port)

