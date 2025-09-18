# SwiftLogistics Voice AI Agent

A sophisticated voice-based customer support system for logistics operations, built with FastAPI, Twilio, Google Cloud services, and PostgreSQL.

## Features

- **Voice-Based Interactions**: Natural phone conversations using Twilio telephony
- **Speech Processing**: Google Cloud Speech-to-Text and Text-to-Speech integration
- **Logistics Operations**: Track shipments, book new shipments, reschedule deliveries
- **Smart Conversation Flow**: Context-aware AI agent with multi-turn conversations
- **Database Integration**: PostgreSQL for shipment and call logging
- **Human Handoff**: Seamless transfer to human agents when needed

## Architecture

```
Phone Call → Twilio → FastAPI Backend → AI Agent
                          ↓              ↓
                    Speech Services → Database
                          ↓
                   Google Cloud APIs
```

## Installation

### Prerequisites

- Python 3.8+
- PostgreSQL database
- Twilio account with phone number
- Google Cloud account with Speech and TTS APIs enabled

### Setup

1. **Clone and install dependencies**:
   ```bash
   git clone <repository-url>
   cd voice-ai-agent
   pip install -r requirements.txt
   ```

2. **Database setup**:
   ```bash
   # Create PostgreSQL database
   createdb swiftlogistics
   
   # Database tables will be created automatically on first run
   ```

3. **Google Cloud setup**:
   - Create a Google Cloud project
   - Enable Speech-to-Text and Text-to-Speech APIs
   - Create a service account and download credentials JSON
   - Place credentials file in project root as `google-credentials.json`

4. **Configuration**:
   ```bash
   cp .env.example .env
   # Edit .env with your actual configuration values
   ```

5. **Required environment variables** - Edit your `.env` file with these values:

   ### Database Configuration
   ```
   DATABASE_URL=postgresql://username:password@localhost:5432/swiftlogistics
   ```
   Replace with your actual PostgreSQL connection string.

   ### Twilio Configuration
   Get these from your [Twilio Console](https://console.twilio.com):
   ```
   TWILIO_ACCOUNT_SID=your_twilio_account_sid
   TWILIO_AUTH_TOKEN=your_twilio_auth_token
   TWILIO_PHONE_NUMBER=your_twilio_phone_number
   HUMAN_AGENT_NUMBER=your_human_agent_number
   ```

   ### Google Cloud Configuration
   ```
   GOOGLE_APPLICATION_CREDENTIALS=./google-credentials.json
   ```

   ### Application Configuration
   ```
   APP_HOST=0.0.0.0
   PORT=8000
   DEBUG=False
   WEBHOOK_BASE_URL=https://your-domain.com
   ```

6. **Google Cloud Service Account Setup**:
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Navigate to IAM & Admin > Service Accounts
   - Create a new service account with "Speech API Admin" permissions
   - Download the JSON key file and save it as `google-credentials.json` in your project root

⚠️ **SECURITY IMPORTANT**:
- Never commit your `.env` file or `google-credentials.json` to version control
- These files contain sensitive credentials and are protected by `.gitignore`
- Always use secure credential management in production

## Usage

### Running the Application

```bash
python main.py
```

The server will start on `http://localhost:8000` by default.

### Twilio Webhook Configuration

Configure your Twilio phone number webhook URL to:
```
https://your-domain.com/webhook/voice
```

### API Endpoints

- `POST /webhook/voice` - Handle incoming calls
- `POST /webhook/process-speech/{call_sid}` - Process recorded speech
- `POST /webhook/transfer-human/{call_sid}` - Transfer to human agent
- `GET /health` - Health check

## Conversation Flow

### Supported Operations

1. **Track Shipment**:
   - Customer: "I want to track my shipment"
   - AI: "Please provide your tracking ID"
   - Customer: "SL12345678"
   - AI: [Provides shipment status, delivery date, and destination]

2. **Book New Shipment**:
   - Customer: "I need to ship a package"
   - AI: Collects customer name, pickup address, delivery address, and delivery date
   - AI: [Creates shipment and provides tracking ID]

3. **Reschedule Delivery**:
   - Customer: "I need to reschedule my delivery"
   - AI: [Verifies customer identity and updates delivery date]

4. **Human Transfer**:
   - Customer: "I want to speak to a human" or "*"
   - AI: [Transfers to human agent]

### Conversation States

- `greeting`: Initial greeting and intent detection
- `tracking`: Shipment tracking flow
- `booking`: New shipment booking flow  
- `rescheduling`: Delivery rescheduling flow
- `identity_verification`: Customer identity verification
- `transfer_human`: Transfer to human agent

## Database Schema

### Shipments Table
```sql
tracking_id VARCHAR(20) PRIMARY KEY
customer_name VARCHAR(255) NOT NULL
pickup_address TEXT NOT NULL
delivery_address TEXT NOT NULL
delivery_date DATE NOT NULL
status VARCHAR(50) DEFAULT 'pending'
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

### Call Logs Table
```sql
id SERIAL PRIMARY KEY
call_sid VARCHAR(255) UNIQUE NOT NULL
from_number VARCHAR(20)
action VARCHAR(50)
tracking_id VARCHAR(20)
details JSONB
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

## Development

### Project Structure

```
voice-ai-agent/
├── main.py              # FastAPI application and webhook handlers
├── ai_agent.py          # Core AI agent logic and conversation flow
├── database.py          # Database models and operations
├── logistics_tools.py   # Logistics-specific tool functions
├── speech_services.py   # Google Cloud Speech services integration
├── config.py           # Configuration management
├── requirements.txt    # Python dependencies
├── .env.example       # Environment configuration template
└── README.md          # This file
```

### Adding New Features

1. **New conversation flows**: Extend `ai_agent.py` with new intent detection and handlers
2. **New tools**: Add to `logistics_tools.py` and integrate with AI agent
3. **Database changes**: Update `database.py` with new models and migrations
4. **Speech enhancements**: Modify `speech_services.py` for voice improvements

### Testing

```bash
# Run tests (when implemented)
pytest

# Format code
black .

# Lint code
flake8 .
```

## Production Deployment

### Requirements

- Publicly accessible HTTPS URL for Twilio webhooks
- Production PostgreSQL database
- Google Cloud project with appropriate quotas
- SSL certificate for HTTPS

### Deployment Steps

1. Deploy to cloud platform (AWS, GCP, Azure, etc.)
2. Set up production database
3. Configure environment variables
4. Update Twilio webhook URLs
5. Set up monitoring and logging
6. Configure auto-scaling if needed

### Monitoring

- Monitor call volume and response times
- Track speech recognition accuracy
- Monitor database performance
- Set up alerts for system failures

## Security Considerations

- All credentials stored in environment variables
- Customer identity verification for shipment modifications
- Secure webhook endpoints with Twilio signature validation
- Database connection security
- HTTPS required for production

## Troubleshooting

### Common Issues

1. **Speech recognition fails**: Check Google Cloud credentials and API quotas
2. **Database connection errors**: Verify DATABASE_URL and PostgreSQL service
3. **Twilio webhook failures**: Ensure public HTTPS URL and correct webhook configuration
4. **Audio playback issues**: Check TTS service and audio file accessibility

### Logs

Application logs provide detailed information about:
- Conversation flows and state transitions
- Tool execution results
- Database operations
- Speech service interactions
- Error conditions

## License

[Add your license information here]

## Support

[Add support contact information here]