from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
from src.gmail_client import send_email

load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend requests

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
    app.run(debug=True, port=5000)

