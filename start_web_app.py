#!/usr/bin/env python3
"""
Start Weather Finder Web App with proper environment loading
"""

import os
import sys
from pathlib import Path

# Load environment variables from .env file
def load_env_file():
    """Load environment variables from .env file"""
    env_path = Path('.env')
    if env_path.exists():
        print("📄 Loading environment variables from .env file...")
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
        print("✅ Environment variables loaded")
    else:
        print("⚠️ No .env file found")

def main():
    """Start the web application"""
    print("🚀 Starting Weather Finder Web Application")
    
    # Load environment variables
    load_env_file()
    
    # Check for required environment variables
    api_key = os.getenv('OPENWEATHER_API_KEY')
    if api_key:
        print(f"✅ OpenWeather API key found: {api_key[:8]}...")
    else:
        print("⚠️ No OpenWeather API key found in environment")
        print("   Make sure OPENWEATHER_API_KEY is set in your .env file")
    
    # Import and run the modular web app
    try:
        from app import create_app
        app = create_app()
        print("✅ Web app imported successfully")
        print("🌐 Starting Flask development server...")
        print("   URL: http://localhost:5001")
        print("   Press Ctrl+C to stop")
        
        # Enable detailed logging
        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        
        app.run(debug=True, host='0.0.0.0', port=5001)
        
    except ImportError as e:
        print(f"❌ Failed to import web app: {e}")
        print("   Make sure all dependencies are installed: pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ Failed to start web app: {e}")

if __name__ == "__main__":
    main() 