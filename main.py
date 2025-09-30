from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse
from twilio.rest import Client
import uvicorn
import os
from datetime import datetime
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from database import Database
from speech_services import SpeechServices
from ai_agent import SwiftLogisticsAgent
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="SwiftLogistics Voice AI", version="1.0.0")

# Initialize services
config = Config()
db = Database(config.database_url)
speech_services = SpeechServices(config.google_credentials_path)
ai_agent = SwiftLogisticsAgent(db)
twilio_client = Client(config.twilio_account_sid, config.twilio_auth_token)

# Store active calls
active_calls = {}


#Addd layers of security to the code

@app.post("/webhook/voice")
async def handle_voice_call(request: Request):
    """Handle incoming voice calls from Twilio"""
    form = await request.form()
    call_sid = form.get("CallSid")
    from_number = form.get("From")
    
    logger.info(f"Incoming call from {from_number}, SID: {call_sid}")
    
    response = VoiceResponse()
    
    # Start recording and gather speech
    response.say("Hello! Welcome to Rocket Shipment. I'm your Rocket Shipment AI agent. How can I help you today?")
    response.record(
        action=f"/webhook/process-speech/{call_sid}",
        method="POST",
        max_length=30,
        finish_on_key="#",
        play_beep=True
    )
    
    # Initialize call session
    active_calls[call_sid] = {
        "from_number": from_number,
        "conversation_state": "greeting",
        "context": {}
    }
    
    return Response(content=str(response), media_type="application/xml")

@app.post("/webhook/process-speech/{call_sid}")
async def process_speech(call_sid: str, request: Request):
    """Process recorded speech and generate AI response"""
    form = await request.form()
    recording_url = form.get("RecordingUrl")
    
    if call_sid not in active_calls:
        logger.error(f"Call SID {call_sid} not found in active calls")
        return Response(content="<Response></Response>", media_type="application/xml")
    
    try:
        # Convert speech to text
        user_text = await speech_services.speech_to_text(recording_url)
        logger.info(f"User said: {user_text}")
        
        # Process with AI agent
        call_context = active_calls[call_sid]
        ai_response = await ai_agent.process_message(
            user_text, 
            call_context["conversation_state"], 
            call_context["context"]
        )
        
        # Update call context
        active_calls[call_sid]["conversation_state"] = ai_response["next_state"]
        active_calls[call_sid]["context"].update(ai_response["context"])
        
        # Convert response to speech
        audio_url = await speech_services.text_to_speech(ai_response["message"])
        
        # Create TwiML response
        response = VoiceResponse()
        response.play(audio_url)
        
        # Continue conversation if needed
        if ai_response["continue_conversation"]:
            response.record(
                action=f"/webhook/process-speech/{call_sid}",
                method="POST",
                max_length=30,
                finish_on_key="#",
                play_beep=True
            )
        else:
            response.say("Thank you for calling SwiftLogistics. Have a great day!")
            response.hangup()
            # Clean up call session
            if call_sid in active_calls:
                del active_calls[call_sid]
        
        return Response(content=str(response), media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Error processing speech: {str(e)}")
        response = VoiceResponse()
        response.say("Sorry, I didn't get that. Can you please speak again?")
        response.record(
            action=f"/webhook/process-speech/{call_sid}",
            method="POST",
            max_length=30,
            finish_on_key="#",
            play_beep=True
        )
        return Response(content=str(response), media_type="application/xml")

@app.post("/webhook/transfer-human/{call_sid}")
async def transfer_to_human(call_sid: str):
    """Transfer call to human agent"""
    response = VoiceResponse()
    response.say("Please hold while I transfer you to a human agent.")
    response.dial(config.human_agent_number)
    
    # Clean up call session
    if call_sid in active_calls:
        del active_calls[call_sid]
    
    return Response(content=str(response), media_type="application/xml")

@app.get("/tmp/{filename}")
async def serve_audio_file(filename: str):
    """Serve temporary audio files"""
    import aiofiles
    from fastapi.responses import FileResponse
    import os
    
    file_path = f"/tmp/{filename}"
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="audio/mpeg")
    else:
        raise HTTPException(status_code=404, detail="Audio file not found")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.on_event("startup")
async def startup_event():
    """Initialize database and services on startup"""
    await db.initialize()
    logger.info("SwiftLogistics Voice AI started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    await db.close()
    logger.info("SwiftLogistics Voice AI shut down")

if __name__ == "__main__":
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=int(os.getenv("PORT", 8000)), 
        reload=True
    )