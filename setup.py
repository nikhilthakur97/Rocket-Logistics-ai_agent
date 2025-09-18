#!/usr/bin/env python3

import os
import subprocess
import sys
from pathlib import Path

def run_command(command, description):
    """Run a shell command and handle errors"""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e.stderr}")
        return None

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")

def setup_virtual_environment():
    """Create and activate virtual environment"""
    venv_path = Path("venv")
    
    if venv_path.exists():
        print("✅ Virtual environment already exists")
        return
    
    if run_command("python -m venv venv", "Creating virtual environment"):
        print("✅ Virtual environment created")
        print("🔔 To activate: source venv/bin/activate (Linux/Mac) or venv\\Scripts\\activate (Windows)")
    else:
        print("❌ Failed to create virtual environment")
        sys.exit(1)

def install_dependencies():
    """Install Python dependencies"""
    # Check if we're in a virtual environment
    if sys.prefix == sys.base_prefix:
        print("⚠️  Warning: Not in a virtual environment. Consider activating venv first.")
    
    if run_command("pip install -r requirements.txt", "Installing dependencies"):
        print("✅ Dependencies installed")
    else:
        print("❌ Failed to install dependencies")
        sys.exit(1)

def setup_environment_file():
    """Create .env file from template"""
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if env_file.exists():
        print("✅ .env file already exists")
        return
    
    if env_example.exists():
        # Copy example to .env
        with open(env_example, 'r') as src, open(env_file, 'w') as dst:
            dst.write(src.read())
        print("✅ Created .env file from template")
        print("🔔 Please edit .env file with your actual configuration values")
    else:
        print("⚠️  .env.example not found")

def check_postgresql():
    """Check if PostgreSQL is available"""
    result = run_command("which psql", "Checking PostgreSQL installation")
    if result:
        print("✅ PostgreSQL client found")
        print("🔔 Make sure PostgreSQL server is running and accessible")
    else:
        print("⚠️  PostgreSQL client not found. Please install PostgreSQL")
        print("   - macOS: brew install postgresql")
        print("   - Ubuntu: sudo apt-get install postgresql-client")
        print("   - Windows: Download from https://www.postgresql.org/download/")

def create_database():
    """Create the database if it doesn't exist"""
    print("\n🔔 Database setup:")
    print("   1. Make sure PostgreSQL is running")
    print("   2. Create database: createdb swiftlogistics")
    print("   3. Update DATABASE_URL in .env file")
    print("   4. Database tables will be created automatically on first run")

def check_google_credentials():
    """Check for Google Cloud credentials"""
    cred_file = Path("google-credentials.json")
    if cred_file.exists():
        print("✅ Google Cloud credentials file found")
    else:
        print("⚠️  Google Cloud credentials not found")
        print("   1. Create a Google Cloud project")
        print("   2. Enable Speech-to-Text and Text-to-Speech APIs")
        print("   3. Create service account and download JSON credentials")
        print("   4. Save as 'google-credentials.json' in project root")

def display_next_steps():
    """Display next steps for the user"""
    print("\n" + "="*60)
    print("🎉 SETUP COMPLETE!")
    print("="*60)
    print("\n📋 NEXT STEPS:")
    print("1. 📝 Edit .env file with your actual configuration:")
    print("   - Twilio credentials (Account SID, Auth Token, Phone Number)")
    print("   - Database URL")
    print("   - Google Cloud credentials path")
    print("   - Webhook base URL for production")
    
    print("\n2. 🗄️  Set up PostgreSQL database:")
    print("   createdb swiftlogistics")
    
    print("\n3. ☁️  Set up Google Cloud:")
    print("   - Enable Speech-to-Text and Text-to-Speech APIs")
    print("   - Place service account JSON in project root")
    
    print("\n4. 📞 Configure Twilio webhook:")
    print("   - Set webhook URL to: https://your-domain.com/webhook/voice")
    
    print("\n5. 🚀 Start the application:")
    print("   python main.py")
    
    print("\n6. 🧪 Test the system:")
    print("   - Call your Twilio phone number")
    print("   - Try different voice commands")
    
    print("\n📚 For more information, see README.md")
    print("🆘 For issues, check the troubleshooting section in README.md")

def main():
    """Main setup function"""
    print("🚀 SwiftLogistics Voice AI Agent Setup")
    print("="*50)
    
    # Check system requirements
    check_python_version()
    
    # Setup virtual environment
    setup_virtual_environment()
    
    # Install dependencies
    install_dependencies()
    
    # Setup configuration
    setup_environment_file()
    
    # Check external dependencies
    check_postgresql()
    check_google_credentials()
    
    # Display next steps
    display_next_steps()

if __name__ == "__main__":
    main()