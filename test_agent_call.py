"""
Test script to initiate a phone call through ElevenLabs agent.
"""
import os
import sys
import re
from dotenv import load_dotenv
from src.elevenlabs_client import ElevenLabsClient
from src.twilio_client import TwilioClient

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


def main():
    """Main function to initiate the agent call."""
    print("=" * 60)
    print("ElevenLabs Agent Call Test")
    print("=" * 60)
    
    # Initialize clients
    try:
        elevenlabs_client = ElevenLabsClient()
        twilio_client = TwilioClient()
    except Exception as e:
        print(f"❌ Error initializing clients: {e}")
        sys.exit(1)
    
    # Get phone number from user (command line argument or prompt)
    print(f"\nYour Twilio phone number: {twilio_client.phone_number}")
    print(f"Agent ID: {AGENT_ID}\n")
    
    if len(sys.argv) > 1:
        recipient_number = sys.argv[1].strip()
        print(f"Using phone number from command line: {recipient_number}")
    else:
        recipient_number = input("Enter the phone number to call (e.g., +1234567890 or 2345678901): ").strip()
    
    if not recipient_number:
        print("❌ Phone number is required!")
        print("Usage: python test_agent_call.py [+1234567890]")
        sys.exit(1)
    
    # Format phone number
    try:
        formatted_number = format_phone_number(recipient_number)
        print(f"\n📞 Formatted number: {formatted_number}")
    except Exception as e:
        print(f"❌ Error formatting phone number: {e}")
        sys.exit(1)
    
    # Get or create phone number in ElevenLabs
    print("\n🔗 Connecting Twilio number to ElevenLabs...")
    try:
        phone_number_id = elevenlabs_client.get_or_create_phone_number(
            twilio_phone_number=twilio_client.phone_number,
            twilio_account_sid=twilio_client.account_sid,
            twilio_auth_token=twilio_client.auth_token,
            label="JournalAI Phone Number"
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
            agent_id=AGENT_ID
        )
        print(f"✓ Agent {AGENT_ID} associated with phone number")
    except Exception as e:
        print(f"⚠️  Could not associate agent (may already be associated): {e}")
    
    # Make the call using ElevenLabs' native outbound call API
    # This handles all webhook configuration automatically
    print(f"\n📞 Initiating call to {formatted_number} using ElevenLabs API...")
    print("   This uses ElevenLabs' native Twilio integration")
    try:
        call_response = elevenlabs_client.make_outbound_call(
            agent_id=AGENT_ID,
            phone_number_id=phone_number_id,
            to_number=formatted_number
        )
        
        print("\n✅ Call initiated successfully via ElevenLabs!")
        
        # Extract and display call details
        call_details = {}
        if hasattr(call_response, 'call_sid'):
            call_details['Call SID'] = call_response.call_sid
        if hasattr(call_response, 'status'):
            call_details['Status'] = call_response.status
        if hasattr(call_response, 'to_number'):
            call_details['To'] = call_response.to_number
        if hasattr(call_response, 'from_number'):
            call_details['From'] = call_response.from_number
        
        # Print all available attributes for debugging
        for key, value in call_details.items():
            print(f"   {key}: {value}")
        
        # Print full response if it's a dict
        if isinstance(call_response, dict):
            print(f"\n   Full response: {call_response}")
        else:
            # Try to print model dump
            try:
                print(f"\n   Response type: {type(call_response)}")
                if hasattr(call_response, 'model_dump'):
                    print(f"   Response data: {call_response.model_dump()}")
            except:
                pass
        
        print("\n📱 The call should connect to your ElevenLabs agent shortly!")
        print("   ElevenLabs will handle the webhook configuration automatically.")
        
        # If we have a call_sid, we can check the call status via Twilio
        if hasattr(call_response, 'call_sid') and call_response.call_sid:
            print(f"\n💡 To check call status later, look for Call SID: {call_response.call_sid}")
            print("   View in Twilio Console: https://console.twilio.com/us1/develop/phone-numbers/manage/active")
        
    except Exception as e:
        error_str = str(e)
        print(f"\n❌ Error initiating call: {error_str}")
        
        # Check for common Twilio errors
        if 'not verified' in error_str.lower() or 'unverified' in error_str.lower():
            print("\n⚠️  This might be a number verification issue.")
            print("   For new Twilio accounts, you may need to verify the recipient number.")
        elif 'restricted' in error_str.lower() or 'blocked' in error_str.lower():
            print("\n⚠️  The number might be restricted or blocked.")
        elif 'geographic' in error_str.lower() or 'region' in error_str.lower():
            print("\n⚠️  There might be geographic restrictions on your account.")
        elif 'insufficient' in error_str.lower() or 'balance' in error_str.lower():
            print("\n⚠️  Check your Twilio account balance.")
        
        import traceback
        print("\nFull error traceback:")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

