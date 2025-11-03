"""
Twilio client for making phone calls and sending SMS messages.
"""
import os
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
from dotenv import load_dotenv

load_dotenv()


class TwilioClient:
    """Client for interacting with Twilio API."""
    
    def __init__(self, account_sid: str = None, auth_token: str = None):
        """
        Initialize Twilio client.
        
        Args:
            account_sid: Twilio Account SID. If not provided, uses TWILIO_ACCOUNT_SID from environment.
            auth_token: Twilio Auth Token. If not provided, uses TWILIO_AUTH_TOKEN from environment.
        """
        self.account_sid = (account_sid or os.getenv("TWILIO_ACCOUNT_SID") or "").strip()
        self.auth_token = (auth_token or os.getenv("TWILIO_AUTH_TOKEN") or "").strip()
        self.phone_number = (os.getenv("TWILIO_PHONE_NUMBER") or "").strip()
        
        if not self.account_sid or not self.auth_token:
            raise ValueError(
                "Twilio credentials are required. Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN environment variables."
            )
        
        self.client = Client(self.account_sid, self.auth_token)
    
    def send_sms(self, to: str, body: str, from_number: str = None) -> dict:
        """
        Send an SMS message.
        
        Args:
            to: Recipient phone number (E.164 format, e.g., +1234567890)
            body: Message body
            from_number: Sender phone number (defaults to TWILIO_PHONE_NUMBER)
            
        Returns:
            Message object from Twilio
        """
        from_number = from_number or self.phone_number
        if not from_number:
            raise ValueError("Twilio phone number is required to send SMS.")
        
        message = self.client.messages.create(
            body=body,
            from_=from_number,
            to=to
        )
        
        return {
            "sid": message.sid,
            "status": message.status,
            "to": message.to,
            "from": message.from_,
            "body": message.body
        }
    
    def make_call(
        self,
        to: str,
        url: str = None,
        twiml: str = None,
        from_number: str = None,
        record: bool = True
    ) -> dict:
        """
        Make a phone call.
        
        Args:
            to: Recipient phone number (E.164 format)
            url: URL to TwiML instructions (preferred over twiml)
            twiml: TwiML string for call instructions
            from_number: Sender phone number (defaults to TWILIO_PHONE_NUMBER)
            record: Whether to record the call
            
        Returns:
            Call object from Twilio
        """
        from_number = from_number or self.phone_number
        if not from_number:
            raise ValueError("Twilio phone number is required to make calls.")
        
        if not url and not twiml:
            raise ValueError("Either 'url' or 'twiml' parameter is required.")
        
        call = self.client.calls.create(
            to=to,
            from_=from_number,
            url=url,
            twiml=twiml,
            record=record
        )
        
        # Note: Some Twilio SDK versions don't expose 'from_' attribute directly
        # We'll use the from_number we passed in, which we know is correct
        call_from = from_number
        
        return {
            "sid": call.sid,
            "status": call.status,
            "to": call.to,
            "from": call_from
        }
    
    def create_voice_response(self, text: str, voice: str = "alice", language: str = "en-US") -> str:
        """
        Create TwiML for a voice call.
        
        Args:
            text: Text to say during the call
            voice: Voice to use (default: alice)
            language: Language code (default: en-US)
            
        Returns:
            TwiML XML string
        """
        response = VoiceResponse()
        response.say(text, voice=voice, language=language)
        return str(response)

