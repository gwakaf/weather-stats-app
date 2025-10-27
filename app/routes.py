#!/usr/bin/env python3
"""
Flask Routes for Weather Finder API
Controller layer that handles HTTP requests, validates input, and returns JSON responses.
"""

from flask import render_template, request, jsonify
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from app.weather_api import weather_api
from app.aws_fetching import aws_fetcher
from app.utils.response_formatter import (
    format_weather_response, 
    format_error_response, 
    format_locations_response,
    format_historic_data_response
)
from app.utils.query_utils import (
    validate_coordinates, 
    validate_date_format, 
    validate_time_format,
    extract_request_data
)

logger = logging.getLogger(__name__)

# Add console handler for better visibility
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
logger.setLevel(logging.INFO)

def register_routes(app):
    """Register all Flask routes"""
    
    @app.route('/')
    def index():
        """Serve the main page"""
        return render_template('index.html')

    @app.route('/api/current_weather', methods=['POST'])
    def get_current_weather():
        """
        Get current weather data for a location
        
        Expected JSON payload:
        {
            "lat": float,
            "lon": float,
            "location_name": string (optional)
        }
        """
        try:
            # Parse incoming HTTP request
            data = request.get_json()
            if not data:
                return jsonify(format_error_response("No JSON data provided", 400))
            
            # Validate input
            lat, lon, _, _, location_name = extract_request_data(data)
            if lat is None or lon is None:
                return jsonify(format_error_response("Invalid coordinates provided", 400))
            
            # Call helper function from weather_api.py
            weather = weather_api.get_current_weather(lat, lon, location_name)
            
            # Return JSON response to frontend
            if weather:
                return jsonify(format_weather_response(weather))
            else:
                return jsonify(format_error_response("Failed to fetch current weather", 500))
                
        except Exception as e:
            logger.error(f"Error getting current weather: {e}")
            return jsonify(format_error_response(str(e), 500))

    @app.route('/api/historic_weather', methods=['POST'])
    def get_historic_weather():
        """
        Get historical weather data for a specific date and time
        
        Expected JSON payload:
        {
            "lat": float,
            "lon": float,
            "date": "YYYY-MM-DD",
            "time": "HH:MM" (optional, default: "12:00"),
            "location_name": string (optional),
            "unit": "celsius|fahrenheit" (optional, default: "celsius"),
            "location_type": "custom|predefined" (optional, default: "custom")
        }
        """
        try:
            # Parse incoming HTTP request
            data = request.get_json()
            if not data:
                return jsonify(format_error_response("No JSON data provided", 400))
            
            # Validate input
            lat, lon, date, time, location_name = extract_request_data(data)
            if lat is None or lon is None:
                return jsonify(format_error_response("Invalid coordinates provided", 400))
            
            if not date:
                return jsonify(format_error_response("Date is required", 400))
            
            if not validate_date_format(date):
                return jsonify(format_error_response("Invalid date format. Use YYYY-MM-DD", 400))
            
            if time and not validate_time_format(time):
                return jsonify(format_error_response("Invalid time format. Use HH:MM", 400))
            
            # Get additional parameters
            unit = data.get('unit', 'celsius')
            location_type = data.get('location_type', 'custom')
            
            # Call helper function from weather_api.py
            weather_data = weather_api.get_historical_weather(lat, lon, date, time)
            
            # Return JSON response to frontend
            if weather_data:
                response_data = format_weather_response(weather_data, unit)
                response_data['data']['data_source'] = 'Open-Meteo API' if location_type == 'custom' else 'Open-Meteo API (fallback)'
                return jsonify(response_data)
            else:
                return jsonify(format_error_response("Failed to fetch historical weather data", 500))
                
        except Exception as e:
            logger.error(f"Error getting historical weather: {e}")
            return jsonify(format_error_response(str(e), 500))

    @app.route('/api/predefined_locations', methods=['GET'])
    def get_predefined_locations():
        """Get list of available predefined locations"""
        try:
            # Call helper function from aws_fetching.py
            locations = aws_fetcher.get_available_locations()
            
            # Return JSON response to frontend
            return jsonify(format_locations_response(locations))
            
        except Exception as e:
            logger.error(f"Error getting predefined locations: {e}")
            return jsonify(format_error_response(str(e), 500))

    @app.route('/api/locations', methods=['GET'])
    def get_locations():
        """Get location coordinates for predefined locations"""
        try:
            # Call helper function from aws_fetching.py
            locations = aws_fetcher.get_available_locations()
            logger.info(f"Available locations: {locations}")
            
            location_data = {}
            
            for location in locations:
                coords = aws_fetcher.get_location_coordinates(location)
                if coords:
                    location_data[location] = coords
            
            logger.info(f"Returning {len(locations)} locations to frontend")
            
            # Return JSON response to frontend
            # Frontend expects data.locations to be an array of location names
            return jsonify({
                'success': True,
                'locations': locations,  # Array of location names
                'location_data': location_data,  # Object with coordinates
                'count': len(locations)
            })
            
        except Exception as e:
            logger.error(f"Error getting locations: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return jsonify(format_error_response(str(e), 500))

    @app.route('/api/weather-predefined', methods=['GET'])
    def get_weather_predefined():
        """
        Get weather data for a predefined location
        
        Query parameters:
        - location: string (required)
        - date: YYYY-MM-DD (optional, for historical data)
        - time: HH:MM (optional, default: "12:00")
        - unit: celsius|fahrenheit (optional, default: "celsius")
        """
        try:
            # Parse query parameters (RESTful GET request)
            location = request.args.get('location')
            date = request.args.get('date')
            time = request.args.get('time', '12:00')
            unit = request.args.get('unit', 'celsius')
            
            if not location:
                return jsonify(format_error_response("Location parameter is required", 400))
            
            # Validate location exists
            coords = aws_fetcher.get_location_coordinates(location)
            if not coords:
                return jsonify(format_error_response(f"Location '{location}' not found", 404))
            
            # Validate date if provided
            if date and not validate_date_format(date):
                return jsonify(format_error_response("Invalid date format. Use YYYY-MM-DD", 400))
            
            # Validate time if provided
            if time and not validate_time_format(time):
                return jsonify(format_error_response("Invalid time format. Use HH:MM", 400))
            
            # Call helper function from weather_api.py
            if date:
                # Historical weather
                logger.info(f"Fetching historical weather for {location} on {date} at {time}")
                weather_data = weather_api.get_historical_weather(
                    coords['lat'], coords['lon'], date, time
                )
                logger.info(f"Weather data received: {weather_data}")
                
                if weather_data:
                    weather_data['location'] = location
                    # Return format expected by JavaScript
                    return jsonify({
                        'success': True,
                        'weather': weather_data,
                        'location': location,
                        'date': date,
                        'time': time,
                        'unit': unit,
                        'data_source': 'Open-Meteo API'
                    })
                else:
                    return jsonify(format_error_response("Failed to fetch historical weather data", 500))
            else:
                # Current weather
                logger.info(f"Fetching current weather for {location}")
                weather_data = weather_api.get_current_weather(
                    coords['lat'], coords['lon'], location
                )
                logger.info(f"Current weather data received: {weather_data}")
                
                if weather_data:
                    # Return format expected by JavaScript
                    return jsonify({
                        'success': True,
                        'weather': weather_data,
                        'location': location,
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'time': datetime.now().strftime('%H:%M'),
                        'unit': unit,
                        'data_source': 'Open-Meteo API'
                    })
                else:
                    return jsonify(format_error_response("Failed to fetch current weather", 500))
                    
        except Exception as e:
            logger.error(f"Error getting weather for predefined location: {e}")
            return jsonify(format_error_response(str(e), 500))

    @app.route('/api/temperature-graph-predefined', methods=['GET'])
    def get_temperature_graph_predefined():
        """
        Get temperature history graph for a predefined location
        
        Query parameters:
        - location: string (required)
        - date: YYYY-MM-DD (required)
        - time: HH:MM (optional, default: "12:00")
        - unit: celsius|fahrenheit (optional, default: "celsius")
        """
        try:
            # Parse query parameters (RESTful GET request)
            location = request.args.get('location')
            date = request.args.get('date')
            time = request.args.get('time', '12:00')
            unit = request.args.get('unit', 'celsius')
            
            # Validate required parameters
            if not location:
                return jsonify(format_error_response("Location parameter is required", 400))
            
            if not date:
                return jsonify(format_error_response("Date parameter is required", 400))
            
            # Validate input
            coords = aws_fetcher.get_location_coordinates(location)
            if not coords:
                return jsonify(format_error_response(f"Location '{location}' not found", 404))
            
            if not validate_date_format(date):
                return jsonify(format_error_response("Invalid date format. Use YYYY-MM-DD", 400))
            
            if not validate_time_format(time):
                return jsonify(format_error_response("Invalid time format. Use HH:MM", 400))
            
            # Fetch 10 years of historical data for the same date/time
            logger.info(f"Generating historical graphs for {location} on {date} at {time}")
            
            from app.utils.graph_generator import generate_historical_graphs
            from datetime import datetime as dt
            
            # Get coordinates
            coords = aws_fetcher.get_location_coordinates(location)
            if not coords:
                return jsonify(format_error_response(f"Location '{location}' not found", 404))
            
            # Parse the target date and time
            target_date = dt.strptime(date, '%Y-%m-%d')
            target_hour = int(time.split(':')[0])
            current_year = dt.now().year
            
            # Fetch data for the same month/day over the past 10 years
            historical_data = []
            aws_count = 0
            meteo_count = 0
            
            # Try fetching from AWS S3/Athena first (if available)
            logger.info(f"Attempting to fetch data from AWS S3/Athena for 10 years")
            for year_offset in range(10):
                year = current_year - year_offset
                historical_date = target_date.replace(year=year)
                historical_date_str = historical_date.strftime('%Y-%m-%d')
                
                # Skip future dates
                if historical_date > dt.now():
                    continue
                
                # Try AWS Athena first
                aws_data = aws_fetcher.query_historic_data(location, historical_date_str, target_hour)
                if aws_data and len(aws_data) > 0:
                    logger.info(f"✅ Fetched {historical_date_str} from AWS S3")
                    historical_data.append(aws_data[0])
                    aws_count += 1
                else:
                    # Fallback to Open-Meteo API
                    logger.info(f"⚠️ AWS data not available for {historical_date_str}, falling back to Open-Meteo API")
                    weather_data = weather_api.get_historical_weather(
                        coords['lat'], coords['lon'], historical_date_str, time
                    )
                    if weather_data:
                        logger.info(f"✅ Fetched {historical_date_str} from Open-Meteo API")
                        historical_data.append(weather_data)
                        meteo_count += 1
                    else:
                        logger.warning(f"❌ No data available for {historical_date_str}")
            
            logger.info(f"📊 Fetched {len(historical_data)} years of historical data")
            logger.info(f"📊 Data sources: AWS S3: {aws_count} years, Open-Meteo: {meteo_count} years")
            
            if len(historical_data) == 0:
                return jsonify(format_error_response("No historical data available for graph generation. Please ensure data has been backfilled for this location.", 404))
            
            # Generate graphs
            logger.info(f"🎨 Generating graphs for {len(historical_data)} data points")
            graphs = generate_historical_graphs(historical_data, location, unit)
            
            if not graphs or len(graphs) == 0:
                return jsonify(format_error_response("Failed to generate graphs", 500))
            
            logger.info(f"✅ Successfully generated {len(graphs)} graphs")
            
            # Determine data source description
            if aws_count > 0 and meteo_count > 0:
                data_source = f'Mixed (AWS S3: {aws_count} years, Open-Meteo: {meteo_count} years)'
            elif aws_count > 0:
                data_source = f'AWS S3 ({aws_count} years)'
            elif meteo_count > 0:
                data_source = f'Open-Meteo API ({meteo_count} years)'
            else:
                data_source = 'No data available'
            
            # Return graphs to frontend
            return jsonify({
                'success': True,
                'graph_data': graphs,
                'location': location,
                'date': date,
                'time': time,
                'unit': unit,
                'years_count': len(historical_data),
                'data_source': data_source
            })
            
        except Exception as e:
            logger.error(f"Error getting temperature graph: {e}")
            return jsonify(format_error_response(str(e), 500))

    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        return jsonify({
            'success': True,
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0'
        })
