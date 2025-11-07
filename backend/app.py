from flask import Flask, request, jsonify, session
from flask_cors import CORS
import os
import argparse
import logging
import threading
from datetime import datetime
from collections import defaultdict
from dotenv import load_dotenv
from src.gmail_client import send_email
from src.auth import request_login_code, verify_login_code, get_user_by_email
from src.db import get_db_connection
from src.twilio_client import TwilioClient
from src.elevenlabs_client import ElevenLabsClient

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
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        phone_number = data.get('phone_number', '').strip()
        message = data.get('message', '').strip()
        
        if not email:
            logger.warning("Missing required field: email")
            return jsonify({'error': 'Email is required'}), 400
        
        if not first_name:
            logger.warning("Missing required field: first_name")
            return jsonify({'error': 'First name is required'}), 400
        
        if not last_name:
            logger.warning("Missing required field: last_name")
            return jsonify({'error': 'Last name is required'}), 400
        
        if not phone_number:
            logger.warning("Missing required field: phone_number")
            return jsonify({'error': 'Phone number is required'}), 400
        
        # Normalize email (lowercase)
        email = email.lower().strip()
        
        logger.info(f"Processing signup for email: {email}")
        
        # Check if user already exists
        try:
            existing_user = get_user_by_email(email)
            if existing_user:
                logger.warning(f"User with email {email} already exists")
                return jsonify({'error': 'An account with this email already exists. Please log in instead.'}), 400
        except Exception as e:
            logger.error(f"Error checking existing user: {str(e)}", exc_info=True)
        
        # Check if phone number is already assigned to another user
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, email FROM users 
                    WHERE phone_number = %s
                """, (phone_number,))
                existing_phone_user = cursor.fetchone()
                cursor.close()
                
                if existing_phone_user:
                    logger.warning(f"Phone number {phone_number} is already assigned to user {existing_phone_user[1]}")
                    return jsonify({'error': 'This phone number is already registered to another account.'}), 400
        except Exception as e:
            logger.error(f"Error checking existing phone number: {str(e)}", exc_info=True)
            return jsonify({'error': 'Failed to validate phone number. Please try again.'}), 500
        
        # Create user in database
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Insert new user
                cursor.execute("""
                    INSERT INTO users (email, first_name, last_name, phone_number, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    RETURNING id, email, first_name, last_name, phone_number, approved
                """, (email, first_name, last_name, phone_number))
                
                user = cursor.fetchone()
                cursor.close()
                
                if not user:
                    raise Exception("Failed to create user")
                
                user_id, user_email, user_first_name, user_last_name, user_phone_number, user_approved = user
                
                # Prepare user data for response
                user_data = {
                    'id': user_id,
                    'email': user_email,
                    'first_name': user_first_name,
                    'last_name': user_last_name,
                    'phone_number': user_phone_number,
                    'approved': user_approved
                }
                
                # Store user info in session
                session['user_id'] = user_id
                session['user_email'] = user_email
                
                logger.info(f"User created successfully: {email}")
                
                # Send notification email asynchronously (optional)
                if message:
                    recipient = os.getenv('RECIPIENT_EMAIL', 'hello@zenbul.com')
                    subject = f"New Journie Sign Up: {email}"
                    body = f"""New sign up for Journie:

Email: {email}
Name: {first_name} {last_name}

How/Why they want to use Journie:
{message}
"""
                    
                    def send_email_async():
                        try:
                            send_email(recipient, subject, body)
                            logger.info("Notification email sent successfully")
                        except Exception as e:
                            logger.error(f"Failed to send notification email: {str(e)}", exc_info=True)
                    
                    email_thread = threading.Thread(target=send_email_async)
                    email_thread.daemon = True
                    email_thread.start()
                
                # Return user data for automatic login
                return jsonify({
                    'success': True,
                    'user': user_data,
                    'message': 'Account created successfully'
                }), 200
                
        except Exception as db_error:
            # Check if it's a unique constraint violation (duplicate email)
            error_str = str(db_error).lower()
            if 'unique' in error_str or 'duplicate' in error_str:
                logger.warning(f"User with email {email} already exists (database constraint)")
                return jsonify({'error': 'An account with this email already exists. Please log in instead.'}), 400
            else:
                logger.error(f"Database error creating user: {str(db_error)}", exc_info=True)
                raise
    
    except Exception as e:
        logger.error(f"Failed to submit sign up: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to create account: {str(e)}'}), 500

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
    """Get user profile by email (for frontend that uses localStorage)"""
    try:
        # Get email from query parameter (frontend uses localStorage, not sessions)
        user_email = request.args.get('email')
        
        if not user_email:
            # Fall back to session if no email provided (for backward compatibility)
            user_id = session.get('user_id')
            user_email = session.get('user_email')
            
            if not user_id or not user_email:
                return jsonify({'error': 'Email is required'}), 400
        
        # Normalize email
        user_email = user_email.lower().strip()
        
        user_data = get_user_by_email(user_email)
        
        if not user_data:
            return jsonify({'error': 'User not found'}), 404
        
        # Log the approval status for debugging
        logger.info(f"User {user_email} approval status: {user_data.get('approved')}")
        
        return jsonify({'user': user_data}), 200
        
    except Exception as e:
        logger.error(f"Failed to get profile: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to get profile: {str(e)}'}), 500

def format_phone_number(phone: str) -> str:
    """Format phone number to E.164 format."""
    import re
    # Remove all non-digit characters except +
    cleaned = re.sub(r'[^\d+]', '', phone)
    
    # If it doesn't start with +, assume US number and add +1
    if not cleaned.startswith('+'):
        if len(cleaned) == 10:
            cleaned = '+1' + cleaned
        elif len(cleaned) == 11 and cleaned[0] == '1':
            cleaned = '+' + cleaned
        else:
            cleaned = '+1' + cleaned
    
    return cleaned

def get_user_conversations_data(user_email: str):
    """
    Get conversation data for a user, grouped by day.
    Returns data in format suitable for plotting.
    """
    try:
        # Get user data
        user_data = get_user_by_email(user_email)
        if not user_data:
            return None
        
        phone_number = user_data.get('phone_number')
        if not phone_number:
            return None
        
        # Format phone number
        formatted_phone = format_phone_number(phone_number)
        
        # Get Twilio call SIDs
        twilio_client = TwilioClient()
        call_sids = set()
        
        # Search calls where the phone number is the recipient (to)
        calls_to = twilio_client.client.calls.list(to=formatted_phone)
        for call in calls_to:
            call_sids.add(call.sid)
        
        # Search calls where the phone number is the caller (from)
        calls_from = twilio_client.client.calls.list(from_=formatted_phone)
        for call in calls_from:
            call_sids.add(call.sid)
        
        if not call_sids:
            return []
        
        # Get ElevenLabs conversations
        elevenlabs_client = ElevenLabsClient()
        conversations = elevenlabs_client.list_conversations(limit=500)
        
        # Import helper functions from find_conversations_by_phone
        import re
        def normalize_phone(phone):
            return re.sub(r'[^\d]', '', str(phone))
        
        def get_elevenlabs_conversation_call_sid(conversation):
            """Extract Twilio call SID from an ElevenLabs conversation object."""
            try:
                if hasattr(conversation, 'conversation_initiation_client_data'):
                    client_data = conversation.conversation_initiation_client_data
                    
                    if isinstance(client_data, dict):
                        dynamic_vars = client_data.get('dynamic_variables', {})
                        if isinstance(dynamic_vars, dict):
                            call_sid = dynamic_vars.get('system__call_sid')
                            if call_sid:
                                return str(call_sid).strip()
                    elif hasattr(client_data, 'dynamic_variables'):
                        dynamic_vars = client_data.dynamic_variables
                        if isinstance(dynamic_vars, dict):
                            call_sid = dynamic_vars.get('system__call_sid')
                        elif hasattr(dynamic_vars, 'system__call_sid'):
                            call_sid = getattr(dynamic_vars, 'system__call_sid')
                        elif hasattr(dynamic_vars, 'system_call_sid'):
                            call_sid = getattr(dynamic_vars, 'system_call_sid')
                        else:
                            call_sid = None
                        
                        if call_sid:
                            return str(call_sid).strip()
                    
                    if hasattr(client_data, 'model_dump'):
                        try:
                            client_data_dict = client_data.model_dump()
                            dynamic_vars = client_data_dict.get('dynamic_variables', {})
                            if isinstance(dynamic_vars, dict):
                                call_sid = dynamic_vars.get('system__call_sid')
                                if call_sid:
                                    return str(call_sid).strip()
                        except:
                            pass
            except:
                pass
            return None
        
        matching_conversations = []
        search_digits = normalize_phone(formatted_phone)
        if formatted_phone.startswith('+1') and len(search_digits) == 11:
            search_variations = [search_digits, search_digits[1:]]
        else:
            search_variations = [search_digits]
        
        for conv in conversations:
            conv_id = getattr(conv, 'conversation_id', None) or getattr(conv, 'id', None) or getattr(conv, 'conversation_uuid', None)
            if not conv_id:
                continue
            
            try:
                full_conv = elevenlabs_client.get_conversation(conv_id)
            except:
                full_conv = conv
            
            twilio_call_sid = get_elevenlabs_conversation_call_sid(full_conv)
            
            if twilio_call_sid and twilio_call_sid in call_sids:
                # Extract datetime
                conv_datetime = None
                datetime_attrs = ['created_at', 'timestamp', 'started_at', 'date_created', 'created', 'start_time', 'updated_at']
                
                for attr in datetime_attrs:
                    if hasattr(full_conv, attr):
                        val = getattr(full_conv, attr)
                        if val:
                            try:
                                if isinstance(val, str):
                                    conv_datetime = datetime.fromisoformat(val.replace('Z', '+00:00'))
                                elif isinstance(val, datetime):
                                    conv_datetime = val
                                else:
                                    conv_datetime = datetime.fromisoformat(str(val).replace('Z', '+00:00'))
                                break
                            except:
                                pass
                
                # Check metadata
                if not conv_datetime and hasattr(full_conv, 'metadata'):
                    try:
                        metadata = full_conv.metadata
                        if isinstance(metadata, dict):
                            for key in ['created_at', 'timestamp', 'started_at', 'date_created', 'start_time']:
                                if key in metadata and metadata[key]:
                                    try:
                                        val = metadata[key]
                                        if isinstance(val, str):
                                            conv_datetime = datetime.fromisoformat(val.replace('Z', '+00:00'))
                                        elif isinstance(val, datetime):
                                            conv_datetime = val
                                        break
                                    except:
                                        pass
                    except:
                        pass
                
                # Fallback to Twilio
                if not conv_datetime and twilio_call_sid:
                    try:
                        twilio_call = twilio_client.client.calls(twilio_call_sid).fetch()
                        if twilio_call.start_time:
                            conv_datetime = twilio_call.start_time
                        elif twilio_call.date_created:
                            conv_datetime = twilio_call.date_created
                    except:
                        pass
                
                # Extract duration
                duration = None
                duration_attrs = ['duration', 'call_duration', 'length', 'call_length']
                
                for attr in duration_attrs:
                    if hasattr(full_conv, attr):
                        val = getattr(full_conv, attr)
                        if val:
                            try:
                                duration = float(val) if val else None
                                if duration:
                                    break
                            except:
                                pass
                
                if not duration and hasattr(full_conv, 'metadata'):
                    try:
                        metadata = full_conv.metadata
                        if isinstance(metadata, dict):
                            for key in ['duration', 'call_duration', 'length']:
                                if key in metadata and metadata[key]:
                                    try:
                                        duration = float(metadata[key])
                                        if duration:
                                            break
                                    except:
                                        pass
                    except:
                        pass
                
                if not duration and twilio_call_sid:
                    try:
                        twilio_call = twilio_client.client.calls(twilio_call_sid).fetch()
                        if twilio_call.duration:
                            duration = float(twilio_call.duration)
                    except:
                        pass
                
                matching_conversations.append({
                    "conversation_id": conv_id,
                    "datetime": conv_datetime,
                    "duration": duration,
                    "twilio_call_sid": twilio_call_sid
                })
        
        # Group by day
        by_day = defaultdict(lambda: {"total_minutes": 0, "conversations": []})
        
        for conv in matching_conversations:
            if conv["datetime"]:
                # Get date as string (YYYY-MM-DD)
                day_key = conv["datetime"].date().isoformat()
                minutes = (conv["duration"] / 60.0) if conv["duration"] else 0
                by_day[day_key]["total_minutes"] += minutes
                by_day[day_key]["conversations"].append({
                    "conversation_id": conv["conversation_id"],
                    "twilio_call_sid": conv["twilio_call_sid"],
                    "duration": conv["duration"],
                    "datetime": conv["datetime"].isoformat() if conv["datetime"] else None
                })
        
        # Convert to list sorted by date
        result = []
        for day in sorted(by_day.keys(), reverse=True):
            result.append({
                "date": day,
                "total_minutes": round(by_day[day]["total_minutes"], 2),
                "conversations": by_day[day]["conversations"]
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting user conversations: {str(e)}", exc_info=True)
        raise

@app.route('/api/user/conversations', methods=['GET'])
def handle_get_conversations():
    """Get conversation data for a user (by email)"""
    try:
        # Get email from query parameter (frontend uses localStorage, not sessions)
        user_email = request.args.get('email')
        
        if not user_email:
            return jsonify({'error': 'Email is required'}), 400
        
        # Normalize email
        user_email = user_email.lower().strip()
        
        # Get user data to check approval status
        user_data = get_user_by_email(user_email)
        if not user_data:
            return jsonify({'error': 'User not found'}), 404
        
        # Only return data if user is approved
        if user_data.get('approved') != 'APPROVED':
            return jsonify({'error': 'User not approved'}), 403
        
        conversations_data = get_user_conversations_data(user_email)
        
        return jsonify({
            'success': True,
            'data': conversations_data or []
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get conversations: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to get conversations: {str(e)}'}), 500

def search_for_summary_recursive(obj, max_depth=10, current_depth=0):
    """Recursively search for summary in any nested structure."""
    if current_depth > max_depth:
        return None
    
    if obj is None:
        return None
    
    # Check if this looks like a summary (string with reasonable length)
    if isinstance(obj, str) and len(obj.strip()) > 20:
        # Check if it contains summary-like keywords
        lower_obj = obj.lower()
        if any(keyword in lower_obj for keyword in ['summary', 'recap', 'overview', 'conclusion', 'key points']):
            return obj
        # Or if it's a longer text that might be a summary
        if len(obj.strip()) > 50:
            return obj
    
    # Check if it's a dict
    if isinstance(obj, dict):
        # Check common summary keys first
        for key in ['summary', 'conversation_summary', 'analysis', 'recap', 'overview', 'conclusion']:
            if key in obj:
                val = obj[key]
                if isinstance(val, str) and val.strip():
                    return val
                result = search_for_summary_recursive(val, max_depth, current_depth + 1)
                if result:
                    return result
        
        # Recursively check all values
        for value in obj.values():
            result = search_for_summary_recursive(value, max_depth, current_depth + 1)
            if result:
                return result
    
    # Check if it's a list
    elif isinstance(obj, list):
        for item in obj:
            result = search_for_summary_recursive(item, max_depth, current_depth + 1)
            if result:
                return result
    
    # Check if it's an object with attributes
    elif hasattr(obj, '__dict__'):
        # Check common summary attributes
        for attr_name in ['summary', 'conversation_summary', 'analysis', 'recap', 'overview', 'conclusion']:
            if hasattr(obj, attr_name):
                try:
                    val = getattr(obj, attr_name)
                    if isinstance(val, str) and val.strip():
                        return val
                    result = search_for_summary_recursive(val, max_depth, current_depth + 1)
                    if result:
                        return result
                except:
                    pass
        
        # Try model_dump or dict method
        if hasattr(obj, 'model_dump'):
            try:
                obj_dict = obj.model_dump()
                return search_for_summary_recursive(obj_dict, max_depth, current_depth + 1)
            except:
                pass
        elif hasattr(obj, 'dict'):
            try:
                obj_dict = obj.dict()
                return search_for_summary_recursive(obj_dict, max_depth, current_depth + 1)
            except:
                pass
    
    return None

@app.route('/api/conversation/details', methods=['GET'])
def handle_get_conversation_details():
    """Get summary and transcript for an ElevenLabs conversation"""
    try:
        conversation_id = request.args.get('conversation_id')
        
        if not conversation_id:
            return jsonify({'error': 'conversation_id is required'}), 400
        
        try:
            elevenlabs_client = ElevenLabsClient()
        except Exception as e:
            raise ValueError(f"Error initializing ElevenLabs client: {e}")
        
        # Get conversation details
        try:
            conversation = elevenlabs_client.get_conversation(conversation_id)
        except Exception as e:
            logger.error(f"Error fetching conversation {conversation_id}: {str(e)}")
            return jsonify({'error': f'Failed to fetch conversation: {str(e)}'}), 500
        
        # Extract summary - try direct attributes first
        summary = None
        summary_attrs = ['summary', 'conversation_summary', 'analysis', 'recap', 'overview', 'conclusion']
        
        for attr in summary_attrs:
            if hasattr(conversation, attr):
                val = getattr(conversation, attr)
                if val:
                    if isinstance(val, str) and val.strip():
                        summary = val
                        break
                    elif hasattr(val, 'text'):
                        summary = val.text
                        break
                    elif hasattr(val, 'summary'):
                        summary = val.summary
                        break
                    elif isinstance(val, dict):
                        summary = val.get('text') or val.get('summary') or str(val)
                        if summary:
                            break
        
        # If not found, recursively search the entire conversation object
        if not summary:
            summary = search_for_summary_recursive(conversation)
        
        # Extract transcript using the existing method
        transcript = None
        try:
            transcript = elevenlabs_client.get_transcription(conversation_id)
        except Exception as e:
            logger.warning(f"Could not fetch transcript: {str(e)}")
        
        # If transcript is still None, try to extract from the conversation object directly
        if not transcript and hasattr(conversation, 'transcript'):
            transcript_obj = conversation.transcript
            if isinstance(transcript_obj, list) and len(transcript_obj) > 0:
                # Try to extract text from each item
                transcript_parts = []
                for item in transcript_obj:
                    # Skip items that are clearly metadata-only (have role but no message)
                    # Check if this item has a role attribute but message is None
                    has_role = False
                    has_message = False
                    message_text = None
                    
                    # Check if item has role attribute
                    if hasattr(item, 'role'):
                        has_role = True
                    
                    # Try to extract message text - ONLY from message attribute
                    if hasattr(item, 'message'):
                        msg_val = getattr(item, 'message')
                        if msg_val and isinstance(msg_val, str) and msg_val.strip():
                            message_text = msg_val.strip()
                            has_message = True
                    
                    # If item has role but no message, skip it entirely (it's metadata)
                    if has_role and not has_message:
                        continue
                    
                    # Only proceed if we have actual message text
                    if not message_text:
                        # Try other text attributes as fallback, but be strict
                        for attr in ['text', 'content']:
                            if hasattr(item, attr):
                                val = getattr(item, attr)
                                if val and isinstance(val, str) and val.strip():
                                    message_text = val.strip()
                                    break
                    
                    # If still no text, try model_dump but ONLY extract message/text/content
                    if not message_text and hasattr(item, 'model_dump'):
                        try:
                            item_dict = item.model_dump()
                            # Only extract from message, text, or content - nothing else
                            message_text = (item_dict.get('message') or 
                                           item_dict.get('text') or 
                                           item_dict.get('content'))
                            if message_text:
                                message_text = str(message_text).strip()
                                # If it's still an object representation, skip it
                                if message_text.startswith("role=") or 'AgentMetadata(' in message_text:
                                    message_text = None
                        except:
                            pass
                    
                    # Try dict access as last resort
                    if not message_text and isinstance(item, dict):
                        message_text = (item.get('message') or 
                                       item.get('text') or 
                                       item.get('content'))
                        if message_text:
                            message_text = str(message_text).strip()
                            # If it's an object representation, skip it
                            if message_text.startswith("role=") or 'AgentMetadata(' in message_text:
                                message_text = None
                    
                    # Only add if we have actual message text (not None, not empty, not object representation)
                    if message_text and len(message_text) > 0:
                        # Final check - filter out any object representations that slipped through
                        is_object_repr = False
                        
                        # Check for Pydantic model representations
                        if message_text.startswith("role="):
                            is_object_repr = True
                        elif 'role=' in message_text and ('agent_metadata=' in message_text or 'AgentMetadata(' in message_text):
                            is_object_repr = True
                        elif 'ConversationHistoryTranscriptToolCallCommonModel(' in message_text:
                            is_object_repr = True
                        elif 'ConversationHistoryTranscriptOtherToolsResultCommonModel(' in message_text:
                            is_object_repr = True
                        elif 'ConversationTurnMetrics(' in message_text:
                            is_object_repr = True
                        elif 'LlmUsageOutput(' in message_text or 'LlmInputOutputTokensUsage(' in message_text:
                            is_object_repr = True
                        elif 'MetricRecord(' in message_text:
                            is_object_repr = True
                        # Check for patterns like: role='agent' agent_metadata=...
                        elif (message_text.count("=") > 3 and message_text.count("(") > 0 and message_text.count(")") > 0):
                            # If it looks like a Python object representation, skip it
                            if any(keyword in message_text for keyword in ['agent_metadata', 'tool_calls', 'tool_results', 'conversation_turn_metrics', 'llm_usage', 'time_in_call_secs']):
                                is_object_repr = True
                        
                        if not is_object_repr:
                            transcript_parts.append(message_text)
                
                if transcript_parts:
                    # Join and clean up the transcript
                    full_transcript = '\n'.join(transcript_parts)
                    # Remove any remaining object representations that might have slipped through
                    lines = full_transcript.split('\n')
                    cleaned_lines = []
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        # Skip lines that look like object representations
                        if (line.startswith("role=") or 
                            'AgentMetadata(' in line or 
                            'ConversationHistoryTranscript' in line or
                            'ConversationTurnMetrics(' in line or
                            'LlmUsageOutput(' in line or
                            'MetricRecord(' in line or
                            ('agent_metadata=' in line and '=' in line and '(' in line) or
                            ('tool_calls=' in line and '[' in line) or
                            ('tool_results=' in line and '[' in line) or
                            ('conversation_turn_metrics=' in line) or
                            ('llm_usage=' in line) or
                            ('time_in_call_secs=' in line)):
                            continue
                        cleaned_lines.append(line)
                    transcript = '\n'.join(cleaned_lines)
                    
                # Log for debugging
                if transcript_obj and len(transcript_obj) > 0:
                    first_item = transcript_obj[0]
                    logger.info(f"Transcript list item type: {type(first_item).__name__}")
                    if hasattr(first_item, '__dict__'):
                        item_attrs = [a for a in dir(first_item) if not a.startswith('_')]
                        logger.info(f"Transcript item has {len(item_attrs)} attributes: {item_attrs[:10]}")
                        # Try common text attributes
                        for attr in ['text', 'content', 'message', 'transcript', 'transcription']:
                            if hasattr(first_item, attr):
                                val = getattr(first_item, attr)
                                logger.info(f"  {attr}: {type(val).__name__} - {str(val)[:100] if val else 'None'}")
        
        # Check analysis object for transcript_summary
        if not summary and hasattr(conversation, 'analysis'):
            try:
                analysis = conversation.analysis
                if hasattr(analysis, 'transcript_summary'):
                    summary = analysis.transcript_summary
                elif hasattr(analysis, 'summary'):
                    summary = analysis.summary
                elif isinstance(analysis, dict):
                    summary = analysis.get('transcript_summary') or analysis.get('summary')
            except:
                pass
        
        # Log for debugging
        logger.info(f"Conversation {conversation_id} - Summary found: {summary is not None}, Transcript found: {transcript is not None}")
        
        # Debug: Log all attributes of the conversation object
        try:
            attrs = [a for a in dir(conversation) if not a.startswith('_')]
            logger.info(f"Conversation {conversation_id} has {len(attrs)} attributes")
            # Log a few key attributes
            for attr in ['summary', 'transcript', 'transcription', 'analysis', 'metadata']:
                if hasattr(conversation, attr):
                    val = getattr(conversation, attr)
                    logger.info(f"  {attr}: {type(val).__name__} - {str(val)[:100] if val else 'None'}")
        except:
            pass
        
        return jsonify({
            'success': True,
            'summary': summary,
            'transcript': transcript
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get conversation details: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to get conversation details: {str(e)}'}), 500

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

