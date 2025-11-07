"""
ElevenLabs client for text-to-speech and voice operations.
"""
import os
from elevenlabs import ElevenLabs
from dotenv import load_dotenv

load_dotenv()


class ElevenLabsClient:
    """Client for interacting with ElevenLabs API."""
    
    def __init__(self, api_key: str = None):
        """
        Initialize ElevenLabs client.
        
        Args:
            api_key: ElevenLabs API key. If not provided, uses ELEVENLABS_API_KEY from environment.
        """
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        if not self.api_key:
            raise ValueError("ElevenLabs API key is required. Set ELEVENLABS_API_KEY environment variable.")
        
        self.client = ElevenLabs(api_key=self.api_key)
    
    def generate_speech(
        self,
        text: str,
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",  # Default: Rachel
        model_id: str = "eleven_monolingual_v1",
        voice_settings: dict = None
    ) -> bytes:
        """
        Generate speech audio from text.
        
        Args:
            text: Text to convert to speech
            voice_id: ElevenLabs voice ID
            model_id: Model to use for generation
            voice_settings: Optional voice settings dict (stability, similarity_boost, style, use_speaker_boost)
            
        Returns:
            Audio data as bytes
        """
        if voice_settings is None:
            voice_settings = {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.0,
                "use_speaker_boost": True
            }
        
        response = self.client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id=model_id,
            voice_settings=voice_settings
        )
        
        # Convert the generator to bytes
        audio_bytes = b"".join(response)
        
        return audio_bytes
    
    def list_voices(self):
        """
        List all available voices.
        
        Returns:
            Response object containing available voices
        """
        return self.client.voices.get_all()
    
    def get_or_create_phone_number(self, twilio_phone_number: str, twilio_account_sid: str, twilio_auth_token: str, label: str = "JournalAI"):
        """
        Get or create a phone number connection in ElevenLabs.
        
        Args:
            twilio_phone_number: Twilio phone number (E.164 format)
            twilio_account_sid: Twilio Account SID
            twilio_auth_token: Twilio Auth Token
            label: Label for the phone number in ElevenLabs
            
        Returns:
            Phone number ID from ElevenLabs
        """
        from elevenlabs.conversational_ai.phone_numbers import PhoneNumbersCreateRequestBody_Twilio
        
        # First, try to list existing phone numbers to see if we already have this one
        try:
            existing_numbers = self.client.conversational_ai.phone_numbers.list()
            # Check if phone number already exists (list() returns a list directly)
            for phone_num in existing_numbers:
                # Try different possible attribute names
                phone_num_value = getattr(phone_num, 'phone_number', None)
                if phone_num_value == twilio_phone_number:
                    phone_id = getattr(phone_num, 'phone_number_id', None) or getattr(phone_num, 'id', None)
                    if phone_id:
                        return phone_id
        except Exception as e:
            print(f"Note: Could not list existing phone numbers: {e}")
        
        # Create new phone number connection
        try:
            result = self.client.conversational_ai.phone_numbers.create(
                request=PhoneNumbersCreateRequestBody_Twilio(
                    phone_number=twilio_phone_number,
                    label=label,
                    sid=twilio_account_sid,
                    token=twilio_auth_token,
                )
            )
            return result.phone_number_id
        except Exception as e:
            # If creation fails, it might already exist - try to get it
            print(f"Phone number creation returned: {e}")
            raise
    
    def associate_agent_with_phone_number(self, phone_number_id: str, agent_id: str):
        """
        Associate an agent with a phone number.
        
        Args:
            phone_number_id: ElevenLabs phone number ID
            agent_id: ElevenLabs agent ID
            
        Returns:
            Updated phone number response
        """
        return self.client.conversational_ai.phone_numbers.update(
            phone_number_id=phone_number_id,
            agent_id=agent_id
        )
    
    def get_phone_number_webhook_url(self, phone_number_id: str):
        """
        Get the webhook URL for a registered phone number.
        
        Args:
            phone_number_id: ElevenLabs phone number ID
            
        Returns:
            Webhook URL string
        """
        phone_number = self.client.conversational_ai.phone_numbers.get(phone_number_id)
        
        # Try to find the webhook URL in the response
        # The structure may vary, so we check multiple possible attributes
        if hasattr(phone_number, 'webhook_url'):
            return phone_number.webhook_url
        elif hasattr(phone_number, 'twilio') and hasattr(phone_number.twilio, 'webhook_url'):
            return phone_number.twilio.webhook_url
        elif hasattr(phone_number, 'agent_phone_number') and hasattr(phone_number.agent_phone_number, 'webhook_url'):
            return phone_number.agent_phone_number.webhook_url
        
        # If we can't find it, construct it using the correct ElevenLabs API pattern
        # For Twilio, the webhook URL should point to ElevenLabs' TwiML endpoint
        return None
    
    def make_outbound_call(self, agent_id: str, phone_number_id: str, to_number: str, conversation_initiation_client_data: dict = None):
        """
        Make an outbound call using ElevenLabs' Twilio integration.
        This is the recommended way to make outbound calls - ElevenLabs handles the webhook setup.
        
        Args:
            agent_id: ElevenLabs agent ID
            phone_number_id: ElevenLabs phone number ID
            to_number: Phone number to call (E.164 format)
            conversation_initiation_client_data: Optional client data for the conversation
            
        Returns:
            TwilioOutboundCallResponse
        """
        return self.client.conversational_ai.twilio.outbound_call(
            agent_id=agent_id,
            agent_phone_number_id=phone_number_id,
            to_number=to_number,
            conversation_initiation_client_data=conversation_initiation_client_data
        )
    
    def get_phone_number_reputation_info(self, phone_number_id: str):
        """
        Get information about phone number reputation and carrier blocking.
        Note: This may not be directly available via API, but we can check call patterns.
        """
        # This is informational - actual reputation data might not be available via API
        return {
            "note": "Carrier spam filtering is common for new/unknown numbers",
            "suggestions": [
                "Use a toll-free number (better reputation)",
                "Use a local number in the recipient's area code",
                "Gradually build call history (reduces spam flags)",
                "Consider caller name registration (CNAM)",
            ]
        }
    
    def list_conversations(self, limit: int = 100):
        """
        List all conversations.
        
        Args:
            limit: Maximum number of conversations to return
            
        Returns:
            List of conversation objects
        """
        try:
            conversations = self.client.conversational_ai.conversations.list()
            # Handle different response structures
            if hasattr(conversations, 'conversations'):
                conv_list = conversations.conversations
            elif isinstance(conversations, list):
                conv_list = conversations
            else:
                conv_list = [conversations]
            
            return conv_list[:limit] if limit else conv_list
        except Exception as e:
            print(f"Error listing conversations: {e}")
            raise
    
    def get_conversation(self, conversation_id: str):
        """
        Get details of a specific conversation.
        
        Args:
            conversation_id: ElevenLabs conversation ID
            
        Returns:
            Conversation object with details and transcription
        """
        try:
            return self.client.conversational_ai.conversations.get(conversation_id)
        except Exception as e:
            print(f"Error getting conversation: {e}")
            raise
    
    def get_latest_conversation_by_phone_number(self, phone_number: str):
        """
        Get the latest conversation for a given phone number.
        
        Args:
            phone_number: Phone number in E.164 format (e.g., +1234567890)
            
        Returns:
            Latest conversation object, or None if not found
        """
        import re
        
        # Normalize phone number for comparison
        normalized = phone_number.strip()
        if not normalized.startswith('+'):
            # Remove all non-digit characters except +
            cleaned = re.sub(r'[^\d+]', '', normalized)
            if len(cleaned) == 10:
                normalized = '+1' + cleaned
            elif len(cleaned) == 11 and cleaned[0] == '1':
                normalized = '+' + cleaned
            else:
                normalized = '+1' + cleaned
        
        conversations = self.list_conversations(limit=500)
        
        # Generate all possible variations of the search phone number
        def normalize_phone(phone):
            """Normalize phone to digits only for comparison."""
            return re.sub(r'[^\d]', '', str(phone))
        
        search_digits = normalize_phone(normalized)
        # If search number starts with +1, also try without the 1
        if normalized.startswith('+1') and len(search_digits) == 11:
            search_variations = [search_digits, search_digits[1:]]  # +18603048753 and 8603048753
        else:
            search_variations = [search_digits]
        
        # Filter conversations by phone number and sort by timestamp
        matching_conversations = []
        seen_conv_ids = set()
        
        # We need to get full conversation details to access phone number
        for conv in conversations:
            # Get conversation ID to avoid duplicates
            conv_id = getattr(conv, 'conversation_id', None) or getattr(conv, 'id', None) or getattr(conv, 'conversation_uuid', None)
            if not conv_id:
                continue
            if conv_id in seen_conv_ids:
                continue
            
            # Get full conversation details - phone number might only be in detailed view
            try:
                full_conv = self.get_conversation(conv_id)
            except:
                # If we can't get full details, try with the basic conv object
                full_conv = conv
            
            # Check various possible attributes for phone number
            caller_phone = None
            phone_attrs_to_check = [
                ('caller_phone_number', lambda x: x),
                ('phone_number', lambda x: x),
                ('caller', lambda x: getattr(x, 'phone_number', None) if hasattr(x, 'phone_number') else None),
                ('from_phone_number', lambda x: x),
                ('from', lambda x: getattr(x, 'phone_number', None) if hasattr(x, 'phone_number') else (x if isinstance(x, str) else None)),
                ('to_phone_number', lambda x: x),
                ('twilio_from', lambda x: x),
                ('twilio_to', lambda x: x),
            ]
            
            # Check basic conversation object first
            for attr_name, extractor in phone_attrs_to_check:
                if hasattr(conv, attr_name):
                    val = getattr(conv, attr_name)
                    if val:
                        extracted = extractor(val)
                        if extracted:
                            caller_phone = extracted
                            break
            
            # Check full conversation object
            if not caller_phone:
                for attr_name, extractor in phone_attrs_to_check:
                    if hasattr(full_conv, attr_name):
                        val = getattr(full_conv, attr_name)
                        if val:
                            extracted = extractor(val)
                            if extracted:
                                caller_phone = extracted
                                break
            
            # Helper function to recursively search for phone numbers
            def find_phone_recursive(obj, depth=0, max_depth=3):
                """Recursively search for phone number in nested structures."""
                if depth > max_depth:
                    return None
                
                if obj is None:
                    return None
                
                # Check if it's a string that looks like a phone number
                if isinstance(obj, str) and len(obj.replace('+', '').replace('-', '').replace(' ', '').replace('(', '').replace(')', '')) >= 10:
                    cleaned = re.sub(r'[^\d+]', '', obj)
                    if len(cleaned) >= 10:  # Basic validation
                        return obj
                
                # Check dict
                if isinstance(obj, dict):
                    for key in ['phone_number', 'caller_phone_number', 'phone', 'caller', 'from', 'to', 'from_phone', 'to_phone', 'caller_number', 'caller_id']:
                        if key.lower() in [k.lower() for k in obj.keys()]:
                            # Find the actual key (case-insensitive)
                            actual_key = [k for k in obj.keys() if k.lower() == key.lower()][0]
                            val = obj[actual_key]
                            if val:
                                result = find_phone_recursive(val, depth+1, max_depth)
                                if result:
                                    return result
                    # Recursively check all values
                    for val in obj.values():
                        result = find_phone_recursive(val, depth+1, max_depth)
                        if result:
                            return result
                
                # Check object attributes (Pydantic models, etc.)
                if hasattr(obj, '__dict__'):
                    for key in ['phone_number', 'caller_phone_number', 'phone', 'caller', 'from', 'to']:
                        if hasattr(obj, key):
                            val = getattr(obj, key)
                            if val:
                                result = find_phone_recursive(val, depth+1, max_depth)
                                if result:
                                    return result
            
            # Check metadata in both objects
            for conv_obj in [conv, full_conv]:
                if caller_phone:
                    break
                
                # Try direct attributes first
                if hasattr(conv_obj, 'metadata'):
                    # Explicitly check metadata.phone_call.{external_number, agent_number}
                    try:
                        md = conv_obj.metadata
                        if isinstance(md, dict):
                            phone_call = md.get('phone_call')
                            if isinstance(phone_call, dict):
                                caller_phone = (
                                    phone_call.get('external_number') or
                                    phone_call.get('caller_number') or
                                    phone_call.get('from') or
                                    phone_call.get('to') or
                                    phone_call.get('agent_number')
                                )
                        # Fallback to recursive search
                        if not caller_phone:
                            caller_phone = find_phone_recursive(md)
                    except Exception:
                        caller_phone = find_phone_recursive(conv_obj.metadata)
                
                # Check conversation_initiation_client_data
                if not caller_phone and hasattr(conv_obj, 'conversation_initiation_client_data'):
                    caller_phone = find_phone_recursive(conv_obj.conversation_initiation_client_data)
                
                # Check analysis object
                if not caller_phone and hasattr(conv_obj, 'analysis'):
                    caller_phone = find_phone_recursive(conv_obj.analysis)
                
                # Try to dump to dict and search recursively
                if not caller_phone:
                    try:
                        if hasattr(conv_obj, 'model_dump'):
                            dump_obj = conv_obj.model_dump()
                            caller_phone = find_phone_recursive(dump_obj)
                        elif hasattr(conv_obj, 'dict'):
                            dump_obj = conv_obj.dict()
                            caller_phone = find_phone_recursive(dump_obj)
                    except:
                        pass
            
            # Check for phone_number_id - we might need to look up the phone number
            if not caller_phone and hasattr(full_conv, 'phone_number_id'):
                phone_number_id = full_conv.phone_number_id
                if phone_number_id:
                    try:
                        # Try to get phone number details from phone_number_id
                        phone_num_obj = self.client.conversational_ai.phone_numbers.get(phone_number_id)
                        if hasattr(phone_num_obj, 'phone_number'):
                            caller_phone = phone_num_obj.phone_number
                    except:
                        pass
            
            if caller_phone:
                # Normalize caller phone for comparison
                caller_digits = normalize_phone(str(caller_phone))
                
                # Check if any variation matches
                matched = False
                for search_var in search_variations:
                    if caller_digits == search_var:
                        matching_conversations.append(conv)
                        seen_conv_ids.add(conv_id)
                        matched = True
                        break
                    # Also check if the last 10 digits match (in case country code is different)
                    if not matched and len(caller_digits) >= 10 and len(search_var) >= 10:
                        if caller_digits[-10:] == search_var[-10:]:
                            matching_conversations.append(conv)
                            seen_conv_ids.add(conv_id)
                            matched = True
                            break
        
        if not matching_conversations:
            return None
        
        # Sort by timestamp (most recent first)
        def get_timestamp(conv):
            if hasattr(conv, 'created_at'):
                return conv.created_at
            elif hasattr(conv, 'timestamp'):
                return conv.timestamp
            elif hasattr(conv, 'started_at'):
                return conv.started_at
            elif hasattr(conv, 'updated_at'):
                return conv.updated_at
            return 0
        
        matching_conversations.sort(key=get_timestamp, reverse=True)
        
        return matching_conversations[0] if matching_conversations else None
    
    def get_transcription(self, conversation_id: str):
        """
        Get the transcription for a conversation.
        
        Args:
            conversation_id: ElevenLabs conversation ID
        
        Returns:
            Transcription text as string, or None if not available
        """
        try:
            conversation = self.get_conversation(conversation_id)
            
            # Try different possible attributes for transcription
            if hasattr(conversation, 'transcript'):
                transcript = conversation.transcript
                
                # Handle list of transcript objects (new format)
                if isinstance(transcript, list):
                    transcript_parts = []
                    for item in transcript:
                        # Skip items that are clearly metadata-only (have role but no message)
                        # Check if this item has a role attribute but message is None
                        has_role = False
                        has_message = False
                        message_text = None
                        
                        # Check if item has role attribute
                        if hasattr(item, 'role'):
                            has_role = True
                        
                        # Try to extract message text - ONLY from message attribute
                        if hasattr(item, 'message'):
                            msg_val = getattr(item, 'message')
                            if msg_val and isinstance(msg_val, str) and msg_val.strip():
                                message_text = msg_val.strip()
                                has_message = True
                        
                        # If item has role but no message, skip it entirely (it's metadata)
                        if has_role and not has_message:
                            continue
                        
                        # Only proceed if we have actual message text
                        if not message_text:
                            # Try other text attributes as fallback, but be strict
                            for attr in ['text', 'content']:
                                if hasattr(item, attr):
                                    val = getattr(item, attr)
                                    if val and isinstance(val, str) and val.strip():
                                        message_text = val.strip()
                                        break
                        
                        # If still no text, try model_dump but ONLY extract message/text/content
                        if not message_text and hasattr(item, 'model_dump'):
                            try:
                                item_dict = item.model_dump()
                                # Only extract from message, text, or content - nothing else
                                message_text = (item_dict.get('message') or 
                                               item_dict.get('text') or 
                                               item_dict.get('content'))
                                if message_text:
                                    message_text = str(message_text).strip()
                                    # If it's still an object representation, skip it
                                    if message_text.startswith("role=") or 'AgentMetadata(' in message_text:
                                        message_text = None
                            except:
                                pass
                        
                        # Try dict access as last resort
                        if not message_text and isinstance(item, dict):
                            message_text = (item.get('message') or 
                                           item.get('text') or 
                                           item.get('content'))
                            if message_text:
                                message_text = str(message_text).strip()
                                # If it's an object representation, skip it
                                if message_text.startswith("role=") or 'AgentMetadata(' in message_text:
                                    message_text = None
                        
                        # Only add if we have actual message text (not None, not empty, not object representation)
                        if message_text and len(message_text) > 0:
                            # Final check - filter out any object representations that slipped through
                            is_object_repr = False
                            
                            # Check for Pydantic model representations
                            if message_text.startswith("role="):
                                is_object_repr = True
                            elif 'role=' in message_text and ('agent_metadata=' in message_text or 'AgentMetadata(' in message_text):
                                is_object_repr = True
                            elif 'ConversationHistoryTranscriptToolCallCommonModel(' in message_text:
                                is_object_repr = True
                            elif 'ConversationHistoryTranscriptOtherToolsResultCommonModel(' in message_text:
                                is_object_repr = True
                            elif 'ConversationTurnMetrics(' in message_text:
                                is_object_repr = True
                            elif 'LlmUsageOutput(' in message_text or 'LlmInputOutputTokensUsage(' in message_text:
                                is_object_repr = True
                            elif 'MetricRecord(' in message_text:
                                is_object_repr = True
                            # Check for patterns like: role='agent' agent_metadata=...
                            elif (message_text.count("=") > 3 and message_text.count("(") > 0 and message_text.count(")") > 0):
                                # If it looks like a Python object representation, skip it
                                if any(keyword in message_text for keyword in ['agent_metadata', 'tool_calls', 'tool_results', 'conversation_turn_metrics', 'llm_usage', 'time_in_call_secs']):
                                    is_object_repr = True
                            
                            if not is_object_repr:
                                transcript_parts.append(message_text)
                    
                    if transcript_parts:
                        # Join and clean up the transcript
                        full_transcript = '\n'.join(transcript_parts)
                        # Remove any remaining object representations that might have slipped through
                        lines = full_transcript.split('\n')
                        cleaned_lines = []
                        for line in lines:
                            line = line.strip()
                            if not line:
                                continue
                            # Skip lines that look like object representations
                            if (line.startswith("role=") or 
                                'AgentMetadata(' in line or 
                                'ConversationHistoryTranscript' in line or
                                'ConversationTurnMetrics(' in line or
                                'LlmUsageOutput(' in line or
                                'MetricRecord(' in line or
                                ('agent_metadata=' in line and '=' in line and '(' in line) or
                                ('tool_calls=' in line and '[' in line) or
                                ('tool_results=' in line and '[' in line) or
                                ('conversation_turn_metrics=' in line) or
                                ('llm_usage=' in line) or
                                ('time_in_call_secs=' in line)):
                                continue
                            cleaned_lines.append(line)
                        return '\n'.join(cleaned_lines)
                
                # Handle string format
                elif isinstance(transcript, str):
                    return transcript
                
                # Handle object with text attribute
                elif hasattr(transcript, 'text'):
                    return transcript.text
                elif hasattr(transcript, 'full_transcript'):
                    return transcript.full_transcript
                elif hasattr(transcript, 'content'):
                    return transcript.content
            
            elif hasattr(conversation, 'transcription'):
                transcript = conversation.transcription
                if isinstance(transcript, list):
                    # Handle list format
                    transcript_parts = []
                    for item in transcript:
                        if hasattr(item, 'text'):
                            transcript_parts.append(item.text)
                        elif hasattr(item, 'content'):
                            transcript_parts.append(item.content)
                        elif isinstance(item, str):
                            transcript_parts.append(item)
                    if transcript_parts:
                        return '\n'.join(transcript_parts)
                return transcript
            elif hasattr(conversation, 'transcript_text'):
                return conversation.transcript_text
            elif hasattr(conversation, 'full_transcript'):
                return conversation.full_transcript
            elif hasattr(conversation, 'data') and hasattr(conversation.data, 'transcript'):
                return conversation.data.transcript
            
            return None
        except Exception as e:
            print(f"Error getting transcription: {e}")
            raise

