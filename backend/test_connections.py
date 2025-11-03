"""
Test script to verify ElevenLabs and Twilio connections are working.
"""
import os
from dotenv import load_dotenv
from src.elevenlabs_client import ElevenLabsClient
from src.twilio_client import TwilioClient

load_dotenv()


def test_elevenlabs():
    """Test ElevenLabs connection and list voices."""
    print("Testing ElevenLabs connection...")
    try:
        client = ElevenLabsClient()
        voices_response = client.list_voices()
        
        # The response structure may vary, handle it flexibly
        voices_list = voices_response.voices if hasattr(voices_response, 'voices') else voices_response
        
        print(f"✓ ElevenLabs connected successfully!")
        print(f"  Available voices: {len(voices_list)}")
        print(f"  Sample voices:")
        for voice in voices_list[:3]:
            name = voice.name if hasattr(voice, 'name') else getattr(voice, 'voice_id', 'Unknown')
            voice_id = voice.voice_id if hasattr(voice, 'voice_id') else 'Unknown'
            print(f"    - {name} (ID: {voice_id})")
        return True
    except Exception as e:
        print(f"✗ ElevenLabs connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_twilio():
    """Test Twilio connection."""
    print("\nTesting Twilio connection...")
    try:
        client = TwilioClient()
        
        # Debug: Check if credentials are loaded (without printing actual values)
        if not client.account_sid or not client.auth_token:
            print(f"✗ Twilio credentials not loaded properly")
            return False
        
        # Try listing incoming phone numbers as a test (less privileged operation)
        try:
            incoming_numbers = client.client.incoming_phone_numbers.list(limit=1)
            account_sid_from_response = client.client.account_sid
            print(f"✓ Twilio connected successfully!")
            print(f"  Account SID: {account_sid_from_response[:10]}...")
            print(f"  Phone Number: {client.phone_number or 'Not configured'}")
            if incoming_numbers:
                print(f"  Found {len(list(client.client.incoming_phone_numbers.list()))} phone number(s) in account")
        except Exception as fetch_error:
            # If account fetch fails, still try TwiML generation as a basic test
            print(f"⚠  Account fetch failed, but testing basic functionality...")
            print(f"  Error: {fetch_error}")
            raise fetch_error
        
        # Test TwiML generation
        twiml = client.create_voice_response("Hello, this is a test.")
        if twiml:
            print(f"  TwiML generation: ✓ Working")
        return True
    except Exception as e:
        print(f"✗ Twilio connection failed: {e}")
        # Check if it's a credential format issue
        import os
        account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        if account_sid:
            print(f"  Account SID length: {len(account_sid)} (should be 34)")
            print(f"  Account SID starts with 'AC': {account_sid.startswith('AC')}")
        if auth_token:
            print(f"  Auth Token length: {len(auth_token)} (should be 32)")
        return False


def main():
    """Run all connection tests."""
    print("=" * 50)
    print("Testing JournalAI Service Connections")
    print("=" * 50)
    
    # Check environment variables
    print("\nChecking environment variables...")
    required_vars = {
        "ELEVENLABS_API_KEY": os.getenv("ELEVENLABS_API_KEY"),
        "TWILIO_ACCOUNT_SID": os.getenv("TWILIO_ACCOUNT_SID"),
        "TWILIO_AUTH_TOKEN": os.getenv("TWILIO_AUTH_TOKEN"),
        "TWILIO_PHONE_NUMBER": os.getenv("TWILIO_PHONE_NUMBER"),
    }
    
    for var, value in required_vars.items():
        if value:
            print(f"  ✓ {var}: {'*' * 10} (configured)")
        else:
            print(f"  ✗ {var}: Not set")
    
    # Test connections
    elevenlabs_ok = test_elevenlabs()
    twilio_ok = test_twilio()
    
    # Summary
    print("\n" + "=" * 50)
    print("Connection Test Summary")
    print("=" * 50)
    print(f"ElevenLabs: {'✓ Connected' if elevenlabs_ok else '✗ Failed'}")
    print(f"Twilio: {'✓ Connected' if twilio_ok else '✗ Failed'}")
    
    if elevenlabs_ok and twilio_ok:
        print("\n🎉 All services connected successfully!")
    else:
        print("\n⚠️  Some services failed to connect. Please check your credentials.")


if __name__ == "__main__":
    main()

