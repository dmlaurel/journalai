# JournalAI

AI-powered journaling assistant that uses ElevenLabs and Twilio to make voice calls to members, prompt them with daily questions, and send summaries via SMS.

## Features

- Voice calls via Twilio with automated prompts
- Text-to-speech using ElevenLabs
- SMS summaries sent to members after journaling
- Database storage for journal entries

## Setup

### Prerequisites

- Python 3.8+
- ElevenLabs API key
- Twilio account with phone number

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd journalai
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
   - Copy `env_template.txt` to `.env`
   - Fill in your API credentials:
     ```bash
     cp env_template.txt .env
     ```
   - Edit `.env` and add your credentials:
     ```
     ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
     TWILIO_ACCOUNT_SID=your_twilio_account_sid_here
     TWILIO_AUTH_TOKEN=your_twilio_auth_token_here
     TWILIO_PHONE_NUMBER=your_twilio_phone_number_here
     ```

### Testing Connections

Test that both services are properly configured:

```bash
python test_connections.py
```

This will verify:
- ElevenLabs API connection
- Available voices
- Twilio account connection
- Twilio phone number configuration

## Project Structure

```
journalai/
├── src/
│   ├── __init__.py
│   ├── elevenlabs_client.py    # ElevenLabs integration
│   └── twilio_client.py         # Twilio integration
├── test_connections.py          # Connection test script
├── requirements.txt             # Python dependencies
├── env_template.txt            # Environment variable template
└── README.md
```

## Usage

### ElevenLabs Client

```python
from src.elevenlabs_client import ElevenLabsClient

client = ElevenLabsClient()
audio = client.generate_speech("Hello, welcome to JournalAI!")
```

### Twilio Client

```python
from src.twilio_client import TwilioClient

client = TwilioClient()
# Send SMS
client.send_sms(to="+1234567890", body="Your journal summary here")

# Make a call
twiml = client.create_voice_response("Please share your thoughts on today's prompt.")
client.make_call(to="+1234567890", twiml=twiml)
```

## Getting API Keys

### ElevenLabs
1. Sign up at https://elevenlabs.io
2. Navigate to your profile settings
3. Copy your API key

### Twilio
1. Sign up at https://www.twilio.com
2. Get your Account SID and Auth Token from the dashboard
3. Purchase a phone number for making calls and sending SMS

## Next Steps

- [ ] Set up database for storing journal entries
- [ ] Create webhook endpoints for Twilio callbacks
- [ ] Implement speech-to-text for recording journal entries
- [ ] Build daily prompt system
- [ ] Add AI summarization for journal entries
