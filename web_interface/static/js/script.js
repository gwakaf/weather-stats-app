// DOM Elements
const locationSelect = document.getElementById('location');
const dateInput = document.getElementById('date');
const timeInput = document.getElementById('time');
const unitSelect = document.getElementById('unit');
const searchBtn = document.getElementById('searchBtn');
const graphBtn = document.getElementById('graphBtn');
const weatherSection = document.getElementById('weatherSection');
const graphSection = document.getElementById('graphSection');
const errorSection = document.getElementById('errorSection');
const loadingSection = document.getElementById('loadingSection');

// Weather display elements
const locationName = document.getElementById('locationName');
const dateTime = document.getElementById('dateTime');
const temperature = document.getElementById('temperature');
const weatherIcon = document.getElementById('weatherIcon');
const feelsLike = document.getElementById('feelsLike');
const humidity = document.getElementById('humidity');
const windSpeed = document.getElementById('windSpeed');
const visibility = document.getElementById('visibility');
const weatherDescription = document.getElementById('weatherDescription');
const errorMessage = document.getElementById('errorMessage');

// Graph display elements
const tempGraph = document.getElementById('temperatureGraph');
const windGraph = document.getElementById('windGraph');
const precipGraph = document.getElementById('precipitationGraph');
const cloudCoverageGraph = document.getElementById('cloudCoverageGraph');
const tempRange = document.getElementById('tempRange');
const windRange = document.getElementById('windRange');
const precipRange = document.getElementById('precipRange');
const cloudCoverageRange = document.getElementById('cloudCoverageRange');
const loadingMessage = document.getElementById('loadingMessage');

// Debug: Check if all DOM elements are found
console.log('DOM Elements check:', {
    locationName: !!locationName,
    dateTime: !!dateTime,
    temperature: !!temperature,
    weatherIcon: !!weatherIcon,
    feelsLike: !!feelsLike,
    humidity: !!humidity,
    windSpeed: !!windSpeed,
    visibility: !!visibility,
    weatherDescription: !!weatherDescription
});

// Initialize the app
document.addEventListener('DOMContentLoaded', function() {
    // Set default date to today
    const today = new Date().toISOString().split('T')[0];
    dateInput.value = today;
    
    // Set date picker constraints: max = today, min = 1 year ago
    dateInput.max = today;
    const oneYearAgo = new Date();
    oneYearAgo.setFullYear(oneYearAgo.getFullYear() - 1);
    dateInput.min = oneYearAgo.toISOString().split('T')[0];
    
    console.log(`Date picker range: ${dateInput.min} to ${dateInput.max}`);
    
    // Load predefined locations
    loadPredefinedLocations();
    
    // Add event listeners
    searchBtn.addEventListener('click', handleSearch);
    graphBtn.addEventListener('click', handleGraphRequest);
    
    // Allow Enter key to trigger search
    [locationSelect, dateInput, timeInput, unitSelect].forEach(input => {
        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                handleSearch();
            }
        });
    });
    
    // Add change event listener for unit selection
    unitSelect.addEventListener('change', function() {
        // If weather data is already displayed, update it with new unit
        if (weatherSection.style.display !== 'none') {
            handleSearch();
        }
    });
});

// Load predefined locations from backend
async function loadPredefinedLocations() {
    try {
        const response = await fetch('/api/locations', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            // Clear existing options except the first one
            locationSelect.innerHTML = '<option value="">Select a location...</option>';
            
            // Add predefined locations
            data.locations.forEach(location => {
                const option = document.createElement('option');
                option.value = location;
                option.textContent = location;
                locationSelect.appendChild(option);
            });
            
            console.log(`✅ Loaded ${data.locations.length} predefined locations`);
        } else {
            console.error('Failed to load predefined locations:', data.error);
            showError('Failed to load predefined locations');
        }
        
    } catch (error) {
        console.error('Error loading predefined locations:', error);
        showError('Failed to load predefined locations. Please refresh the page.');
    }
}

// Handle search button click
async function handleSearch() {
    const location = locationSelect.value.trim();
    const date = dateInput.value;
    const time = timeInput.value;
    const unit = unitSelect.value;
    
    // Validate inputs
    if (!location || !date || !time) {
        showError('Please fill in all fields');
        return;
    }
    
    // Show loading state
    showLoading('Fetching weather data...');
    
    try {
        // Call Flask backend API for predefined locations (using GET with query parameters)
        const queryParams = new URLSearchParams({
            location: location,
            date: date,
            time: time,
            unit: unit
        });
        const response = await fetch(`/api/weather-predefined?${queryParams}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const data = await response.json();
        
        console.log('API Response:', data);
        
        if (response.ok && data.success) {
            console.log('Weather data received:', data.weather);
            displayWeather(data.weather, data.location, data.date, data.time, data.unit);
        } else {
            showError(data.error || 'Failed to fetch weather data');
        }
        
    } catch (error) {
        console.error('Error fetching weather data:', error);
        showError('Failed to fetch weather data. Please check your internet connection and try again.');
    }
}

// Handle temperature graph button click
async function handleGraphRequest() {
    const location = locationSelect.value.trim();
    const date = dateInput.value;
    const time = timeInput.value;
    const unit = unitSelect.value;
    
    // Validate inputs
    if (!location || !date || !time) {
        showError('Please fill in all fields');
        return;
    }
    
    // Show loading state
    showLoading('Generating historical graphs...');
    
    try {
        // Call Flask backend API for temperature graph with predefined locations (using GET with query parameters)
        const queryParams = new URLSearchParams({
            location: location,
            date: date,
            time: time,
            unit: unit
        });
        const response = await fetch(`/api/temperature-graph-predefined?${queryParams}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        console.log('Response status:', response.status);
        
        const data = await response.json();
        console.log('Response data:', data);
        
        if (response.ok && data.success) {
            // Check if this is the placeholder response (not implemented yet)
            if (data.data && data.data.message) {
                console.log('Graph feature not yet implemented:', data.data.message);
                showError('📊 Historical weather graphs feature is coming soon! For now, use the "Get Weather" button to view weather data for specific dates.');
            } else if (data.graph_data) {
                console.log('Graph data received:', data.graph_data);
                displayGraphs(data.graph_data, data.location, data.date, data.time, data.unit);
            } else {
                showError('No graph data available');
            }
        } else {
            console.error('API error:', data.error);
            showError(data.error || 'Failed to generate graphs.');
        }
        
    } catch (error) {
        console.error('Error generating graphs:', error);
        showError('Failed to generate graphs. Please try again.');
    }
}

// Display weather data in the UI
function displayWeather(weatherData, location, date, time, unit) {
    console.log('Displaying weather data:', weatherData);
    
    // Format date and time
    const dateObj = new Date(date + 'T' + time);
    const dateTimeStr = dateObj.toLocaleString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
    
    // Extract temperature from Open-Meteo API format
    const tempCelsius = weatherData.temperature_celsius || 0;
    const tempValue = unit === 'fahrenheit' ? (tempCelsius * 9/5) + 32 : tempCelsius;
    const unitSymbol = unit === 'fahrenheit' ? '°F' : '°C';
    
    // Extract wind speed (already in km/h from Open-Meteo)
    const windKmh = weatherData.wind_speed_kmh || 0;
    const windValue = unit === 'fahrenheit' ? windKmh * 0.621371 : windKmh;
    const windUnit = unit === 'fahrenheit' ? ' mph' : ' km/h';
    
    // Extract other data
    const cloudCover = weatherData.cloud_coverage_percent || 0;
    const precipitation = weatherData.precipitation_mm || 0;
    const humidityValue = weatherData.humidity || 0;
    
    // Update UI elements
    if (locationName) locationName.textContent = location;
    if (dateTime) dateTime.textContent = dateTimeStr;
    if (temperature) temperature.textContent = Math.round(tempValue) + unitSymbol;
    
    // feelsLike not available from Open-Meteo, use actual temp
    if (feelsLike) feelsLike.textContent = Math.round(tempValue) + unitSymbol;
    
    if (humidity) humidity.textContent = humidityValue + '%';
    if (windSpeed) windSpeed.textContent = windValue.toFixed(1) + windUnit;
    
    // Visibility not available from Open-Meteo, show cloud cover instead
    if (visibility) visibility.textContent = cloudCover + '% clouds';
    
    // Set weather description based on conditions
    let description = '';
    if (cloudCover < 20) description = 'Clear sky';
    else if (cloudCover < 50) description = 'Partly cloudy';
    else if (cloudCover < 80) description = 'Mostly cloudy';
    else description = 'Overcast';
    
    if (precipitation > 0) description += `, ${precipitation.toFixed(1)}mm rain`;
    
    if (weatherDescription) weatherDescription.textContent = description;
    
    // Set weather icon based on conditions
    if (weatherIcon) {
        if (cloudCover < 20) setWeatherIcon('Clear', 'clear sky');
        else if (cloudCover < 50) setWeatherIcon('Clouds', 'few clouds');
        else if (precipitation > 0) setWeatherIcon('Rain', 'rain');
        else setWeatherIcon('Clouds', 'overcast clouds');
    }
    
    // Show weather section
    hideAllSections();
    if (weatherSection) weatherSection.style.display = 'block';
}

// Display both temperature and wind graphs in the UI
function displayGraphs(graphData, location, date, time, unit) {
    try {
        console.log('Displaying graphs for:', location, date, time);
        console.log('Graph data keys:', Object.keys(graphData));
        
        // Display temperature graph
        if (graphData.temperature_graph) {
            console.log('Setting temperature graph, length:', graphData.temperature_graph.length);
            tempGraph.src = `data:image/png;base64,${graphData.temperature_graph}`;
            tempGraph.alt = `Temperature history for ${location}`;
            
            // Add error handling for image loading
            tempGraph.onerror = function() {
                console.error('Failed to load temperature graph image');
                showError('Failed to load temperature graph image');
            };
            
            tempGraph.onload = function() {
                console.log('Temperature graph image loaded successfully');
            };
        } else {
            console.error('No temperature graph data received');
            showError('No temperature graph data received from server');
            return;
        }
        
        // Display wind graph
        if (graphData.wind_graph) {
            console.log('Setting wind graph, length:', graphData.wind_graph.length);
            windGraph.src = `data:image/png;base64,${graphData.wind_graph}`;
            windGraph.alt = `Wind speed history for ${location}`;
            
            // Add error handling for image loading
            windGraph.onerror = function() {
                console.error('Failed to load wind graph image');
                showError('Failed to load wind graph image');
            };
            
            windGraph.onload = function() {
                console.log('Wind graph image loaded successfully');
            };
        } else {
            console.error('No wind graph data received');
            showError('No wind graph data received from server');
            return;
        }
        
        // Display precipitation graph
        if (graphData.precipitation_graph) {
            console.log('Setting precipitation graph, length:', graphData.precipitation_graph.length);
            precipGraph.src = `data:image/png;base64,${graphData.precipitation_graph}`;
            precipGraph.alt = `Precipitation history for ${location}`;
            
            // Add error handling for image loading
            precipGraph.onerror = function() {
                console.error('Failed to load precipitation graph image');
                showError('Failed to load precipitation graph image');
            };
            
            precipGraph.onload = function() {
                console.log('Precipitation graph image loaded successfully');
            };
        } else {
            console.error('No precipitation graph data received');
            showError('No precipitation graph data received from server');
            return;
        }
        
        // Display cloud coverage graph
        if (graphData.cloud_coverage_graph) {
            console.log('Setting cloud coverage graph, length:', graphData.cloud_coverage_graph.length);
            cloudCoverageGraph.src = `data:image/png;base64,${graphData.cloud_coverage_graph}`;
            cloudCoverageGraph.alt = `Cloud coverage history for ${location}`;
            
            // Add error handling for image loading
            cloudCoverageGraph.onerror = function() {
                console.error('Failed to load cloud coverage graph image');
                showError('Failed to load cloud coverage graph image');
            };
            
            cloudCoverageGraph.onload = function() {
                console.log('Cloud coverage graph image loaded successfully');
            };
        } else {
            console.error('No cloud coverage graph data received');
            showError('No cloud coverage graph data received from server');
            return;
        }
        
        // Update statistics from the stats object
        if (graphData.stats) {
            console.log('📊 Statistics received:', graphData.stats);
            
            // Temperature stats
            if (graphData.stats.temperature && tempRange) {
                tempRange.textContent = `${graphData.stats.temperature.range} (Avg: ${graphData.stats.temperature.avg})`;
            }
            
            // Wind stats
            if (graphData.stats.wind && windRange) {
                windRange.textContent = `${graphData.stats.wind.range} (Avg: ${graphData.stats.wind.avg})`;
            }
            
            // Precipitation stats
            if (graphData.stats.precipitation && precipRange) {
                precipRange.textContent = `${graphData.stats.precipitation.range} (Avg: ${graphData.stats.precipitation.avg}, Total: ${graphData.stats.precipitation.total})`;
            }
            
            // Cloud coverage stats
            if (graphData.stats.cloud_coverage && cloudCoverageRange) {
                cloudCoverageRange.textContent = `${graphData.stats.cloud_coverage.range} (Avg: ${graphData.stats.cloud_coverage.avg})`;
            }
            
            console.log('✅ Statistics updated successfully');
        } else {
            console.warn('⚠️ No statistics data received');
        }
        
        // Show graph section
        hideAllSections();
        graphSection.style.display = 'block';
        graphSection.scrollIntoView({ behavior: 'smooth' });
        
        console.log('✅ All four graphs displayed successfully');
        console.log('📊 Temperature data:', graphData.temperatures);
        console.log('💨 Wind data:', graphData.wind_speeds);
        console.log('🌧️ Precipitation data:', graphData.precipitations);
        console.log('☁️ Cloud coverage data:', graphData.cloud_coverages);
        
    } catch (error) {
        console.error('Error displaying graphs:', error);
        showError('Error displaying graphs: ' + error.message);
    }
}

// Set weather icon based on weather condition
function setWeatherIcon(weatherMain, description) {
    const iconMap = {
        'Clear': 'fa-sun',
        'Clouds': 'fa-cloud',
        'Rain': 'fa-cloud-rain',
        'Drizzle': 'fa-cloud-rain',
        'Thunderstorm': 'fa-bolt',
        'Snow': 'fa-snowflake',
        'Mist': 'fa-smog',
        'Smoke': 'fa-smog',
        'Haze': 'fa-smog',
        'Dust': 'fa-smog',
        'Fog': 'fa-smog',
        'Sand': 'fa-smog',
        'Ash': 'fa-smog',
        'Squall': 'fa-wind',
        'Tornado': 'fa-wind'
    };
    
    const iconClass = iconMap[weatherMain] || 'fa-cloud';
    if (weatherIcon) weatherIcon.className = `fas ${iconClass}`;
}

// Show loading state
function showLoading(message = 'Loading...') {
    hideAllSections();
    if (loadingMessage) loadingMessage.textContent = message;
    if (loadingSection) loadingSection.style.display = 'block';
}

// Show error message
function showError(message) {
    hideAllSections();
    if (errorMessage) errorMessage.textContent = message;
    if (errorSection) errorSection.style.display = 'block';
}

// Hide all sections
function hideAllSections() {
    if (weatherSection) weatherSection.style.display = 'none';
    if (graphSection) graphSection.style.display = 'none';
    if (errorSection) errorSection.style.display = 'none';
    if (loadingSection) loadingSection.style.display = 'none';
}

// Utility function to format temperature
function formatTemperature(temp) {
    return Math.round(temp);
}

// Utility function to format wind speed
function formatWindSpeed(speed) {
    return speed.toFixed(1);
}

// Utility function to format visibility
function formatVisibility(visibility) {
    return (visibility / 1000).toFixed(1);
}

// Utility function to convert temperature
function convertTemperature(temp, unit) {
    if (unit === 'fahrenheit') {
        return (temp * 9/5) + 32;
    } else if (unit === 'celsius') {
        return temp;
    } else {
        throw new Error('Unsupported temperature unit');
    }
}

// Utility function to convert wind speed
function convertWindSpeed(speed, unit) {
    if (unit === 'fahrenheit') {
        // Convert km/h to mph (1 km/h = 0.621371 mph)
        return speed * 0.621371;
    } else if (unit === 'celsius') {
        return speed;
    } else {
        throw new Error('Unsupported temperature unit');
    }
}