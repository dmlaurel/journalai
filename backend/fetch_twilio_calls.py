"""
Fetch Twilio call SIDs for a given phone number via Twilio API.
"""
import os
import sys
import re
import argparse
from dotenv import load_dotenv
from src.twilio_client import TwilioClient

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


def fetch_call_sids(phone_number: str, search_direction: str = "both", limit: int = None) -> list:
    """
    Fetch all call SIDs for a given phone number.
    
    Args:
        phone_number: Phone number in E.164 format (e.g., +15551234567)
        search_direction: Which direction to search - "to", "from", or "both" (default: "both")
        limit: Maximum number of calls to return (default: None, returns all)
    
    Returns:
        List of call SIDs with details
    """
    try:
        client = TwilioClient()
    except Exception as e:
        raise ValueError(f"Error initializing Twilio client: {e}")
    
    call_sids = []
    
    try:
        # Search calls where the phone number is the recipient (to)
        if search_direction in ["to", "both"]:
            calls_to = client.client.calls.list(to=phone_number, limit=limit)
            for call in calls_to:
                call_from = getattr(call, 'from_', getattr(call, 'from_formatted', 'N/A'))
                call_sids.append({
                    "sid": call.sid,
                    "direction": "to",
                    "from": call_from,
                    "to": call.to,
                    "status": call.status,
                    "duration": call.duration,
                    "date_created": call.date_created,
                    "date_updated": call.date_updated
                })
        
        # Search calls where the phone number is the caller (from)
        if search_direction in ["from", "both"]:
            calls_from = client.client.calls.list(from_=phone_number, limit=limit)
            for call in calls_from:
                call_from = getattr(call, 'from_', getattr(call, 'from_formatted', 'N/A'))
                call_sids.append({
                    "sid": call.sid,
                    "direction": "from",
                    "from": call_from,
                    "to": call.to,
                    "status": call.status,
                    "duration": call.duration,
                    "date_created": call.date_created,
                    "date_updated": call.date_updated
                })
        
        # Remove duplicates (in case a call appears in both lists)
        seen_sids = set()
        unique_calls = []
        for call in call_sids:
            if call["sid"] not in seen_sids:
                seen_sids.add(call["sid"])
                unique_calls.append(call)
        
        # Sort by date_created (most recent first)
        unique_calls.sort(key=lambda x: x["date_created"], reverse=True)
        
        return unique_calls
        
    except Exception as e:
        raise Exception(f"Error fetching calls from Twilio API: {e}")


def main():
    """Main function to fetch and display call SIDs."""
    parser = argparse.ArgumentParser(
        description="Fetch Twilio call SIDs for a given phone number"
    )
    parser.add_argument(
        "phone_number",
        help="Phone number to search for (will be formatted to E.164)"
    )
    parser.add_argument(
        "--direction", "-d",
        choices=["to", "from", "both"],
        default="both",
        help="Search direction: 'to' (calls to this number), 'from' (calls from this number), or 'both' (default: both)"
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=None,
        help="Maximum number of calls to return (default: all)"
    )
    parser.add_argument(
        "--details", "-v",
        action="store_true",
        help="Show detailed information for each call"
    )
    args = parser.parse_args()
    
    try:
        # Format phone number to E.164
        formatted_phone = format_phone_number(args.phone_number)
        print(f"Searching for calls with phone number: {formatted_phone}")
        print(f"Direction: {args.direction}")
        print("=" * 60)
        
        # Fetch call SIDs
        calls = fetch_call_sids(formatted_phone, args.direction, args.limit)
        
        if not calls:
            print(f"\nNo calls found for {formatted_phone}")
            sys.exit(0)
        
        print(f"\nFound {len(calls)} call(s):\n")
        
        for idx, call in enumerate(calls, start=1):
            if args.details:
                print(f"{idx}. Call SID: {call['sid']}")
                print(f"   Direction: {call['direction']}")
                print(f"   From: {call['from']}")
                print(f"   To: {call['to']}")
                print(f"   Status: {call['status']}")
                print(f"   Duration: {call['duration']}s" if call['duration'] else "   Duration: N/A")
                print(f"   Created: {call['date_created']}")
                print()
            else:
                print(f"{idx}. {call['sid']} ({call['direction']}, {call['status']}, {call['date_created']})")
        
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

