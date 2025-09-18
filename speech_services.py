import os
import tempfile
import requests
from google.cloud import speech
from google.cloud import texttospeech
import logging
from typing import Optional
import asyncio
import aiofiles
import aiohttp

logger = logging.getLogger(__name__)

class SpeechServices:
    def __init__(self, credentials_path: str):
        """Initialize Google Cloud Speech and Text-to-Speech services"""
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
        
        self.speech_client = speech.SpeechClient()
        self.tts_client = texttospeech.TextToSpeechClient()
        
        # Simple response cache for common phrases
        self.tts_cache = {}
        
        # Configure TTS voice - using faster Standard voice instead of Neural2
        self.voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Standard-F",  # Faster Standard voice
            ssml_gender=texttospeech.SsmlVoiceGender.FEMALE,
        )
        
        # Configure audio output - optimized for speed
        self.audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.1,  # Faster speech for quicker responses
            pitch=0.0,
        )
    
    async def speech_to_text(self, recording_url: str) -> str:
        """
        Convert speech recording to text using Google Cloud Speech-to-Text
        Args:
            recording_url: URL of the Twilio recording
        Returns:
            Transcribed text
        """
        try:
            # Download the audio file from Twilio
            audio_content = await self._download_audio(recording_url)
            
            if not audio_content:
                raise Exception("Failed to download audio from Twilio")
            
            # Configure speech recognition - optimized for speed
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.MP3,
                sample_rate_hertz=8000,  # Twilio phone quality
                language_code="en-US",
                enable_automatic_punctuation=False,  # Faster without punctuation
                model="latest_short",  # Faster model for short phrases
                use_enhanced=False,  # Faster without enhancement
            )
            
            audio = speech.RecognitionAudio(content=audio_content)
            
            # Perform speech recognition
            response = self.speech_client.recognize(config=config, audio=audio)
            
            # Extract transcript
            if response.results:
                transcript = response.results[0].alternatives[0].transcript
                logger.info(f"Speech-to-text result: {transcript}")
                return transcript.strip()
            else:
                logger.warning("No speech detected in audio")
                return ""
                
        except Exception as e:
            logger.error(f"Speech-to-text error: {str(e)}")
            raise
    
    async def text_to_speech(self, text: str) -> str:
        """
        Convert text to speech using Google Cloud Text-to-Speech
        Args:
            text: Text to convert to speech
        Returns:
            URL of the generated audio file
        """
        try:
            # Check cache for common phrases first
            text_key = text.lower().strip()
            if text_key in self.tts_cache:
                logger.info(f"Using cached TTS audio for: {text}")
                return self.tts_cache[text_key]
            
            # Prepare the synthesis input
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # Perform the text-to-speech request
            response = self.tts_client.synthesize_speech(
                input=synthesis_input, 
                voice=self.voice, 
                audio_config=self.audio_config
            )
            
            # Save audio to temporary file and return URL
            audio_url = await self._save_audio_file(response.audio_content)
            logger.info(f"Generated TTS audio: {audio_url}")
            
            # Cache common phrases (keep cache small)
            if len(text) < 100 and len(self.tts_cache) < 50:
                self.tts_cache[text_key] = audio_url
            
            return audio_url
            
        except Exception as e:
            logger.error(f"Text-to-speech error: {str(e)}")
            raise
    
    async def _download_audio(self, url: str) -> Optional[bytes]:
        """Download audio file from URL"""
        try:
            # Add Twilio authentication if needed
            auth = None
            if 'twilio.com' in url:
                from config import Config
                config = Config()
                auth = aiohttp.BasicAuth(config.twilio_account_sid, config.twilio_auth_token)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, auth=auth) as response:
                    if response.status == 200:
                        return await response.read()
                    else:
                        logger.error(f"Failed to download audio: HTTP {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error downloading audio: {str(e)}")
            return None
    
    async def _save_audio_file(self, audio_content: bytes) -> str:
        """Save audio content to temporary file and return accessible URL"""
        try:
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(
                delete=False, 
                suffix='.mp3',
                dir='/tmp'  # Use /tmp for web accessibility
            )
            
            # Write audio content
            async with aiofiles.open(temp_file.name, 'wb') as f:
                await f.write(audio_content)
            
            # Return file path (in production, this should be a publicly accessible URL)
            # For now, we'll use the local file path
            # In production, you'd upload to cloud storage and return the public URL
            return temp_file.name
            
        except Exception as e:
            logger.error(f"Error saving audio file: {str(e)}")
            raise
    
    def cleanup_temp_files(self):
        """Clean up old temporary audio files (should be called periodically)"""
        try:
            import glob
            import time
            
            # Remove files older than 1 hour
            temp_pattern = "/tmp/*.mp3"
            current_time = time.time()
            
            for file_path in glob.glob(temp_pattern):
                if os.path.exists(file_path):
                    file_age = current_time - os.path.getctime(file_path)
                    if file_age > 3600:  # 1 hour
                        os.remove(file_path)
                        logger.info(f"Cleaned up old temp file: {file_path}")
                        
        except Exception as e:
            logger.error(f"Error cleaning up temp files: {str(e)}")