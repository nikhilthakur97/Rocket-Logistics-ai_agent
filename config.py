import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class Config:
    """Configuration management for SwiftLogistics Voice AI"""
    
    def __init__(self):
        self.load_config()
    
    def load_config(self):
        """Load configuration from environment variables"""
        
        # Database Configuration
        self.database_url = os.getenv(
            'DATABASE_URL', 
            'postgresql://user:password@localhost/swiftlogistics'
        )
        
        # Twilio Configuration
        self.twilio_account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.twilio_auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.twilio_phone_number = os.getenv('TWILIO_PHONE_NUMBER')
        self.human_agent_number = os.getenv('HUMAN_AGENT_NUMBER', '+1234567890')
        
        # Google Cloud Configuration
        self.google_credentials_path = os.getenv(
            'GOOGLE_APPLICATION_CREDENTIALS',
            './google-credentials.json'
        )
        
        # Application Configuration
        self.app_host = os.getenv('APP_HOST', '0.0.0.0')
        self.app_port = int(os.getenv('PORT', 8000))
        self.debug_mode = os.getenv('DEBUG', 'False').lower() == 'true'
        
        # Webhook URL (for Twilio callbacks)
        self.webhook_base_url = os.getenv(
            'WEBHOOK_BASE_URL', 
            f'http://localhost:{self.app_port}'
        )
        
        # Validate critical configuration
        self._validate_config()
    
    def _validate_config(self):
        """Validate that all required configuration is present"""
        required_configs = [
            ('TWILIO_ACCOUNT_SID', self.twilio_account_sid),
            ('TWILIO_AUTH_TOKEN', self.twilio_auth_token),
            ('TWILIO_PHONE_NUMBER', self.twilio_phone_number),
            ('DATABASE_URL', self.database_url),
            ('GOOGLE_APPLICATION_CREDENTIALS', self.google_credentials_path)
        ]
        
        missing_configs = []
        for config_name, config_value in required_configs:
            if not config_value:
                missing_configs.append(config_name)
        
        if missing_configs:
            logger.warning(f"Missing configuration: {', '.join(missing_configs)}")
            logger.warning("Application may not function correctly without these configurations")
        
        # Check if Google credentials file exists
        if not os.path.exists(self.google_credentials_path):
            logger.warning(f"Google credentials file not found at: {self.google_credentials_path}")
    
    def get_twilio_webhook_url(self, endpoint: str) -> str:
        """Get full webhook URL for Twilio configuration"""
        return f"{self.webhook_base_url}/webhook/{endpoint}"
    
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return not self.debug_mode
    
    def get_database_config(self) -> dict:
        """Get database configuration dictionary"""
        return {
            'url': self.database_url,
            'echo': self.debug_mode  # Enable SQL logging in debug mode
        }