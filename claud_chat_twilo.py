from fastapi import FastAPI, Form, Request
from fastapi.responses import Response
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from openai import OpenAI
import json
import os
from datetime import datetime
from config import (
    TWILIO_ACCOUNT_SID, 
    TWILIO_AUTH_TOKEN, 
    TWILIO_PHONE_NUMBER,
    OPENAI_API_KEY
)

app = FastAPI()

# Initialize Twilio client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Initialize OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Store conversation history (in production, use a database)
conversation_history = {}

def get_chatbot_response(user_message: str, phone_number: str) -> str:
    """Get response from OpenAI API with conversation context"""
    
    # Get or initialize conversation history for this phone number
    if phone_number not in conversation_history:
        conversation_history[phone_number] = [
            {"role": "system", 
            "content": "You are a knowledgeable medical information assistant providing general health education via SMS. Keep all responses concise and clear due to SMS format limitations.\n\nYour role:\n- Provide accurate, evidence-based medical information for educational purposes only\n- Help users understand basic medical concepts and wellness practices\n- Your responses are NOT a substitute for professional medical advice, diagnosis, or treatment\n\nIMMEDIATELY refer to medical professionals when users describe:\n- Emergency symptoms (chest pain, difficulty breathing, severe injuries)\n- Serious acute conditions requiring urgent care\n- Complex medical issues needing professional diagnosis\n- Medication concerns or drug interactions\n- Mental health crises\n- Any situation where delayed treatment could cause harm\n\nFor serious conditions, respond: 'Please contact a healthcare professional or seek emergency medical attention immediately.'\n\nWhat you can discuss:\n- General medical concepts and common condition information\n- Basic wellness and prevention tips\n- When symptoms warrant medical attention\n- Simple first aid for minor issues\n\nAlways remind users to consult healthcare professionals for personalized medical guidance. Keep responses under 160 characters when possible for SMS compatibility."}
            
        ]
    
    # Add user message to history
    conversation_history[phone_number].append({"role": "user", "content": user_message})
    
    try:
        # Get response from OpenAI
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",  # or "gpt-4" if you have access
            messages=conversation_history[phone_number],
            max_tokens=150,  # Keep responses short for SMS
            temperature=0.7
        )
        
        assistant_message = response.choices[0].message.content.strip()
        
        # Add assistant response to history
        conversation_history[phone_number].append({"role": "assistant", "content": assistant_message})
        
        # Keep only last 10 messages to prevent context from getting too long
        if len(conversation_history[phone_number]) > 10:
            conversation_history[phone_number] = conversation_history[phone_number][-10:]
        
        return assistant_message
        
    except Exception as e:
        print(f"Error getting OpenAI response: {e}")
        return "Sorry, I'm having trouble processing your request right now. Please try again later."

@app.post("/chat")
async def chat_endpoint(query: str):
    """Direct chat endpoint for testing (your original idea)"""
    try:
        system_prompt = {
            "role": "system",
            "content": "You are a knowledgeable medical information assistant providing general health education via SMS. Keep all responses concise and clear due to SMS format limitations.\n\nYour role:\n- Provide accurate, evidence-based medical information for educational purposes only\n- Help users understand basic medical concepts and wellness practices\n- Your responses are NOT a substitute for professional medical advice, diagnosis, or treatment\n\nIMMEDIATELY refer to medical professionals when users describe:\n- Emergency symptoms (chest pain, difficulty breathing, severe injuries)\n- Serious acute conditions requiring urgent care\n- Complex medical issues needing professional diagnosis\n- Medication concerns or drug interactions\n- Mental health crises\n- Any situation where delayed treatment could cause harm\n\nFor serious conditions, respond: 'Please contact a healthcare professional or seek emergency medical attention immediately.'\n\nWhat you can discuss:\n- General medical concepts and common condition information\n- Basic wellness and prevention tips\n- When symptoms warrant medical attention\n- Simple first aid for minor issues\n\nAlways remind users to consult healthcare professionals for personalized medical guidance. Keep responses under 160 characters when possible for SMS compatibility."
        }

        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[system_prompt,{"role": "user", "content": query}],
            max_tokens=500,
            temperature=0.7
        )
        return {"response": response.choices[0].message.content.strip()}
    except Exception as e:
        return {"error": str(e)}

@app.post("/webhook/sms")
async def handle_sms(request: Request, Body: str = Form(...), From: str = Form(...)):
    """Webhook endpoint for incoming Twilio SMS messages"""
    
    print(f"Received SMS from {From}: {Body}")
    
    # Get chatbot response
    bot_response = get_chatbot_response(Body, From)
    
    # Create TwiML response
    twiml_response = MessagingResponse()
    twiml_response.message(bot_response)
    
    # Log the interaction
    log_interaction(From, Body, bot_response)
    
    return Response(content=str(twiml_response), media_type="application/xml")

def log_interaction(phone_number: str, user_message: str, bot_response: str):
    """Log conversation for debugging/analytics"""
    log_entry = {
        "timestamp": str(datetime.utcnow()),
        "phone_number": phone_number,
        "user_message": user_message,
        "bot_response": bot_response
    }
    
    log_file = "chatbot_logs.json"
    
    # Load existing logs
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            try:
                logs = json.load(f)
                if not isinstance(logs, list):
                    logs = [logs]
            except json.JSONDecodeError:
                logs = []
    else:
        logs = []
    
    # Add new log entry
    logs.append(log_entry)
    
    # Save logs
    with open(log_file, "w") as f:
        json.dump(logs, f, indent=2)

@app.post("/send-sms")
async def send_sms(phone_number: str, message: str):
    """Endpoint to send SMS manually (useful for notifications)"""
    try:
        message = twilio_client.messages.create(
            from_=TWILIO_PHONE_NUMBER,
            body=message,
            to=phone_number
        )
        return {"success": True, "message_sid": message.sid}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/")
async def root():
    return {"message": "Twilio-OpenAI Chatbot is running!"}

@app.get("/conversation/{phone_number}")
async def get_conversation(phone_number: str):
    """Get conversation history for a specific phone number"""
    if phone_number in conversation_history:
        return {"conversation": conversation_history[phone_number]}
    else:
        return {"conversation": []}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)