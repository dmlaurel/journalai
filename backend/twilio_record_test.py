"""
Quick Twilio-only recording sanity test.

Places a call that:
1) Says a brief instruction
2) Records for up to 20s and creates a Twilio Recording

Usage:
  python twilio_record_test.py +12345556789

Check Twilio Console → Monitor → Calls → the call → Recordings.
"""
import os
import sys
from dotenv import load_dotenv
from src.twilio_client import TwilioClient


load_dotenv()


def main():
    if len(sys.argv) < 2:
        print("Usage: python twilio_record_test.py +12345556789")
        sys.exit(1)

    to_number = sys.argv[1].strip()

    try:
        twilio_client = TwilioClient()
    except Exception as e:
        print(f"Error initializing Twilio client: {e}")
        sys.exit(1)

    # Simple TwiML that forces Twilio to record your microphone audio
    twiml = (
        "<Response>"
        "<Say voice=\"alice\" language=\"en-US\">After the beep, please speak for a few seconds, then hang up.</Say>"
        "<Record maxLength=\"20\" playBeep=\"true\" trim=\"do-not-trim\" />"
        "<Say>Thank you. Goodbye.</Say>"
        "</Response>"
    )

    print(f"Placing recording test call to {to_number} from {twilio_client.phone_number}...")
    print("This call will create a Twilio Recording once you hang up.")
    try:
        # Note: record=True here requests Twilio to record the call media too,
        # but the <Record> verb guarantees a recording is created server-side.
        resp = twilio_client.make_call(to=to_number, twiml=twiml, record=True)
        print("Call initiated:")
        print(f"  SID: {resp.get('sid')}")
        print(f"  Status: {resp.get('status')}")
    except Exception as e:
        print(f"Failed to place call: {e}")
        sys.exit(1)

    print("\nAfter the call ends:")
    print("- Go to Twilio Console → Monitor → Calls → your call → Recordings")
    print("- Verify the recording exists and contains your voice audio")


if __name__ == "__main__":
    main()





