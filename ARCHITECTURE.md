# Weather Finder - Current Architecture

**Last Updated**: October 21, 2025

---

## 📋 **Table of Contents**
1. [Overview](#overview)
2. [Component Structure](#component-structure)
3. [Data Flows](#data-flows)
4. [API Specifications](#api-specifications)
5. [Storage Architecture](#storage-architecture)
6. [Deployment](#deployment)

---

## 🎯 **Overview**

Weather Finder is a comprehensive weather data platform with:
- ✅ **Web UI**: Interactive interface for viewing current and historical weather
- ✅ **Backend API**: Flask-based REST API for weather data
- ✅ **Data Pipelines**: Airflow-orchestrated ETL processes
- ✅ **AWS Integration**: S3 storage and Athena querying
- ✅ **External APIs**: Open-Meteo for all weather data (no API key required!)

---

## 🏗️ **Component Structure**

### **1. Web UI (`web_interface/` + `app/`)**

#### **Frontend Files:**
```
web_interface/
├── templates/
│   └── index.html          # Main UI with location selector, date/time picker
├── static/
│   ├── css/styles.css      # Modern, responsive styling
│   └── js/script.js        # API calls, graph rendering, UI updates
```

#### **Backend Entry Point:**
```
start_web_app.py            # Flask app launcher with .env loading
app/__init__.py             # Flask app factory (create_app)
```

#### **Features:**
- ✅ Location dropdown (4 predefined CA locations)
- ✅ Date picker (limited to today - 1 year back)
- ✅ Time selector
- ✅ Temperature unit converter (Celsius/Fahrenheit)
- ✅ Wind unit converter (km/h/mph)
- ✅ "Get Weather" button - Single date/time weather
- ✅ "Historic Weather" button - 10-year trend graphs

---

### **2. Backend API (`app/`)**

#### **Core API Handler (`app/weather_api.py`)**

**WeatherAPI Class:**
- **Purpose**: Centralized handler for ALL weather API calls
- **No API key required** - Uses Open-Meteo exclusively

**Methods:**
```python
get_current_weather(lat, lon, location_name)
├── Uses: Open-Meteo Forecast API
├── Endpoint: https://api.open-meteo.com/v1/forecast
├── Returns: Current weather (temp, wind, precipitation, clouds, humidity)
└── Used by: Web UI "Get Weather" for today's date

get_historical_weather(lat, lon, date, time)
├── Uses: Open-Meteo Archive API
├── Endpoint: https://archive-api.open-meteo.com/v1/archive
├── Returns: Weather for specific date/time
└── Used by: Web UI "Get Weather" for past dates, graph generation

get_historical_weather_all_hours(lat, lon, date, location_name)
├── Uses: Open-Meteo Archive API
├── Endpoint: https://archive-api.open-meteo.com/v1/archive
├── Returns: 24 hours of weather data for one date
└── Used by: Daily ingestion pipeline, backfilling pipeline
```

**Key Points:**
- ✅ **FREE** - No API key required for any functionality
- ✅ **Consistent data format** across all methods
- ✅ **Built-in retry logic** with exponential backoff
- ✅ **Error handling** with detailed logging

---

#### **AWS Data Fetcher (`app/aws_fetching.py`)**

**AWSDataFetcher Class:**
- **Purpose**: Query historical weather data from AWS S3/Athena

**Methods:**
```python
get_available_locations()
├── Returns: List of predefined location names
└── Source: config/locations.yaml

get_location_coordinates(location_name)
├── Returns: {lat, lon} for a location
└── Source: config/locations.yaml

query_historic_data(location_name, target_date, target_hour)
├── Queries: AWS Athena
├── Database: weather_finder_db (from infra_config.yaml)
├── Table: historic_weather
├── Returns: Weather data from S3 (if available)
└── Used by: Web UI "Historic Weather" graphs (with fallback to Open-Meteo)
```

**Key Points:**
- ✅ Loads locations from centralized config
- ✅ AWS credentials from environment variables
- ⚠️ Graceful fallback if AWS not configured
- ✅ Athena query execution with status polling

---

#### **Flask Routes (`app/routes.py`)**

**API Endpoints:**

```python
GET /
├── Returns: Main web UI page (index.html)

GET /api/locations
├── Returns: {success: true, locations: [...], location_data: {...}}
├── Source: config/locations.yaml
└── Used by: Web UI to populate location dropdown

GET /api/weather-predefined?location=...&date=...&time=...&unit=...
├── Logic:
│   ├── If date provided: get_historical_weather() from Open-Meteo
│   └── Else: get_current_weather() from Open-Meteo
├── Returns: {success: true, weather: {...}, location, date, time, unit}
└── Used by: Web UI "Get Weather" button

GET /api/temperature-graph-predefined?location=...&date=...&time=...&unit=...
├── Logic:
│   ├── For past 10 years of same date/time:
│   │   ├── Try: AWS S3/Athena query_historic_data()
│   │   └── Fallback: Open-Meteo Archive API
│   ├── Generate matplotlib graphs (4 graphs)
│   └── Return base64-encoded PNG images
├── Returns: {success: true, graph_data: {...}, stats: {...}}
└── Used by: Web UI "Historic Weather" button

POST /api/current_weather
├── Body: {lat, lon, location_name}
├── Returns: Current weather from Open-Meteo
└── Legacy endpoint (not used by current UI)

POST /api/historic_weather
├── Body: {lat, lon, date, time}
├── Returns: Historical weather from Open-Meteo
└── Legacy endpoint (not used by current UI)

GET /api/health
├── Returns: {success: true, status: 'healthy'}
└── Health check endpoint
```

---

#### **Utilities (`app/utils/`)**

**`query_utils.py`:**
- Input validation (coordinates, dates, times)
- Request data extraction
- Query parameter building

**`response_formatter.py`:**
- Weather response formatting
- Error response formatting
- Unit conversions (Celsius/Fahrenheit, km/h/mph)

**`graph_generator.py`:** *(NEW)*
- Generate 4 matplotlib graphs for 10-year trends
- Base64 encoding for web display
- Statistical calculations (min/max/avg)
- Beautiful visualizations with seaborn styling

---

### **3. Data Pipelines (`pipelines/`)**

#### **Daily Ingestion (`pipelines/daily_ingest.py`)**

**Purpose**: Ingest weather data from 1 week ago for all locations

**Functions:**
```python
get_locations()
├── Loads locations from config/locations.yaml
└── Returns: List of {name, lat, lon} dictionaries

run_daily_ingestion(**context)
├── Date processed: 1 week ago (due to Open-Meteo data delay)
├── For each location:
│   ├── Call: weather_api.get_historical_weather_all_hours()
│   ├── Convert to DataFrame (24 hours of data)
│   ├── Add metadata (location, ingestion_timestamp)
│   └── Save: save_to_s3_parquet()
└── Returns: Success/failure status
```

**Key Points:**
- ✅ Processes **1 week ago** (not yesterday) due to API data availability
- ✅ Fetches **24 hours** of data per location per day
- ✅ Uses WeatherAPI class (no direct API key handling)
- ✅ Detailed logging for debugging

---

#### **Backfilling (`pipelines/backfilling_ingest.py`)**

**Purpose**: Backfill historical weather data for specific date ranges

**Functions:**
```python
load_backfilling_config()
├── Loads: config/backfilling_config.yaml
└── Returns: {start_date, end_date, location, api settings}

get_location_coordinates(location_name)
├── Loads: config/locations.yaml
└── Returns: {lat, lon, name}

backfill_historic_weather(start_date, end_date, location_name, save_to_s3)
├── For each day in range:
│   ├── Call: weather_api.get_historical_weather_all_hours()
│   ├── Convert to DataFrame (24 hours)
│   ├── Add metadata
│   ├── Save: save_to_s3_parquet()
│   └── Delay between requests (configurable)
└── Returns: (successful_days, total_days, failed_days)

backfill_multiple_locations(start_date, end_date, locations, save_to_s3)
├── Calls backfill_historic_weather() for each location
└── Returns: Summary dictionary for all locations
```

**Key Points:**
- ✅ Configurable API delays (default: 1 second)
- ✅ Configurable max retries (default: 3)
- ✅ Supports single or multiple locations
- ✅ Comprehensive progress logging
- ✅ Summary statistics

---

#### **S3 Writer (`pipelines/s3_writer.py`)**

**Purpose**: Save weather DataFrames to AWS S3 in Parquet format

**Functions:**
```python
get_s3_config()
├── Reads: config/infra_config.yaml
└── Returns: S3 bucket name

save_to_s3_parquet(df, location_name, date)
├── Path structure: weather-data/location={name}/year={YYYY}/month={MM}/day={DD}/weather_data_{date}.parquet
├── Example: s3://weather-data-yy/weather-data/location=San_Francisco_CA/year=2025/month=10/day=21/weather_data_2025-10-21.parquet
├── Uses: boto3.client('s3')
└── Returns: True/False
```

**Key Points:**
- ✅ Partitioned by location, year, month, day
- ✅ Descriptive filenames with date
- ✅ Parquet format for efficient querying
- ✅ Auto-extracts year/month/day from date

---

### **4. Airflow DAGs (`dags/`)**

#### **Daily Ingestion DAG (`dags/daily_ingestion_dag.py`)**

**Configuration:**
- **DAG ID**: `daily_weather_ingestion`
- **Schedule**: Daily at 6 AM (`0 6 * * *`)
- **Catchup**: False
- **Max Active Runs**: 1

**Tasks:**
```python
ingest_weather_data (PythonOperator)
├── Callable: pipelines.daily_ingest.run_daily_ingestion
├── Provides context: True
└── No task dependencies (single task)
```

**Data Processed:**
- Date: 1 week ago (not yesterday - due to Open-Meteo delay)
- Locations: All 4 locations from config/locations.yaml
- Records: ~96 records (24 hours × 4 locations)

**Key Points:**
- ✅ Pure orchestration (no business logic in DAG)
- ✅ Imports from pipelines.daily_ingest
- ✅ Fails if import fails (no fallback)
- ✅ Retries: 2, Delay: 5 minutes

---

#### **Backfilling DAG (`dags/backfilling_dag.py`)**

**Configuration:**
- **DAG ID**: `backfilling`
- **Schedule**: Manual trigger only
- **Catchup**: False
- **Max Active Runs**: 1

**Tasks:**
```python
1. get_backfilling_status (PythonOperator)
   ├── Callable: get_backfilling_status
   └── Logs current configuration

2. backfill_historic_data (PythonOperator)
   ├── Callable: airflow_backfill_task
   ├── Imports: pipelines.backfilling_ingest
   └── Depends on: get_backfilling_status
```

**Configuration Sources:**
1. Primary: `config/backfilling_config.yaml`
2. Override: DAG run config (JSON parameters)

**Trigger with Config:**
```bash
# Via Airflow UI: Trigger DAG w/ config
{
  "start_date": "2025-07-19",
  "end_date": "2025-10-19",
  "location": "Menlo Park, CA"
}

# Via CLI:
airflow dags trigger backfilling \
  --conf '{"start_date":"2025-07-19","end_date":"2025-10-19","location":"Menlo Park, CA"}'
```

**Key Points:**
- ✅ Pure orchestration (no business logic in DAG)
- ✅ Imports from pipelines.backfilling_ingest
- ✅ Configurable via YAML or JSON
- ✅ Single location per run (run 4 times for all locations)

---

### **5. Configuration (`config/`)**

#### **`config/locations.yaml`**
```yaml
locations:
  - name: "Menlo Park, CA"
    lat: 37.4529
    lon: -122.1817
  - name: "Walnut Creek, CA"
    lat: 37.9101
    lon: -122.0652
  - name: "San Francisco, CA"
    lat: 37.7749
    lon: -122.4194
  - name: "Carmel-By-The-Sea, CA"
    lat: 36.5552
    lon: -121.9283
```

#### **`config/infra_config.yaml`**
```yaml
s3_bucket: "weather-data-yy"
glue_database: "weather_finder_db"
glue_table: "historic_weather"
athena_workgroup: "weather-finder-workgroup"
athena_output_bucket: "weather-data-yy-athena-output"
region: "us-east-1"
```

#### **`config/backfilling_config.yaml`**
```yaml
start_date: "2025-01-01"
end_date: "2025-06-30"
location: "San Francisco, CA"
api:
  delay_between_requests: 1
  max_retries: 3
logging:
  level: "INFO"
  detailed_progress: true
```

#### **`config/config.py`**
```python
get_locations_config()      # Load locations.yaml
get_infra_config()          # Load infra_config.yaml
get_config(config_name)     # Generic YAML loader
```

---

### **6. Testing (`tests/`)**

#### **`tests/tests.py`** (pytest suite)

**Test Classes:**
```python
TestOpenWeatherAPI
├── test_get_current_weather_san_francisco
└── Tests Open-Meteo Forecast API for current weather

TestOpenMeteoAPI
├── test_get_historical_weather_san_francisco
└── Tests Open-Meteo Archive API for historical weather (1 week ago)

TestAWSConnectivity
├── test_aws_credentials_configured
│   └── Validates AWS credentials
└── test_save_to_s3_parquet_function
    └── Tests S3 upload with real data
```

**Environment:**
- Uses `.env` file for credentials
- Skips tests if credentials not found
- Marks slow tests (API/AWS calls)

**Run Tests:**
```bash
source venv/bin/activate
pytest tests/tests.py -v -s
```

---

## 🔄 **Data Flows**

### **Flow 1: Daily Ingestion (Airflow)**

```
┌─────────────────────────────────────────────────────────────┐
│ Daily @ 6 AM                                                │
│ Airflow DAG: daily_weather_ingestion                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Task: ingest_weather_data                                   │
│ Callable: pipelines.daily_ingest.run_daily_ingestion       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 1. Load locations from config/locations.yaml               │
│    - Menlo Park, CA                                         │
│    - Walnut Creek, CA                                       │
│    - San Francisco, CA                                      │
│    - Carmel-By-The-Sea, CA                                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. For each location:                                       │
│    date = today - 7 days (1 week ago)                       │
│    weather_api.get_historical_weather_all_hours(lat, lon, date) │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Open-Meteo Archive API Call                             │
│    GET https://archive-api.open-meteo.com/v1/archive       │
│    Returns: 24 hours of weather data                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Convert to DataFrame                                     │
│    - 24 rows (one per hour)                                 │
│    - Columns: temperature, wind, precipitation, clouds      │
│    - Add metadata: location, ingestion_timestamp            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Save to S3 (save_to_s3_parquet)                          │
│    Path: weather-data/location=.../year=.../month=.../day=.../weather_data_YYYY-MM-DD.parquet │
│    Format: Parquet (compressed)                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Result: 4 locations × 24 hours = 96 records in S3          │
└─────────────────────────────────────────────────────────────┘
```

---

### **Flow 2: Backfilling (Airflow - Manual Trigger)**

```
┌─────────────────────────────────────────────────────────────┐
│ Manual Trigger with Config                                  │
│ Airflow DAG: backfilling                                    │
│ Config: {"start_date": "2025-07-19",                        │
│          "end_date": "2025-10-19",                          │
│          "location": "Menlo Park, CA"}                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Task 1: get_backfilling_status                              │
│ Logs configuration and validates parameters                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Task 2: backfill_historic_data                              │
│ Callable: pipelines.backfilling_ingest.backfill_historic_weather │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ For each day in date range (e.g., 93 days):                │
│   1. weather_api.get_historical_weather_all_hours(date)    │
│   2. Convert to DataFrame (24 hours)                        │
│   3. save_to_s3_parquet(df, location, date)                │
│   4. Delay 1 second (configurable)                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Result: 93 days × 24 hours = 2,232 records in S3           │
│ Duration: ~2-3 minutes per location                         │
└─────────────────────────────────────────────────────────────┘
```

**To Backfill All 4 Locations:**
Run the DAG 4 times with different location parameters.

---

### **Flow 3: Web UI - "Get Weather" Button**

```
┌─────────────────────────────────────────────────────────────┐
│ User Action:                                                │
│ 1. Select location: "Menlo Park, CA"                        │
│ 2. Select date: 2025-10-21 (today or past year)            │
│ 3. Select time: 13:00                                       │
│ 4. Click "Get Weather"                                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ JavaScript:                                                 │
│ GET /api/weather-predefined?location=Menlo+Park,+CA&date=2025-10-21&time=13:00&unit=celsius │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Backend (routes.py):                                        │
│ 1. Validate location (exists in config)                     │
│ 2. Get coordinates: aws_fetcher.get_location_coordinates()  │
│ 3. If date == today:                                        │
│    └── weather_api.get_current_weather()                    │
│        └── Open-Meteo Forecast API                          │
│ 4. If date < today:                                         │
│    └── weather_api.get_historical_weather()                 │
│        └── Open-Meteo Archive API                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Response:                                                   │
│ {success: true,                                             │
│  weather: {temperature_celsius, wind_speed_kmh, ...},       │
│  location: "Menlo Park, CA",                                │
│  date: "2025-10-21",                                        │
│  time: "13:00",                                             │
│  unit: "celsius"}                                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ JavaScript (displayWeather):                                │
│ - Display temperature, wind, precipitation                  │
│ - Convert units if needed (F/mph)                           │
│ - Show weather icon based on conditions                     │
│ - Update UI card                                            │
└─────────────────────────────────────────────────────────────┘
```

---

### **Flow 4: Web UI - "Historic Weather" Button (10-Year Graphs)**

```
┌─────────────────────────────────────────────────────────────┐
│ User Action:                                                │
│ 1. Select location: "Menlo Park, CA"                        │
│ 2. Select date: 2025-10-21                                  │
│ 3. Select time: 13:00                                       │
│ 4. Click "Historic Weather"                                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ JavaScript:                                                 │
│ GET /api/temperature-graph-predefined?location=...&date=...│
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Backend (routes.py):                                        │
│ For years 2025, 2024, 2023, ..., 2016 (10 years):          │
│   For each year's Oct 21 @ 13:00:                          │
│     1. Try AWS S3/Athena:                                   │
│        aws_fetcher.query_historic_data(location, date, hour)│
│     2. If AWS data found:                                   │
│        └── Use AWS data (faster, your backfilled data)      │
│     3. If AWS data NOT found:                               │
│        └── Fallback: weather_api.get_historical_weather()   │
│            └── Open-Meteo Archive API                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Collect 10 years of data points:                           │
│ [{date: 2025-10-21, temp: 21°C, ...},                      │
│  {date: 2024-10-21, temp: 19°C, ...},                      │
│  {date: 2023-10-21, temp: 22°C, ...},                      │
│  ... 10 data points total]                                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Generate 4 Matplotlib Graphs (graph_generator.py):         │
│ 1. Temperature History (line graph with trend)             │
│ 2. Wind Speed History (bar graph)                          │
│ 3. Precipitation History (bar graph)                       │
│ 4. Cloud Coverage History (area graph)                     │
│                                                             │
│ Calculate Statistics:                                       │
│ - Min/Max/Avg for each metric                              │
│ - Temperature range                                         │
│ - Total precipitation                                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Convert to Base64 PNG:                                      │
│ - Each graph → base64 string                                │
│ - Include in JSON response                                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Response:                                                   │
│ {success: true,                                             │
│  graph_data: {                                              │
│    temperature_graph: "iVBORw0KG...",                       │
│    wind_graph: "iVBORw0KG...",                              │
│    precipitation_graph: "iVBORw0KG...",                     │
│    cloud_coverage_graph: "iVBORw0KG...",                    │
│    stats: {temperature: {...}, wind: {...}, ...}            │
│  },                                                         │
│  years_count: 10,                                           │
│  data_source: "Mixed (AWS S3 + Open-Meteo)"}               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ JavaScript (displayGraphs):                                 │
│ - Decode base64 PNG images                                  │
│ - Display 4 graphs in UI                                    │
│ - Show statistics under each graph                          │
│ - Smooth scroll to graph section                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 **Storage Architecture**

### **S3 Bucket Structure:**

```
s3://weather-data-yy/
└── weather-data/
    ├── location=Menlo_Park_CA/
    │   ├── year=2015/
    │   │   ├── month=07/
    │   │   │   ├── day=19/
    │   │   │   │   └── weather_data_2015-07-19.parquet
    │   │   │   ├── day=20/
    │   │   │   │   └── weather_data_2015-07-20.parquet
    │   │   │   └── ...
    │   │   ├── month=08/
    │   │   └── ...
    │   ├── year=2016/
    │   ├── ...
    │   └── year=2025/
    ├── location=San_Francisco_CA/
    ├── location=Walnut_Creek_CA/
    └── location=Carmel-By-The-Sea_CA/
```

**Partitioning Strategy:**
- **Level 1**: `location` - Enables per-location queries
- **Level 2**: `year` - Enables year-based filtering
- **Level 3**: `month` - Enables month-based filtering
- **Level 4**: `day` - Enables day-based filtering

**File Naming:**
- Pattern: `weather_data_{YYYY-MM-DD}.parquet`
- Example: `weather_data_2025-10-21.parquet`

**Benefits:**
- ✅ Efficient partition pruning in Athena queries
- ✅ Easy to identify data by date
- ✅ Supports time-range queries
- ✅ Scales to millions of files

---

### **Parquet File Schema:**

```
location: string
date: string (YYYY-MM-DD)
hour: int (0-23)
temperature_celsius: float
wind_speed_kmh: float
precipitation_mm: float
cloud_coverage_percent: float
ingestion_timestamp: string (ISO 8601)
```

---

## 🚀 **Deployment**

### **Local Development:**

```bash
# 1. Setup environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure .env
cat > .env << 'EOF'
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_DEFAULT_REGION=us-east-1
AWS_S3_BUCKET=weather-data-yy
OPENWEATHER_API_KEY=optional_key
EOF

# 3. Run web app
python start_web_app.py
# Access: http://localhost:5001
```

---

### **Airflow Deployment:**

```bash
# 1. Start Airflow with Docker Compose
docker-compose -f docker-compose.airflow.yml up -d

# 2. Access Airflow UI
# http://localhost:8081
# Username: airflow
# Password: airflow

# 3. Enable DAGs
# - daily_weather_ingestion (runs daily at 6 AM)
# - backfilling (manual trigger only)

# 4. Trigger backfilling for each location
# Via UI: Trigger DAG w/ config
# {"start_date": "2025-07-19", "end_date": "2025-10-19", "location": "Menlo Park, CA"}
```

**Volume Mounts:**
```yaml
- ./dags:/opt/airflow/dags
- ./pipelines:/opt/airflow/pipelines
- ./app:/opt/airflow/app
- ./config:/opt/airflow/config
- ./logs:/opt/airflow/logs
```

**Environment Variables:**
```yaml
PYTHONPATH: /opt/airflow
OPENWEATHER_API_KEY: "..."
AWS_ACCESS_KEY_ID: "..."
AWS_SECRET_ACCESS_KEY: "..."
AWS_DEFAULT_REGION: "us-east-1"
AWS_S3_BUCKET: "weather-data-yy"
```

---

## 🧩 **Component Integration**

### **How Components Work Together:**

```
┌─────────────────────────────────────────────────────────────┐
│                         USER                                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      WEB UI                                 │
│  (web_interface/ + app/routes.py)                           │
│                                                             │
│  - Select location, date, time                              │
│  - "Get Weather" → Single point data                        │
│  - "Historic Weather" → 10-year graphs                      │
└─────────────────────────────────────────────────────────────┘
            ↓                               ↓
┌──────────────────────────┐   ┌──────────────────────────┐
│   app/weather_api.py     │   │  app/aws_fetching.py     │
│   (Open-Meteo API)       │   │  (AWS S3/Athena)         │
│                          │   │                          │
│  - Current weather       │   │  - Query S3 data         │
│  - Historical weather    │   │  - Athena queries        │
│  - 24-hour data          │   │  - Location lookup       │
└──────────────────────────┘   └──────────────────────────┘
            ↓                               ↓
┌─────────────────────────────────────────────────────────────┐
│                   app/utils/                                │
│                                                             │
│  - graph_generator.py (matplotlib graphs)                   │
│  - response_formatter.py (JSON responses)                   │
│  - query_utils.py (validation)                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   RESPONSE TO USER                          │
│  - Weather data card                                        │
│  - OR 4 historical graphs with statistics                   │
└─────────────────────────────────────────────────────────────┘
```

---

```
┌─────────────────────────────────────────────────────────────┐
│                      AIRFLOW                                │
│  (Scheduler + Worker + Webserver)                           │
└─────────────────────────────────────────────────────────────┘
            ↓                               ↓
┌──────────────────────────┐   ┌──────────────────────────┐
│  daily_ingestion_dag.py  │   │  backfilling_dag.py      │
│  (Schedule: Daily 6 AM)  │   │  (Manual trigger)        │
└──────────────────────────┘   └──────────────────────────┘
            ↓                               ↓
┌──────────────────────────┐   ┌──────────────────────────┐
│  pipelines/              │   │  pipelines/              │
│  daily_ingest.py         │   │  backfilling_ingest.py   │
└──────────────────────────┘   └──────────────────────────┘
            ↓                               ↓
┌─────────────────────────────────────────────────────────────┐
│                 app/weather_api.py                          │
│              (Open-Meteo Archive API)                       │
│                                                             │
│  get_historical_weather_all_hours(lat, lon, date)          │
│  └── Returns 24 hours of weather data                       │
└─────────────────────────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────────────────────────┐
│                 pipelines/s3_writer.py                      │
│                                                             │
│  save_to_s3_parquet(df, location, date)                    │
│  └── S3: weather-data/location=/year=/month=/day=/*.parquet│
└─────────────────────────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────────────────────────┐
│                      AWS S3                                 │
│              (Partitioned Parquet Files)                    │
│                                                             │
│  - Queryable via Athena                                     │
│  - Used by Web UI for 10-year graphs                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 **Current Status Summary**

### ✅ **Fully Implemented:**

1. **Web UI:**
   - ✅ Location selection (4 CA locations)
   - ✅ Date/time picker (today to 1 year back)
   - ✅ "Get Weather" - Current/historical weather
   - ✅ "Historic Weather" - 10-year trend graphs
   - ✅ Unit conversion (Celsius/Fahrenheit, km/h/mph)

2. **Backend API:**
   - ✅ `WeatherAPI` class - Open-Meteo integration
   - ✅ `AWSDataFetcher` class - S3/Athena queries
   - ✅ Flask routes for all endpoints
   - ✅ Graph generation with matplotlib
   - ✅ Response formatting and validation

3. **Data Pipelines:**
   - ✅ Daily ingestion (1 week ago data)
   - ✅ Backfilling (date range, single location)
   - ✅ S3 writer with partitioned storage

4. **Airflow DAGs:**
   - ✅ `daily_weather_ingestion` - Scheduled daily
   - ✅ `backfilling` - Manual trigger

5. **Configuration:**
   - ✅ Centralized YAML configs
   - ✅ Environment variable support
   - ✅ Location management

6. **Testing:**
   - ✅ Pytest suite for APIs and AWS
   - ✅ Environment-based credential loading

---

### ⚠️ **Notes:**

1. **Open-Meteo API Only**: 
   - Changed from OpenWeather to Open-Meteo for ALL weather data
   - ✅ Completely FREE (no API key needed)
   - ✅ Current weather via Forecast API
   - ✅ Historical weather via Archive API

2. **Daily Ingestion Date:**
   - Processes **1 week ago** (not yesterday)
   - Reason: Open-Meteo Archive API has data delay

3. **AWS S3 + Open-Meteo Hybrid:**
   - 10-year graphs: **Try AWS first**, fallback to Open-Meteo
   - Single weather: **Open-Meteo only** (faster)

4. **Backfilling:**
   - Manual process (run DAG 4 times for 4 locations)
   - Alternative: Could create multi-location script

---

## 🎯 **How to Use**

### **1. View Current Weather:**
```
Web UI → Select location → Today's date → Click "Get Weather"
→ Shows current weather from Open-Meteo Forecast API
```

### **2. View Past Weather:**
```
Web UI → Select location → Past date (up to 1 year) → Click "Get Weather"
→ Shows historical weather from Open-Meteo Archive API
```

### **3. View 10-Year Trends:**
```
Web UI → Select location → Any date → Click "Historic Weather"
→ Shows 4 graphs with 10 years of data (AWS S3 + Open-Meteo fallback)
```

### **4. Backfill Data:**
```
Airflow UI → backfilling DAG → Trigger w/ config
→ {"start_date": "2025-07-19", "end_date": "2025-10-19", "location": "Menlo Park, CA"}
→ Fetches data from Open-Meteo → Saves to S3
```

### **5. Daily Automation:**
```
Airflow Scheduler (6 AM daily) → daily_weather_ingestion DAG
→ Fetches 1-week-ago data for all 4 locations → Saves to S3
```

---

This architecture provides a clean, scalable, and maintainable weather data platform! 🎉

