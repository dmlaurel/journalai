"""
Script to fetch the latest conversation transcription from ElevenLabs based on the caller phone number.
"""
import os
import sys
import re
from dotenv import load_dotenv
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


def main():
    """Main function to fetch the latest transcription."""
    print("=" * 60)
    print("ElevenLabs Transcription Fetcher")
    print("=" * 60)
    
    # Initialize client
    try:
        elevenlabs_client = ElevenLabsClient()
        print("✓ Connected to ElevenLabs")
    except Exception as e:
        print(f"❌ Error initializing ElevenLabs client: {e}")
        sys.exit(1)
    
    # Get phone number from user (command line argument or prompt)
    if len(sys.argv) > 1:
        caller_number = sys.argv[1].strip()
        print(f"\n📞 Using phone number from command line: {caller_number}")
    else:
        caller_number = input("\nEnter the caller phone number (e.g., +1234567890 or 2345678901): ").strip()
    
    if not caller_number:
        print("❌ Phone number is required!")
        print("Usage: python fetch_transcription.py [+1234567890]")
        sys.exit(1)
    
    # Format phone number
    try:
        formatted_number = format_phone_number(caller_number)
        print(f"\n📞 Formatted number: {formatted_number}")
    except Exception as e:
        print(f"❌ Error formatting phone number: {e}")
        sys.exit(1)
    
    # Get the latest conversation for this phone number
    print("\n🔍 Searching for latest conversation...")
    try:
        conversation = elevenlabs_client.get_latest_conversation_by_phone_number(formatted_number)
        
        if not conversation:
            print(f"❌ No conversations found for phone number: {formatted_number}")
            print("\n🔍 Debug: Listing available conversations to check phone number formats...")
            try:
                all_conversations = elevenlabs_client.list_conversations(limit=5)  # Limit to 5 to avoid too many API calls
                print(f"\nFound {len(all_conversations)} recent conversations. Fetching full details...")
                for i, conv in enumerate(all_conversations[:5], 1):
                    # Get conversation ID
                    conv_id = getattr(conv, 'conversation_id', None) or getattr(conv, 'id', None) or getattr(conv, 'conversation_uuid', 'Unknown')
                    
                    print(f"\n  Conversation {i}:")
                    print(f"    ID: {conv_id}")
                    
                    # Try to get full conversation details
                    try:
                        full_conv = elevenlabs_client.get_conversation(conv_id)
                        print(f"    ✓ Fetched full details")
                        
                        # Try to extract phone number from various attributes
                        phone_attrs = {}
                        phone_attrs_to_check = ['caller_phone_number', 'phone_number', 'caller', 'from', 'from_phone_number', 'to_phone_number', 'twilio_from', 'twilio_to']
                        
                        for attr in phone_attrs_to_check:
                            if hasattr(full_conv, attr):
                                val = getattr(full_conv, attr)
                                if isinstance(val, str) and val:
                                    phone_attrs[attr] = val
                                elif hasattr(val, 'phone_number'):
                                    phone_attrs[f"{attr}.phone_number"] = val.phone_number
                        
                        # Check metadata
                        if hasattr(full_conv, 'metadata'):
                            if isinstance(full_conv.metadata, dict):
                                for key in ['phone_number', 'caller_phone_number', 'from', 'to']:
                                    if key in full_conv.metadata and full_conv.metadata[key]:
                                        phone_attrs[f"metadata.{key}"] = full_conv.metadata[key]
                            else:
                                for attr in ['phone_number', 'caller_phone_number']:
                                    if hasattr(full_conv.metadata, attr):
                                        phone_attrs[f"metadata.{attr}"] = getattr(full_conv.metadata, attr)
                        
                        # Show all non-private attributes for debugging
                        all_attrs = [a for a in dir(full_conv) if not a.startswith('_')]
                        print(f"    All attributes ({len(all_attrs)}): {', '.join(all_attrs[:20])}")
                        if len(all_attrs) > 20:
                            print(f"    ... and {len(all_attrs) - 20} more")
                        
                        if phone_attrs:
                            print(f"    Phone numbers found:")
                            for key, value in phone_attrs.items():
                                print(f"      {key}: {value}")
                        else:
                            print(f"    ⚠️  No phone number found in any standard attribute")
                            
                            # Deep inspect metadata and conversation_initiation_client_data
                            print(f"    Inspecting metadata and conversation_initiation_client_data...")
                            if hasattr(full_conv, 'metadata') and full_conv.metadata:
                                try:
                                    if isinstance(full_conv.metadata, dict):
                                        print(f"      metadata (dict): {full_conv.metadata}")
                                    else:
                                        # Try to convert to dict
                                        if hasattr(full_conv.metadata, 'dict'):
                                            print(f"      metadata (dict()): {full_conv.metadata.dict()}")
                                        elif hasattr(full_conv.metadata, 'model_dump'):
                                            print(f"      metadata (model_dump()): {full_conv.metadata.model_dump()}")
                                        else:
                                            print(f"      metadata (str): {str(full_conv.metadata)}")
                                except Exception as e:
                                    print(f"      metadata inspection error: {e}")
                            
                            if hasattr(full_conv, 'conversation_initiation_client_data') and full_conv.conversation_initiation_client_data:
                                try:
                                    if isinstance(full_conv.conversation_initiation_client_data, dict):
                                        print(f"      conversation_initiation_client_data (dict): {full_conv.conversation_initiation_client_data}")
                                    else:
                                        if hasattr(full_conv.conversation_initiation_client_data, 'dict'):
                                            print(f"      conversation_initiation_client_data (dict()): {full_conv.conversation_initiation_client_data.dict()}")
                                        elif hasattr(full_conv.conversation_initiation_client_data, 'model_dump'):
                                            print(f"      conversation_initiation_client_data (model_dump()): {full_conv.conversation_initiation_client_data.model_dump()}")
                                        else:
                                            print(f"      conversation_initiation_client_data (str): {str(full_conv.conversation_initiation_client_data)}")
                                except Exception as e:
                                    print(f"      conversation_initiation_client_data inspection error: {e}")
                            
                            # Try to get JSON representation
                            try:
                                if hasattr(full_conv, 'model_dump_json'):
                                    import json
                                    conv_json = json.loads(full_conv.model_dump_json())
                                    # Look for phone-related keys recursively
                                    def find_phone_keys(obj, path=""):
                                        results = []
                                        if isinstance(obj, dict):
                                            for k, v in obj.items():
                                                if 'phone' in k.lower() or 'caller' in k.lower() or 'from' in k.lower() or 'to' in k.lower():
                                                    results.append(f"{path}.{k}: {v}")
                                                if isinstance(v, (dict, list)):
                                                    results.extend(find_phone_keys(v, f"{path}.{k}" if path else k))
                                        elif isinstance(obj, list):
                                            for i, item in enumerate(obj):
                                                results.extend(find_phone_keys(item, f"{path}[{i}]" if path else f"[{i}]"))
                                        return results
                                    
                                    phone_matches = find_phone_keys(conv_json)
                                    if phone_matches:
                                        print(f"    Found phone-related keys in JSON:")
                                        for match in phone_matches:
                                            print(f"      {match}")
                            except Exception as json_e:
                                pass
                            
                            # Show a few key attributes for debugging
                            key_attrs = ['direction', 'caller', 'from', 'to', 'twilio_from', 'twilio_to', 'phone_number_id']
                            for attr in key_attrs:
                                if hasattr(full_conv, attr):
                                    val = getattr(full_conv, attr)
                                    if val:
                                        print(f"      {attr}: {val}")
                    except Exception as fetch_e:
                        print(f"    ❌ Could not fetch full details: {fetch_e}")
                        # Fall back to basic info
                        phone_attrs = {}
                        for attr in ['caller_phone_number', 'phone_number', 'caller']:
                            if hasattr(conv, attr):
                                val = getattr(conv, attr)
                                if isinstance(val, str):
                                    phone_attrs[attr] = val
                                elif hasattr(val, 'phone_number'):
                                    phone_attrs[attr] = val.phone_number
                        if phone_attrs:
                            for key, value in phone_attrs.items():
                                print(f"    {key}: {value}")
                    
                    if hasattr(conv, 'created_at'):
                        print(f"    Created: {conv.created_at}")
                    elif hasattr(conv, 'timestamp'):
                        print(f"    Timestamp: {conv.timestamp}")
            except Exception as debug_e:
                print(f"  Could not list conversations for debugging: {debug_e}")
            
            print(f"\n💡 Tip: Try searching with different phone number formats:")
            print(f"   - With +1: {formatted_number}")
            print(f"   - Without +1: {formatted_number[2:] if formatted_number.startswith('+1') else formatted_number[1:]}")
            print(f"   - Without +: {formatted_number[1:]}")
            sys.exit(1)
        
        # Get conversation ID
        conversation_id = None
        if hasattr(conversation, 'conversation_id'):
            conversation_id = conversation.conversation_id
        elif hasattr(conversation, 'id'):
            conversation_id = conversation.id
        elif hasattr(conversation, 'conversation_uuid'):
            conversation_id = conversation.conversation_uuid
        
        if not conversation_id:
            print("❌ Could not extract conversation ID")
            sys.exit(1)
        
        print(f"✓ Found conversation: {conversation_id}")
        
        # Get transcription
        print("\n📝 Fetching transcription...")
        transcription = elevenlabs_client.get_transcription(conversation_id)
        
        if not transcription:
            print("⚠️  No transcription available for this conversation")
            print("\nConversation details:")
            print(f"  Conversation ID: {conversation_id}")
            if hasattr(conversation, 'created_at'):
                print(f"  Created: {conversation.created_at}")
            elif hasattr(conversation, 'timestamp'):
                print(f"  Timestamp: {conversation.timestamp}")
            sys.exit(0)
        
        # Display transcription
        print("\n" + "=" * 60)
        print("TRANSCRIPTION")
        print("=" * 60)
        print(transcription)
        print("=" * 60)
        
        # Display conversation metadata
        print("\nConversation Details:")
        print(f"  Conversation ID: {conversation_id}")
        if hasattr(conversation, 'created_at'):
            print(f"  Created: {conversation.created_at}")
        elif hasattr(conversation, 'timestamp'):
            print(f"  Timestamp: {conversation.timestamp}")
        if hasattr(conversation, 'status'):
            print(f"  Status: {conversation.status}")
        if hasattr(conversation, 'duration'):
            print(f"  Duration: {conversation.duration}")
        
        print("\n✅ Transcription fetched successfully!")
        
    except Exception as e:
        print(f"❌ Error fetching transcription: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

