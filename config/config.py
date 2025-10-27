#!/usr/bin/env python3
"""
Configuration module for Weather Finder
Provides functions to read YAML configuration files
"""

import os
import yaml
from typing import Dict, Any

def get_infra_config() -> Dict[str, Any]:
    """Load infrastructure configuration from aws_infra_config.yaml"""
    config_path = os.path.join(os.path.dirname(__file__), 'aws_infra_config.yaml')
    try:
        with open(config_path, 'r') as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        raise FileNotFoundError(f"Infrastructure config file not found: {config_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing infrastructure config: {e}")

def get_locations_config() -> Dict[str, Any]:
    """Load locations configuration from locations.yaml"""
    config_path = os.path.join(os.path.dirname(__file__), 'locations.yaml')
    try:
        with open(config_path, 'r') as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        raise FileNotFoundError(f"Locations config file not found: {config_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing locations config: {e}")

def get_config(config_name: str) -> Dict[str, Any]:
    """Generic function to load any YAML config file"""
    config_path = os.path.join(os.path.dirname(__file__), f'{config_name}.yaml')
    try:
        with open(config_path, 'r') as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found: {config_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing config {config_name}: {e}") 