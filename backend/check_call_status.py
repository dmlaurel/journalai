"""
Check the status of a Twilio call by Call SID.
"""
import os
import sys
from dotenv import load_dotenv
from src.twilio_client import TwilioClient

load_dotenv()


def check_call_status(call_sid: str):
    """Check the status of a Twilio call."""
    try:
        client = TwilioClient()
        
        # Fetch the call details
        call = client.client.calls(call_sid).fetch()
        
        print("=" * 60)
        print(f"Call Status: {call_sid}")
        print("=" * 60)
        print(f"Status: {call.status}")
        print(f"Direction: {call.direction}")
        # Handle from_ attribute safely
        call_from = getattr(call, 'from_', getattr(call, 'from_formatted', 'N/A'))
        print(f"From: {call_from}")
        print(f"To: {call.to}")
        print(f"Duration: {call.duration} seconds")
        print(f"Price: ${call.price}" if call.price else "Price: N/A")
        print(f"Start Time: {call.start_time}")
        print(f"End Time: {call.end_time}")
        
        # Check for errors
        if call.status == 'failed':
            print(f"\n❌ Call Failed!")
            print(f"Error Code: {call.error_code}")
            print(f"Error Message: {call.error_message}")
        elif call.status == 'no-answer':
            print(f"\n⚠️  No Answer")
            print("The phone rang but wasn't answered.")
        elif call.status == 'busy':
            print(f"\n⚠️  Busy")
            print("The recipient's phone was busy.")
        elif call.status == 'canceled':
            print(f"\n⚠️  Canceled")
            print("The call was canceled.")
        elif call.status == 'completed':
            print(f"\n✅ Call Completed Successfully")
        elif call.status == 'queued' or call.status == 'ringing':
            print(f"\n🔄 Call in Progress")
            print(f"Current status: {call.status}")
        
        # Get call events for more details
        print(f"\n📋 Call Details:")
        print(f"   Account SID: {call.account_sid}")
        print(f"   Phone Number SID: {call.phone_number_sid}")
        
        # Check if there's additional info
        if hasattr(call, 'answered_by'):
            print(f"   Answered By: {call.answered_by}")
        if hasattr(call, 'caller_name'):
            print(f"   Caller Name: {call.caller_name}")
        
        # Check call outcome
        print(f"\n💡 Call Analysis:")
        if call.status == 'completed' and call.duration and int(call.duration) > 0:
            print(f"   ✅ Call connected and lasted {call.duration} seconds")
            print(f"   This suggests the call went through - possibly to voicemail")
            print(f"   or was answered but phone was on silent/Do Not Disturb")
        elif call.status == 'no-answer':
            print(f"   ⚠️  Phone rang but wasn't answered")
        elif call.status == 'failed':
            print(f"   ❌ Call failed to connect")
            if hasattr(call, 'error_code'):
                print(f"   Error code: {call.error_code}")
                print(f"   Error message: {call.error_message}")
        
    except Exception as e:
        print(f"❌ Error checking call status: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_call_status.py <call_sid>")
        print("Example: python check_call_status.py CA0cc79efb5b1bbb760e72f1d67a892df8")
        sys.exit(1)
    
    call_sid = sys.argv[1]
    check_call_status(call_sid)

