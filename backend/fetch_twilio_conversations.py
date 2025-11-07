"""
Fetch Twilio conversation IDs for a given phone number via Twilio Conversations API.
"""
import os
import sys
import re
import argparse
from dotenv import load_dotenv
import requests
from requests.auth import HTTPBasicAuth
from urllib.parse import urlencode

load_dotenv()

# Environment variables: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_SERVICE_SID
ACCT = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
SERVICE_SID = os.getenv("TWILIO_SERVICE_SID", "").strip()


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


def fetch_conversation_ids(phone_number: str) -> list:
    """
    Fetch all conversation IDs for a given phone number.
    
    Args:
        phone_number: Phone number in E.164 format (e.g., +15551234567)
    
    Returns:
        List of conversation SIDs
    """
    if not ACCT or not TOKEN:
        raise ValueError(
            "Twilio credentials are required. Set TWILIO_ACCOUNT_SID and "
            "TWILIO_AUTH_TOKEN environment variables."
        )
    
    if not SERVICE_SID:
        raise ValueError(
            "TWILIO_SERVICE_SID environment variable is required. "
            "This is your Twilio Conversations Service SID (starts with IS...)."
        )
    
    # Base URL for service-scoped ParticipantConversations
    base_url = f"https://conversations.twilio.com/v1/Services/{SERVICE_SID}/ParticipantConversations"
    
    # Parameters: use Address for SMS/WhatsApp
    params = {"Address": phone_number}
    
    conversation_ids = []
    next_page_url = None
    
    while True:
        # Use next_page_url if available, otherwise use base_url
        url = next_page_url if next_page_url else base_url
        
        try:
            resp = requests.get(
                url,
                auth=HTTPBasicAuth(ACCT, TOKEN),
                params=params if not next_page_url else None,  # Don't pass params if using next_page_url
                timeout=20
            )
            resp.raise_for_status()
            data = resp.json()
            
            # Extract conversation SIDs from the response
            conversations = data.get("conversations", [])
            for item in conversations:
                conversation_sid = item.get("conversationSid")
                if conversation_sid:
                    conversation_ids.append(conversation_sid)
            
            # Check for pagination
            next_page_url = data.get("meta", {}).get("next_page_url")
            if not next_page_url:
                break
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error fetching conversations from Twilio API: {e}")
    
    return conversation_ids


def main():
    """Main function to fetch and display conversation IDs."""
    parser = argparse.ArgumentParser(
        description="Fetch Twilio conversation IDs for a given phone number"
    )
    parser.add_argument(
        "phone_number",
        help="Phone number to search for (will be formatted to E.164)"
    )
    args = parser.parse_args()
    
    try:
        # Format phone number to E.164
        formatted_phone = format_phone_number(args.phone_number)
        print(f"Searching for conversations with phone number: {formatted_phone}")
        print("=" * 60)
        
        # Fetch conversation IDs
        conversation_ids = fetch_conversation_ids(formatted_phone)
        
        if not conversation_ids:
            print(f"No conversations found for {formatted_phone}")
            sys.exit(0)
        
        print(f"\nFound {len(conversation_ids)} conversation(s):\n")
        for idx, conv_id in enumerate(conversation_ids, start=1):
            print(f"{idx}. {conv_id}")
        
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

