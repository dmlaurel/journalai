"""
Find all ElevenLabs conversations for a phone number that match Twilio calls.
"""
import os
import sys
import re
import argparse
from datetime import datetime
from dotenv import load_dotenv
from src.twilio_client import TwilioClient
from src.elevenlabs_client import ElevenLabsClient

load_dotenv()


def format_phone_number(phone: str) -> str:
    """Format phone number to E.164 format."""
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


def get_twilio_call_sids(phone_number: str, search_direction: str = "both") -> list:
    """
    Get all Twilio call SIDs for a phone number.
    
    Args:
        phone_number: Phone number in E.164 format
        search_direction: "to", "from", or "both"
    
    Returns:
        List of call SIDs (strings)
    """
    try:
        client = TwilioClient()
    except Exception as e:
        raise ValueError(f"Error initializing Twilio client: {e}")
    
    call_sids = set()  # Use set to avoid duplicates
    
    try:
        # Search calls where the phone number is the recipient (to)
        if search_direction in ["to", "both"]:
            calls_to = client.client.calls.list(to=phone_number)
            for call in calls_to:
                call_sids.add(call.sid)
        
        # Search calls where the phone number is the caller (from)
        if search_direction in ["from", "both"]:
            calls_from = client.client.calls.list(from_=phone_number)
            for call in calls_from:
                call_sids.add(call.sid)
        
        return list(call_sids)
        
    except Exception as e:
        raise Exception(f"Error fetching calls from Twilio API: {e}")


def get_elevenlabs_conversation_call_sid(conversation) -> str:
    """
    Extract Twilio call SID from an ElevenLabs conversation object.
    
    Returns:
        Twilio call SID if found, None otherwise
    """
    try:
        # Check the known path: conversation_initiation_client_data.dynamic_variables.system__call_sid
        if hasattr(conversation, 'conversation_initiation_client_data'):
            client_data = conversation.conversation_initiation_client_data
            
            # Check if it's a dict
            if isinstance(client_data, dict):
                dynamic_vars = client_data.get('dynamic_variables', {})
                if isinstance(dynamic_vars, dict):
                    call_sid = dynamic_vars.get('system__call_sid')
                    if call_sid:
                        return str(call_sid).strip()
            
            # Check if it's an object
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
            
            # Try model_dump if it's a Pydantic model
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


def find_matching_conversations(phone_number: str, twilio_call_sids: set, debug: bool = False) -> list:
    """
    Find ElevenLabs conversations for a phone number that match Twilio call SIDs.
    
    Args:
        phone_number: Phone number in E.164 format
        twilio_call_sids: Set of Twilio call SIDs to match against
        debug: If True, print debug information
    
    Returns:
        List of conversation objects with datetime, duration, and conversation_id
    """
    try:
        elevenlabs_client = ElevenLabsClient()
    except Exception as e:
        raise ValueError(f"Error initializing ElevenLabs client: {e}")
    
    # Get all conversations
    try:
        conversations = elevenlabs_client.list_conversations(limit=500)
    except Exception as e:
        raise Exception(f"Error listing ElevenLabs conversations: {e}")
    
    if debug:
        print(f"   Checking {len(conversations)} ElevenLabs conversations...")
    
    matching_conversations = []
    
    # Normalize phone number for comparison
    def normalize_phone(phone):
        """Normalize phone to digits only for comparison."""
        return re.sub(r'[^\d]', '', str(phone))
    
    search_digits = normalize_phone(phone_number)
    # If search number starts with +1, also try without the 1
    if phone_number.startswith('+1') and len(search_digits) == 11:
        search_variations = [search_digits, search_digits[1:]]  # +18603048753 and 8603048753
    else:
        search_variations = [search_digits]
    
    if debug:
        print(f"   Search variations: {search_variations}")
        print(f"   Looking for Twilio call SIDs: {list(twilio_call_sids)[:5]}..." if len(twilio_call_sids) > 5 else f"   Looking for Twilio call SIDs: {list(twilio_call_sids)}")
    
    # Search through conversations
    # Strategy: First check if Twilio call SID matches (more reliable), then verify phone number
    for idx, conv in enumerate(conversations, 1):
        conv_id = getattr(conv, 'conversation_id', None) or getattr(conv, 'id', None) or getattr(conv, 'conversation_uuid', None)
        if not conv_id:
            continue
        
        if debug and idx <= 10:
            print(f"   [{idx}] Checking conversation: {conv_id}")
        
        # Get full conversation details
        try:
            full_conv = elevenlabs_client.get_conversation(conv_id)
        except:
            full_conv = conv
        
        # FIRST: Extract Twilio call SID from this conversation (more reliable than phone matching)
        twilio_call_sid = get_elevenlabs_conversation_call_sid(full_conv)
        
        if debug and idx <= 10:
            print(f"      Twilio call SID: {twilio_call_sid}")
        
        # Check if this conversation's Twilio call SID matches any of our Twilio calls
        if twilio_call_sid and twilio_call_sid in twilio_call_sids:
            if debug:
                print(f"      ✓ Found matching Twilio call SID: {twilio_call_sid}")
            
            # NOW verify phone number matches (as a double-check)
            caller_phone = None
            phone_attrs_to_check = [
                ('caller_phone_number', lambda x: x),
                ('phone_number', lambda x: x),
                ('from_phone_number', lambda x: x),
                ('twilio_from', lambda x: x),
            ]
            
            # Check direct attributes
            for attr_name, extractor in phone_attrs_to_check:
                if hasattr(full_conv, attr_name):
                    val = getattr(full_conv, attr_name)
                    if val:
                        extracted = extractor(val)
                        if extracted:
                            caller_phone = str(extracted).strip()
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
            
            if debug:
                print(f"      Phone number in conversation: {caller_phone}")
            
            # Check if phone number matches (but don't require it if we have Twilio call SID match)
            phone_matches = True  # Default to True if we can't find phone number
            if caller_phone:
                caller_digits = normalize_phone(caller_phone)
                
                # Check if any variation matches
                phone_matches = False
                for search_var in search_variations:
                    if caller_digits == search_var:
                        phone_matches = True
                        break
                    # Also check if the last 10 digits match
                    if len(caller_digits) >= 10 and len(search_var) >= 10:
                        if caller_digits[-10:] == search_var[-10:]:
                            phone_matches = True
                            break
                
                if debug:
                    print(f"      Phone match: {phone_matches}")
            
            # If Twilio call SID matches, include it (phone number match is optional verification)
            if phone_matches:
                # Extract datetime from ElevenLabs conversation
                conv_datetime = None
                datetime_attrs = ['created_at', 'timestamp', 'started_at', 'date_created', 'created', 'start_time', 'updated_at']
                
                for attr in datetime_attrs:
                    if hasattr(full_conv, attr):
                        val = getattr(full_conv, attr)
                        if val:
                            try:
                                if isinstance(val, str):
                                    # Try ISO format
                                    conv_datetime = datetime.fromisoformat(val.replace('Z', '+00:00'))
                                elif isinstance(val, datetime):
                                    conv_datetime = val
                                else:
                                    # Try to convert
                                    conv_datetime = datetime.fromisoformat(str(val).replace('Z', '+00:00'))
                                break
                            except:
                                pass
                
                # Check metadata for datetime
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
                
                # If still not found, try to get from Twilio call details (fallback)
                if not conv_datetime and twilio_call_sid:
                    try:
                        twilio_client = TwilioClient()
                        twilio_call = twilio_client.client.calls(twilio_call_sid).fetch()
                        # Try start_time first, then date_created
                        if twilio_call.start_time:
                            conv_datetime = twilio_call.start_time
                        elif twilio_call.date_created:
                            conv_datetime = twilio_call.date_created
                    except:
                        pass
                
                # Extract duration (length of call)
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
                
                # Check metadata for duration
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
                
                # If duration not found, try to get from Twilio call details
                if not duration and twilio_call_sid:
                    try:
                        twilio_client = TwilioClient()
                        twilio_call = twilio_client.client.calls(twilio_call_sid).fetch()
                        if twilio_call.duration:
                            duration = float(twilio_call.duration)
                    except:
                        pass
                
                if debug:
                    print(f"      Datetime: {conv_datetime}")
                    print(f"      Duration: {duration}")
                
                matching_conversations.append({
                    "conversation_id": conv_id,
                    "datetime": conv_datetime,
                    "duration": duration,
                    "twilio_call_sid": twilio_call_sid
                })
    
    # Sort by datetime (most recent first)
    matching_conversations.sort(key=lambda x: x["datetime"] or datetime.min, reverse=True)
    
    return matching_conversations


def main():
    """Main function to find matching conversations."""
    parser = argparse.ArgumentParser(
        description="Find all ElevenLabs conversations for a phone number that match Twilio calls"
    )
    parser.add_argument(
        "phone_number",
        help="Phone number to search for (will be formatted to E.164)"
    )
    parser.add_argument(
        "--direction",
        choices=["to", "from", "both"],
        default="both",
        help="Search direction for Twilio calls: 'to' (calls to this number), 'from' (calls from this number), or 'both' (default: both)"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["json", "table", "simple"],
        default="table",
        help="Output format: 'json', 'table', or 'simple' (default: table)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output to see search progress"
    )
    args = parser.parse_args()
    
    try:
        # Format phone number
        formatted_phone = format_phone_number(args.phone_number)
        print("=" * 60)
        print(f"Finding conversations for phone number: {formatted_phone}")
        print("=" * 60)
        
        # Step 1: Get all Twilio call SIDs for this phone number
        print("\n📞 Step 1: Fetching Twilio call SIDs...")
        twilio_call_sids = get_twilio_call_sids(formatted_phone, args.direction)
        print(f"✓ Found {len(twilio_call_sids)} Twilio call(s)")
        
        if not twilio_call_sids:
            print("\n⚠️  No Twilio calls found for this phone number.")
            print("   Cannot match to ElevenLabs conversations without Twilio call SIDs.")
            sys.exit(0)
        
        # Step 2: Find matching ElevenLabs conversations
        print(f"\n🔍 Step 2: Searching ElevenLabs conversations...")
        print(f"   Looking for conversations with phone: {formatted_phone}")
        print(f"   Matching against {len(twilio_call_sids)} Twilio call SIDs...")
        
        matching_conversations = find_matching_conversations(
            formatted_phone, 
            set(twilio_call_sids),
            debug=args.debug
        )
        
        print(f"\n✅ Found {len(matching_conversations)} matching conversation(s)\n")
        
        # Output results
        if args.format == "json":
            import json
            # Convert datetime to ISO format string for JSON
            output = []
            for conv in matching_conversations:
                conv_copy = conv.copy()
                if conv_copy["datetime"]:
                    conv_copy["datetime"] = conv_copy["datetime"].isoformat()
                output.append(conv_copy)
            print(json.dumps(output, indent=2))
        
        elif args.format == "table":
            print(f"{'Conversation ID':<40} {'Datetime':<25} {'Duration (s)':<15} {'Twilio Call SID':<35}")
            print("-" * 115)
            for conv in matching_conversations:
                conv_id = conv["conversation_id"][:38] if len(conv["conversation_id"]) > 38 else conv["conversation_id"]
                dt_str = conv["datetime"].isoformat() if conv["datetime"] else "N/A"
                duration_str = f"{conv['duration']:.1f}" if conv["duration"] else "N/A"
                twilio_sid = conv["twilio_call_sid"][:33] if conv["twilio_call_sid"] and len(conv["twilio_call_sid"]) > 33 else (conv["twilio_call_sid"] or "N/A")
                print(f"{conv_id:<40} {dt_str:<25} {duration_str:<15} {twilio_sid:<35}")
        
        else:  # simple
            for idx, conv in enumerate(matching_conversations, 1):
                print(f"{idx}. Conversation ID: {conv['conversation_id']}")
                print(f"   Datetime: {conv['datetime'].isoformat() if conv['datetime'] else 'N/A'}")
                print(f"   Duration: {conv['duration']:.1f}s" if conv['duration'] else "   Duration: N/A")
                print(f"   Twilio Call SID: {conv['twilio_call_sid'] or 'N/A'}")
                print()
        
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

