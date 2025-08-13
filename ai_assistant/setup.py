#!/usr/bin/env python3
"""
Setup script for AI Assistant
Handles initial configuration and dependency installation
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def print_step(step, description):
    """Print formatted step"""
    print(f"\n{'='*50}")
    print(f"Step {step}: {description}")
    print('='*50)

def check_python_version():
    """Check Python version"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version}")
    return True

def install_dependencies():
    """Install required dependencies"""
    try:
        print("Installing dependencies from requirements.txt...")
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], check=True, capture_output=True, text=True)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        print(f"Error output: {e.stderr}")
        return False

def setup_directories():
    """Create necessary directories"""
    directories = ["logs", "data"]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Created directory: {directory}")
    
    return True

def setup_environment_file():
    """Help user set up environment variables"""
    env_file = Path("config.env")
    example_file = Path("config.env.example")
    
    if env_file.exists():
        print("✅ config.env already exists")
        return True
    
    if not example_file.exists():
        print("❌ config.env.example not found")
        return False
    
    print("Setting up environment variables...")
    print(f"Please copy {example_file} to {env_file} and fill in your API keys:")
    
    # Show user what they need to configure
    try:
        with open(example_file, 'r') as f:
            content = f.read()
        
        print("\nRequired configuration:")
        for line in content.split('\n'):
            if line.startswith('OPEN_AI_API_KEY'):
                print("• OpenAI API Key (get from https://openai.com/api/)")
            elif line.startswith('GOOGLE_CLIENT_ID'):
                print("• Google Client ID (get from Google Cloud Console)")
            elif line.startswith('GOOGLE_CLIENT_SECRET'):
                print("• Google Client Secret (get from Google Cloud Console)")
        
        # Create the file for them
        with open(env_file, 'w') as f:
            f.write(content)
        
        print(f"\n✅ Created {env_file} - please edit it with your actual API keys")
        
    except Exception as e:
        print(f"❌ Error setting up environment file: {e}")
        return False
    
    return True

def check_oauth_setup():
    """Check if OAuth credentials are set up"""
    creds_file = Path("credentials.json")
    
    if creds_file.exists():
        print("✅ credentials.json found")
        return True
    else:
        print("⚠️ credentials.json not found")
        print("You'll need to:")
        print("1. Go to Google Cloud Console")
        print("2. Enable Gmail API")
        print("3. Create OAuth 2.0 credentials")
        print("4. Download the credentials.json file to this directory")
        return False

def main():
    """Main setup function"""
    print("🔧 AI Assistant Setup")
    print("This script will help you set up the AI Assistant")
    
    success = True
    
    # Step 1: Check Python version
    print_step(1, "Checking Python Version")
    if not check_python_version():
        success = False
    
    # Step 2: Create directories
    print_step(2, "Setting up Directories")
    if not setup_directories():
        success = False
    
    # Step 3: Install dependencies
    print_step(3, "Installing Dependencies")
    if not install_dependencies():
        success = False
    
    # Step 4: Setup environment file
    print_step(4, "Setting up Environment Variables")
    if not setup_environment_file():
        success = False
    
    # Step 5: Check OAuth setup
    print_step(5, "Checking OAuth Setup")
    oauth_ready = check_oauth_setup()
    
    # Final summary
    print_step("Final", "Setup Summary")
    
    if success:
        print("✅ Basic setup completed successfully!")
        
        if not oauth_ready:
            print("\n⚠️ Additional steps needed:")
            print("1. Set up Google OAuth credentials (credentials.json)")
            print("2. Edit config.env with your actual API keys")
            print("3. Add your cases.xlsx file to the data/ directory")
        
        print("\n🚀 Next steps:")
        print("1. Run: python main_new.py")
        print("2. For the first run, you'll need to authenticate with Google")
        
    else:
        print("❌ Setup encountered errors. Please fix the issues above and run again.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)