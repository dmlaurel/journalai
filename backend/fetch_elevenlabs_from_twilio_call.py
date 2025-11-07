"""
Fetch corresponding ElevenLabs conversation from a Twilio call SID.
"""
import os
import sys
import argparse
from datetime import datetime, timedelta
from dotenv import load_dotenv
from src.twilio_client import TwilioClient
from src.elevenlabs_client import ElevenLabsClient

load_dotenv()


def get_twilio_call_details(call_sid: str) -> dict:
    """
    Get details of a Twilio call by SID.
    
    Args:
        call_sid: Twilio call SID
    
    Returns:
        Dictionary with call details
    """
    try:
        client = TwilioClient()
        call = client.client.calls(call_sid).fetch()
        
        call_from = getattr(call, 'from_', getattr(call, 'from_formatted', 'N/A'))
        
        return {
            "sid": call.sid,
            "status": call.status,
            "direction": call.direction,
            "from": call_from,
            "to": call.to,
            "duration": call.duration,
            "date_created": call.date_created,
            "start_time": call.start_time,
            "end_time": call.end_time,
        }
    except Exception as e:
        raise Exception(f"Error fetching Twilio call details: {e}")


def search_for_call_sid_recursive(obj, target_sid: str, path: str = "", max_depth: int = 10, current_depth: int = 0):
    """
    Recursively search for Twilio call SID in any nested structure.
    
    Returns:
        Tuple of (found_value, path_where_found) or (None, None)
    """
    if current_depth > max_depth:
        return None, None
    
    if obj is None:
        return None, None
    
    # Check if this is the value we're looking for
    obj_str = str(obj).strip()
    if obj_str == target_sid:
        return obj, path
    
    # Check if it's a dict
    if isinstance(obj, dict):
        for key, value in obj.items():
            # Check the key itself
            if str(key).strip() == target_sid:
                return key, f"{path}.{key}"
            # Recursively check the value
            new_path = f"{path}.{key}" if path else key
            found, found_path = search_for_call_sid_recursive(value, target_sid, new_path, max_depth, current_depth + 1)
            if found:
                return found, found_path
    
    # Check if it's a list
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            new_path = f"{path}[{idx}]" if path else f"[{idx}]"
            found, found_path = search_for_call_sid_recursive(item, target_sid, new_path, max_depth, current_depth + 1)
            if found:
                return found, found_path
    
    # Check if it's an object with attributes
    elif hasattr(obj, '__dict__'):
        for attr_name in dir(obj):
            if attr_name.startswith('_'):
                continue
            try:
                attr_value = getattr(obj, attr_name)
                if callable(attr_value):
                    continue
                new_path = f"{path}.{attr_name}" if path else attr_name
                found, found_path = search_for_call_sid_recursive(attr_value, target_sid, new_path, max_depth, current_depth + 1)
                if found:
                    return found, found_path
            except:
                pass
    
    # Try to convert to dict if it has model_dump or dict method
    if hasattr(obj, 'model_dump'):
        try:
            obj_dict = obj.model_dump()
            return search_for_call_sid_recursive(obj_dict, target_sid, path, max_depth, current_depth + 1)
        except:
            pass
    elif hasattr(obj, 'dict'):
        try:
            obj_dict = obj.dict()
            return search_for_call_sid_recursive(obj_dict, target_sid, path, max_depth, current_depth + 1)
        except:
            pass
    
    return None, None


def find_elevenlabs_conversation_by_call_sid(twilio_call_sid: str, phone_number: str = None, call_timestamp: datetime = None, debug: bool = False) -> dict:
    """
    Find ElevenLabs conversation corresponding to a Twilio call SID.
    
    Args:
        twilio_call_sid: Twilio call SID to search for
        phone_number: Optional phone number to narrow search (from Twilio call)
        call_timestamp: Optional call timestamp to narrow search (from Twilio call)
        debug: If True, print debug information
    
    Returns:
        Dictionary with conversation details or None if not found
    """
    try:
        elevenlabs_client = ElevenLabsClient()
    except Exception as e:
        raise ValueError(f"Error initializing ElevenLabs client: {e}")
    
    # Get all conversations (or recent ones if we have a timestamp)
    limit = 500 if not call_timestamp else 100
    try:
        conversations = elevenlabs_client.list_conversations(limit=limit)
    except Exception as e:
        raise Exception(f"Error listing ElevenLabs conversations: {e}")
    
    print(f"Searching through {len(conversations)} ElevenLabs conversations...")
    
    # Search for conversation with matching Twilio call SID
    for idx, conv in enumerate(conversations, 1):
        conv_id = getattr(conv, 'conversation_id', None) or getattr(conv, 'id', None) or getattr(conv, 'conversation_uuid', None)
        if not conv_id:
            continue
        
        if debug and idx <= 5:  # Debug first 5 conversations
            print(f"  Checking conversation {idx}: {conv_id}")
        
        # Get full conversation details
        try:
            full_conv = elevenlabs_client.get_conversation(conv_id)
        except:
            full_conv = conv
        
        # First, check the known path where Twilio call SID is stored
        # Path: conversation_initiation_client_data.dynamic_variables.system__call_sid
        found_value = None
        found_path = None
        
        try:
            if hasattr(full_conv, 'conversation_initiation_client_data'):
                client_data = full_conv.conversation_initiation_client_data
                
                # Check if it's a dict or object
                if isinstance(client_data, dict):
                    dynamic_vars = client_data.get('dynamic_variables', {})
                    if isinstance(dynamic_vars, dict):
                        found_value = dynamic_vars.get('system__call_sid')
                        if found_value and str(found_value).strip() == twilio_call_sid:
                            found_path = "conversation_initiation_client_data.dynamic_variables.system__call_sid"
                elif hasattr(client_data, 'dynamic_variables'):
                    dynamic_vars = client_data.dynamic_variables
                    if isinstance(dynamic_vars, dict):
                        found_value = dynamic_vars.get('system__call_sid')
                    elif hasattr(dynamic_vars, 'system__call_sid'):
                        found_value = getattr(dynamic_vars, 'system__call_sid')
                    elif hasattr(dynamic_vars, 'system_call_sid'):  # Try without double underscore
                        found_value = getattr(dynamic_vars, 'system_call_sid')
                    
                    if found_value and str(found_value).strip() == twilio_call_sid:
                        found_path = "conversation_initiation_client_data.dynamic_variables.system__call_sid"
                
                # Also try model_dump if it's a Pydantic model
                if not found_value and hasattr(client_data, 'model_dump'):
                    try:
                        client_data_dict = client_data.model_dump()
                        dynamic_vars = client_data_dict.get('dynamic_variables', {})
                        if isinstance(dynamic_vars, dict):
                            found_value = dynamic_vars.get('system__call_sid')
                            if found_value and str(found_value).strip() == twilio_call_sid:
                                found_path = "conversation_initiation_client_data.dynamic_variables.system__call_sid"
                    except:
                        pass
        except Exception as e:
            if debug:
                print(f"  Error checking known path: {e}")
        
        # If not found in known path, fall back to recursive search
        if not found_value:
            if debug:
                print(f"  Not found in known path, trying recursive search...")
            found_value, found_path = search_for_call_sid_recursive(full_conv, twilio_call_sid)
        
        if found_value:
            if debug:
                print(f"  ✓ Found Twilio call SID at: {found_path}")
            return {
                "conversation_id": conv_id,
                "conversation": full_conv,
                "match_method": "twilio_call_sid",
                "twilio_call_sid": found_value,
                "found_path": found_path
            }
        
        # If we have phone number and timestamp, try matching by those (fallback)
        if phone_number and call_timestamp:
            # Extract phone number from conversation
            caller_phone = None
            for attr in ['caller_phone_number', 'phone_number', 'from_phone_number', 'twilio_from']:
                if hasattr(full_conv, attr):
                    val = getattr(full_conv, attr)
                    if val:
                        caller_phone = str(val).strip()
                        break
            
            # Check metadata for phone number
            if not caller_phone and hasattr(full_conv, 'metadata'):
                try:
                    metadata = full_conv.metadata
                    if isinstance(metadata, dict):
                        phone_call = metadata.get('phone_call', {})
                        if isinstance(phone_call, dict):
                            caller_phone = (
                                phone_call.get('external_number') or
                                phone_call.get('caller_number') or
                                phone_call.get('from')
                            )
                except:
                    pass
            
            # Normalize phone numbers for comparison
            def normalize_phone(phone):
                return ''.join(c for c in str(phone) if c.isdigit())
            
            if caller_phone:
                caller_digits = normalize_phone(caller_phone)
                search_digits = normalize_phone(phone_number)
                
                # Check if phone numbers match (last 10 digits)
                if caller_digits[-10:] == search_digits[-10:]:
                    # Check if timestamp is close (within 5 minutes)
                    conv_timestamp = None
                    for attr in ['created_at', 'timestamp', 'started_at']:
                        if hasattr(full_conv, attr):
                            conv_timestamp = getattr(full_conv, attr)
                            break
                    
                    if conv_timestamp:
                        try:
                            # Parse timestamp
                            if isinstance(conv_timestamp, str):
                                conv_dt = datetime.fromisoformat(conv_timestamp.replace('Z', '+00:00'))
                            else:
                                conv_dt = conv_timestamp
                            
                            # Compare timestamps (within 5 minutes)
                            time_diff = abs((conv_dt - call_timestamp).total_seconds())
                            if time_diff < 300:  # 5 minutes
                                return {
                                    "conversation_id": conv_id,
                                    "conversation": full_conv,
                                    "match_method": "phone_and_timestamp",
                                    "phone_match": True,
                                    "time_diff_seconds": time_diff
                                }
                        except:
                            pass
    
    return None


def main():
    """Main function to find ElevenLabs conversation from Twilio call SID."""
    parser = argparse.ArgumentParser(
        description="Find ElevenLabs conversation corresponding to a Twilio call SID"
    )
    parser.add_argument(
        "call_sid",
        help="Twilio call SID (e.g., CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx)"
    )
    parser.add_argument(
        "--details", "-v",
        action="store_true",
        help="Show detailed conversation information"
    )
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Enable debug output to see search progress"
    )
    args = parser.parse_args()
    
    try:
        print("=" * 60)
        print(f"Finding ElevenLabs conversation for Twilio call: {args.call_sid}")
        print("=" * 60)
        
        # Get Twilio call details
        print("\n📞 Fetching Twilio call details...")
        twilio_call = get_twilio_call_details(args.call_sid)
        
        print(f"✓ Found Twilio call:")
        print(f"  From: {twilio_call['from']}")
        print(f"  To: {twilio_call['to']}")
        print(f"  Status: {twilio_call['status']}")
        print(f"  Created: {twilio_call['date_created']}")
        
        # Parse timestamp
        call_timestamp = None
        if twilio_call.get('date_created'):
            try:
                call_timestamp = datetime.fromisoformat(str(twilio_call['date_created']).replace('Z', '+00:00'))
            except:
                pass
        
        # Determine which phone number to search for
        # For outbound calls, search by "to" number
        # For inbound calls, search by "from" number
        search_phone = None
        if twilio_call['direction'] == 'outbound-api' or twilio_call['direction'] == 'outbound-dial':
            search_phone = twilio_call['to']
        else:
            search_phone = twilio_call['from']
        
        # Search for ElevenLabs conversation
        print(f"\n🔍 Searching ElevenLabs conversations...")
        print(f"  Searching for phone: {search_phone}")
        if call_timestamp:
            print(f"  Call timestamp: {call_timestamp}")
        
        result = find_elevenlabs_conversation_by_call_sid(
            args.call_sid,
            phone_number=search_phone,
            call_timestamp=call_timestamp,
            debug=args.debug
        )
        
        if not result:
            print(f"\n❌ No matching ElevenLabs conversation found")
            print(f"\n💡 Tips:")
            print(f"  - The call might not have been made through ElevenLabs")
            print(f"  - The conversation might be older than the search limit")
            print(f"  - Try searching by phone number directly using fetch_transcription.py")
            sys.exit(1)
        
        print(f"\n✅ Found matching ElevenLabs conversation!")
        print(f"  Conversation ID: {result['conversation_id']}")
        print(f"  Match method: {result['match_method']}")
        if 'found_path' in result:
            print(f"  Found at path: {result['found_path']}")
        
        if args.details:
            conv = result['conversation']
            print(f"\n📋 Conversation Details:")
            
            # Show available attributes
            attrs = [a for a in dir(conv) if not a.startswith('_')]
            print(f"  Available attributes: {len(attrs)}")
            
            # Show key attributes
            for attr in ['created_at', 'updated_at', 'status', 'duration', 'caller_phone_number', 'phone_number']:
                if hasattr(conv, attr):
                    val = getattr(conv, attr)
                    print(f"  {attr}: {val}")
            
            # Try to get transcription
            try:
                elevenlabs_client = ElevenLabsClient()
                transcription = elevenlabs_client.get_transcription(result['conversation_id'])
                if transcription:
                    print(f"\n📝 Transcription:")
                    print(f"  {transcription[:500]}..." if len(transcription) > 500 else f"  {transcription}")
            except:
                print(f"\n⚠️  Could not fetch transcription")
        
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

