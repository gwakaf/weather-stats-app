import os
import yaml
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# CONFIG_DIR should point to weather-app/config/
CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')

# Helper to load a YAML config file from config/
def load_yaml_config(filename):
    path = os.path.join(CONFIG_DIR, filename)
    with open(path, 'r') as f:
        return yaml.safe_load(f)

# Import from the centralized config module
from config.config import get_locations_config, get_infra_config

# Example: get env variable with fallback
def get_env_var(key, default=None):
    return os.getenv(key, default)

# Example: get OpenWeather API key
def get_openweather_api_key():
    return get_env_var('OPENWEATHER_API_KEY', None)

# Example: get Flask secret key
def get_flask_secret_key():
    return get_env_var('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production') 