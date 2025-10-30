"""
Check details about a phone number and call attempts.
"""
import os
import sys
from dotenv import load_dotenv
from src.twilio_client import TwilioClient

load_dotenv()


def check_recent_calls(to_number: str = None, limit: int = 10):
    """Check recent calls."""
    try:
        client = TwilioClient()
        
        # Get recent calls
        if to_number:
            calls = client.client.calls.list(to=to_number, limit=limit)
        else:
            calls = client.client.calls.list(limit=limit)
        
        print("=" * 60)
        print("Recent Calls")
        print("=" * 60)
        
        for call in calls:
            call_from = getattr(call, 'from_', getattr(call, 'from_formatted', 'N/A'))
            print(f"\nCall SID: {call.sid}")
            print(f"  Status: {call.status}")
            print(f"  From: {call_from}")
            print(f"  To: {call.to}")
            print(f"  Duration: {call.duration}s" if call.duration else "  Duration: N/A")
            print(f"  Date: {call.date_created}")
            
            if call.status == 'failed' and hasattr(call, 'error_code'):
                print(f"  Error Code: {call.error_code}")
                print(f"  Error Message: {call.error_message}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    to_number = sys.argv[1] if len(sys.argv) > 1 else None
    check_recent_calls(to_number)

