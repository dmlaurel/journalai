"""
Test script to initiate a phone call through ElevenLabs agent.
"""
import os
import sys
import re
import argparse
import time
from dotenv import load_dotenv
from src.elevenlabs_client import ElevenLabsClient
from src.twilio_client import TwilioClient
from src.db import get_db_connection

load_dotenv()

# ElevenLabs Agent ID
AGENT_ID = "agent_5201k8s317vffxfb14sd7zspmd9g"


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


def get_approved_users() -> list:
    """Query database for all users with approved status 'APPROVED' and phone numbers."""
    approved_users = []
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, email, first_name, last_name, phone_number
                FROM users
                WHERE approved = 'APPROVED' AND phone_number IS NOT NULL
                ORDER BY id
            """)
            
            rows = cursor.fetchall()
            for row in rows:
                user_id, email, first_name, last_name, phone_number = row
                approved_users.append({
                    'id': user_id,
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                    'phone_number': phone_number
                })
            
            cursor.close()
    except Exception as e:
        raise Exception(f"Error querying database: {e}")
    
    return approved_users


def main():
    """Main function to initiate agent calls to all approved users."""
    print("=" * 60)
    print("ElevenLabs Agent Multi-Call")
    print("=" * 60)

    # Parse CLI args
    parser = argparse.ArgumentParser(description="Initiate calls to all approved users via ElevenLabs agent")
    parser.add_argument('--agent-id', '-a', default=None,
                        help="ElevenLabs Agent ID (default: uses hardcoded AGENT_ID)")
    parser.add_argument('--label', '-l', default='JournalAI Phone Number',
                        help="Label for phone number in ElevenLabs (default: 'JournalAI Phone Number')")
    args = parser.parse_args()

    # Query approved users from database
    print("\n📊 Querying database for approved users...")
    try:
        approved_users = get_approved_users()
    except Exception as e:
        print(f"❌ Error querying database: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    if not approved_users:
        print("⚠️  No approved users with phone numbers found in database.")
        sys.exit(0)

    print(f"✓ Found {len(approved_users)} approved user(s) with phone numbers")

    # Extract phone numbers from approved users
    numbers = [user['phone_number'] for user in approved_users]
    effective_agent_id = args.agent_id or AGENT_ID
    cfg_label = args.label

    # Initialize clients
    try:
        elevenlabs_client = ElevenLabsClient()
        twilio_client = TwilioClient()
    except Exception as e:
        print(f"❌ Error initializing clients: {e}")
        sys.exit(1)

    print(f"\nYour Twilio phone number: {twilio_client.phone_number}")
    print(f"Agent ID: {effective_agent_id}")

    # Get or create phone number in ElevenLabs
    print("\n🔗 Connecting Twilio number to ElevenLabs...")
    try:
        phone_number_id = elevenlabs_client.get_or_create_phone_number(
            twilio_phone_number=twilio_client.phone_number,
            twilio_account_sid=twilio_client.account_sid,
            twilio_auth_token=twilio_client.auth_token,
            label=cfg_label
        )
        print(f"✓ Phone number connected: {phone_number_id}")
    except Exception as e:
        print(f"❌ Error connecting phone number: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Associate agent with phone number
    print("\n🤖 Associating agent with phone number...")
    try:
        elevenlabs_client.associate_agent_with_phone_number(
            phone_number_id=phone_number_id,
            agent_id=effective_agent_id
        )
        print(f"✓ Agent {effective_agent_id} associated with phone number")
    except Exception as e:
        print(f"⚠️  Could not associate agent (may already be associated): {e}")

    # Iterate over approved users and initiate calls
    total_numbers = len(approved_users)
    print(f"\n📋 Initiating calls to {total_numbers} approved user(s)")
    for idx, user in enumerate(approved_users, start=1):
        raw_number = user['phone_number']
        user_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or user.get('email', 'Unknown')
        
        try:
            formatted_number = format_phone_number(str(raw_number))
        except Exception as e:
            print(f"\n[{idx}] ❌ Skipping invalid number for user {user_name} ({raw_number}): {e}")
            continue

        print(f"\n[{idx}] 📞 Initiating call to {user_name} ({formatted_number}) using ElevenLabs API...")
        try:
            call_response = elevenlabs_client.make_outbound_call(
                agent_id=effective_agent_id,
                phone_number_id=phone_number_id,
                to_number=formatted_number
            )

            print("   ✅ Call initiated successfully")

            call_details = {}
            if hasattr(call_response, 'call_sid'):
                call_details['Call SID'] = call_response.call_sid
            if hasattr(call_response, 'status'):
                call_details['Status'] = call_response.status
            if hasattr(call_response, 'to_number'):
                call_details['To'] = call_response.to_number
            if hasattr(call_response, 'from_number'):
                call_details['From'] = call_response.from_number

            for key, value in call_details.items():
                print(f"   {key}: {value}")

            if hasattr(call_response, 'call_sid') and call_response.call_sid:
                print(f"   View in Twilio Console: https://console.twilio.com/us1/develop/phone-numbers/manage/active")

        except Exception as e:
            error_str = str(e)
            print(f"   ❌ Error initiating call: {error_str}")

            low = error_str.lower()
            if 'not verified' in low or 'unverified' in low:
                print("   ⚠️  This might be a number verification issue in Twilio")
            elif 'restricted' in low or 'blocked' in low:
                print("   ⚠️  The number might be restricted or blocked")
            elif 'geographic' in low or 'region' in low:
                print("   ⚠️  There might be geographic restrictions on your account")
            elif 'insufficient' in low or 'balance' in low:
                print("   ⚠️  Check your Twilio account balance")
            # Wait before attempting the next number
            if idx < total_numbers:
                print("   ⏳ Waiting 3 seconds before next call...")
                time.sleep(3)
            continue

        # Wait before the next call on success as well
        if idx < total_numbers:
            print("   ⏳ Waiting 3 seconds before next call...")
            time.sleep(3)


if __name__ == "__main__":
    main()

