import argparse
import sys
from dotenv import load_dotenv

from src.twilio_client import TwilioClient


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send a test SMS using TwilioClient"
    )
    parser.add_argument(
        "--to",
        required=True,
        help="Recipient phone number in E.164 format (e.g., +12345556789)",
    )
    parser.add_argument(
        "--body",
        required=True,
        help="Message body to send",
    )
    parser.add_argument(
        "--from",
        dest="from_number",
        required=False,
        help="Sender phone number in E.164 format. Defaults to TWILIO_PHONE_NUMBER",
    )
    return parser.parse_args()


def main() -> int:
    # Load environment variables (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER)
    load_dotenv()

    args = parse_args()

    try:
        client = TwilioClient()
        result = client.send_sms(
            to=args.to,
            body=args.body,
            from_number=args.from_number,
        )
    except Exception as exc:
        print(f"Failed to send SMS: {exc}")
        return 1

    print("SMS sent successfully:")
    print(f"  SID: {result['sid']}")
    print(f"  Status: {result['status']}")
    print(f"  To: {result['to']}")
    print(f"  From: {result['from']}")
    print(f"  Body: {result['body']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())




