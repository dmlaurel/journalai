"""
Debug script to inspect ElevenLabs conversation metadata structure.
"""
import os
import sys
import json
import argparse
from dotenv import load_dotenv
from src.elevenlabs_client import ElevenLabsClient

load_dotenv()


def inspect_conversation(conversation_id: str = None, phone_number: str = None, limit: int = 5):
    """
    Inspect conversation metadata to see what fields are available.
    """
    try:
        client = ElevenLabsClient()
    except Exception as e:
        print(f"❌ Error initializing ElevenLabs client: {e}")
        sys.exit(1)
    
    if conversation_id:
        # Inspect specific conversation
        print(f"Inspecting conversation: {conversation_id}")
        try:
            conv = client.get_conversation(conversation_id)
            print_conversation_details(conv)
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    else:
        # List recent conversations
        print(f"Listing recent conversations (limit: {limit})...")
        try:
            conversations = client.list_conversations(limit=limit)
            print(f"Found {len(conversations)} conversations\n")
            
            for idx, conv in enumerate(conversations, 1):
                conv_id = getattr(conv, 'conversation_id', None) or getattr(conv, 'id', None) or getattr(conv, 'conversation_uuid', 'Unknown')
                print(f"{'='*60}")
                print(f"Conversation {idx}: {conv_id}")
                print(f"{'='*60}")
                print_conversation_details(conv)
                print()
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()


def print_conversation_details(conv):
    """Print all details of a conversation."""
    # Get full conversation if we only have a summary
    try:
        conv_id = getattr(conv, 'conversation_id', None) or getattr(conv, 'id', None) or getattr(conv, 'conversation_uuid', None)
        if conv_id:
            full_conv = conv  # Try to get full details
            try:
                client = ElevenLabsClient()
                full_conv = client.get_conversation(conv_id)
            except:
                pass
        else:
            full_conv = conv
    except:
        full_conv = conv
    
    # Print all attributes
    print("\n📋 All Attributes:")
    attrs = [a for a in dir(full_conv) if not a.startswith('_')]
    for attr in sorted(attrs):
        try:
            val = getattr(full_conv, attr)
            if not callable(val):
                print(f"  {attr}: {type(val).__name__}")
        except:
            pass
    
    # Print metadata in detail
    print("\n📦 Metadata:")
    if hasattr(full_conv, 'metadata'):
        metadata = full_conv.metadata
        print_metadata_recursive(metadata, indent=2)
    else:
        print("  No metadata attribute found")
    
    # Print conversation_initiation_client_data
    print("\n📞 conversation_initiation_client_data:")
    if hasattr(full_conv, 'conversation_initiation_client_data'):
        data = full_conv.conversation_initiation_client_data
        print_metadata_recursive(data, indent=2)
    else:
        print("  No conversation_initiation_client_data attribute found")
    
    # Try to convert to dict and print
    print("\n📄 Full Object (as dict):")
    try:
        if hasattr(full_conv, 'model_dump'):
            obj_dict = full_conv.model_dump()
        elif hasattr(full_conv, 'dict'):
            obj_dict = full_conv.dict()
        else:
            obj_dict = {}
            for attr in attrs:
                try:
                    val = getattr(full_conv, attr)
                    if not callable(val):
                        obj_dict[attr] = str(val)[:100]  # Truncate long values
                except:
                    pass
        
        print(json.dumps(obj_dict, indent=2, default=str)[:2000])  # Limit output
    except Exception as e:
        print(f"  Could not convert to dict: {e}")


def print_metadata_recursive(obj, indent=0, max_depth=5, current_depth=0):
    """Recursively print metadata structure."""
    if current_depth > max_depth:
        print(" " * indent + "... (max depth reached)")
        return
    
    prefix = " " * indent
    
    if obj is None:
        print(prefix + "None")
    elif isinstance(obj, str):
        print(prefix + f'"{obj}"')
    elif isinstance(obj, (int, float, bool)):
        print(prefix + str(obj))
    elif isinstance(obj, dict):
        for key, value in obj.items():
            print(prefix + f"{key}:")
            print_metadata_recursive(value, indent + 2, max_depth, current_depth + 1)
    elif isinstance(obj, list):
        for idx, item in enumerate(obj[:5]):  # Limit to first 5 items
            print(prefix + f"[{idx}]:")
            print_metadata_recursive(item, indent + 2, max_depth, current_depth + 1)
        if len(obj) > 5:
            print(prefix + f"... ({len(obj) - 5} more items)")
    elif hasattr(obj, '__dict__'):
        # Object with attributes
        for key in dir(obj):
            if not key.startswith('_'):
                try:
                    val = getattr(obj, key)
                    if not callable(val):
                        print(prefix + f"{key}:")
                        print_metadata_recursive(val, indent + 2, max_depth, current_depth + 1)
                except:
                    pass
    else:
        print(prefix + str(obj)[:100])


def main():
    parser = argparse.ArgumentParser(
        description="Inspect ElevenLabs conversation metadata structure"
    )
    parser.add_argument(
        "--conversation-id", "-c",
        help="Specific conversation ID to inspect"
    )
    parser.add_argument(
        "--phone-number", "-p",
        help="Phone number to search for (will find latest conversation)"
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=5,
        help="Number of recent conversations to inspect (default: 5)"
    )
    args = parser.parse_args()
    
    if args.conversation_id:
        inspect_conversation(conversation_id=args.conversation_id)
    elif args.phone_number:
        # Find latest conversation for phone number
        try:
            client = ElevenLabsClient()
            conv = client.get_latest_conversation_by_phone_number(args.phone_number)
            if conv:
                conv_id = getattr(conv, 'conversation_id', None) or getattr(conv, 'id', None) or getattr(conv, 'conversation_uuid', None)
                print(f"Found latest conversation for {args.phone_number}: {conv_id}\n")
                inspect_conversation(conversation_id=conv_id)
            else:
                print(f"No conversation found for {args.phone_number}")
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    else:
        inspect_conversation(limit=args.limit)


if __name__ == "__main__":
    main()

