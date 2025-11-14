# ☀️ Weather Finder – Historic Weather Lookup for Event Planning
## Project Business Goal
Help user to make an informed decision on event planning using wether statistics data for the last 10 years for the location of their choice.

## Project Development Goals
- **Reliable Data Ingestion**: automated incremental daily ingestion of weather data with schema validation and built-in monitoring to ensure data quality.
- **Scalability**: on-demand backfilling pipelines that allow  expansion to new locations and historical ranges.
- **ETL System**: orchestrated extraction, transformation, and loading raw format data from external APIs to AWS S3 storage, applying formatting and data modeling techniques.
- **Data lake**: organized centralized repository in AWS S3 for structured  data storage.
- **Optimized Data Access**: fast querying and efficient storage using columnar Parquet format, hierarchical partitioning (by date/location), and Athena for querying at scale.
- **Scalability**: leverage AWS S3 storage to accommodate growing data volumes without re-architecting the system.
- **Monitoring & Observability**: Track data pipeline execution, failures, and performance metrics through Airflow's native monitoring capabilities and custom logging.

## Components and Tech Stack
- **Frontend**: HTML5/CSS3, JavaScript
- **Backend**: Flask, Python
- **Cloud Infrastructure (AWS)**: S3, Athena, Glue
- **Infrastructure as Code**: Terraform (S3 buckets, Glue database, Athena workgroup configuration)
- **Data Orchestration**: Apache Airflow, Docker Compose
- **External APIs**: Open-Meteo API, OpenWeather Geocoding API
- **Testing**: Pytest


## Architecture Diagram
The app consists of a web interface, a Flask backend, and a cloud-native data pipeline using Airflow, S3, and Athena.
It fetches historic weather data using the Open-Meteo API, stores it in AWS S3 in partitioned Parquet format, and allows fast querying via Athena.
Current weather is fetched live from the OpenWeather API.

<img width="707" height="440" alt="Screenshot 2025-10-28 at 2 55 34 PM" src="https://github.com/user-attachments/assets/c238fd3a-9ae9-42a6-8427-8367ca8af100" />

## Cost Overview

This mini-, practice costs near zero, because it stays within AWS Free Tier due to small data volume, efficient formats, and lightweight queries.See the breakdown below:

| **AWS Service**      | **Optimization Strategy**                                                                 | **Monthly Cost** |
|----------------------|--------------------------------------------------------------------------------------------|------------------|
| **S3 Storage**       | Small Data Volume and Parquet Compression: ~86 MB of total data with ~96 records/day (≈ 24 KB/day).  Free tier includes 5 GB.                  | **$0.00**        |
| **S3 Requests**      | Only a handful of PUTs/day and occasional GETs: under free tier limits.              | **$0.00**        |
| **Athena Queries**   | Query scans ~6 KB due to partition pruning. Free tier covers first 10 MB/query.           | **$0.00**        |
| **Glue Catalog**     | ~14,600 partitions. Free-tier has 1M  object limit.                             | **$0.00**        |
| **EC2, RDS**    | Serverless Architecture: No EC2, RDS, or idle resource cost.   | **$0.00**        |
| **TOTAL**            |                                                                                           | **$0.00 / month** |

Even with **1,000 queries/day**, total Athena scan volume is ~180 MB/month, resulting in **$0.00/month** cost under current pricing.


### Cost Scaling Estimate

| **Scenario**        | **Locations** | **Queries/day** | **Monthly Cost** | **Annual Cost** |
|---------------------|---------------|------------------|------------------|-----------------|
| **Current**       | 4             | 10 – 1,000       | $0.00            | $0.00           |
| **A: Small**      | 10            | 1,000            | $0.00            | $0.00           |
| **B: Medium**     | 50            | 10,000           | $0.03            | $0.36           |
| **C: Large**      | 100           | 50,000           | $0.10            | $1.20           |
| **D: Enterprise** | 500           | 100,000          | $0.51            | $6.12           |

Costs mostly estimate Athena query volume, assumig S3 storage and Glue catalog usage remain under Free Tier limits in most scenarios.


## User Experience
Planning an outdoor event months in advance can be stressful — especially when the weather is unpredictable. This app helps solve that problem by letting users:
- Select a venue (from a predefined list of locations)
- Choose a specific day and time
- Instantly view weather history for the same date and hour over the past 10 years
  
💡 This enables data-driven decisions for event planning by identifying patterns like rain probability, temperature ranges, and wind conditions — helping users find the most weather-friendly dates and venues.

<img width="436" height="1209" alt="127 0 0 1_5001_" src="https://github.com/user-attachments/assets/6f772b92-fc35-4760-a54c-a988e8c0df33" />

## Project Structure

```
weather_finder/
├── app/                   # Application backend
│   ├── routes.py          # API endpoints
│   ├── aws_fetching.py    # AWS S3/Athena queries
│   ├── weather_api.py     # Open-Meteo API integration
│   └── utils/             # Graph generation, response formatting
├── aws_infra/             # AWS infrastructure (Terraform)
│   ├── main.tf           
│   ├── glue.tf           
│   └── s3.tf              
├── config/                # Configuration files
│   ├── aws_infra_config.yaml  # AWS infrastructure config
│   ├── backfilling_config.yaml # Backfilling parameters
│   ├── config.py          # Functions to read YAML configuration files
│   └── locations.yaml     # Locations list
├── dags/                  # Airflow DAGs
│   ├── daily_ingestion_dag.py # Daily ingestion DAG fetches data and saves to S3
│   └── backfilling_dag.py # Backfilling DAG fetches historic data for specific date ranges
├── pipelines/             # Data ingestion pipelines logic
│   ├── daily_ingest.py    
│   ├── backfilling_ingest.py
│   └── s3_writer.py
├── tests/                 # Test suite
│   └── tests.py
├── web_interface/         # web UI
│   ├── templates/index.html
│   └── static/js/script.js
├── requirements.txt
├── .env
└── README.md
```

## Features

### 🌐 Web Interface
- **Current Weather**: Real-time weather data for any location
- **Historic Analysis**: 10-year temperature, wind, and precipitation trends
- **Unit Conversion**: Celsius/Fahrenheit temperature, km/h/mph wind speed
- **Data Sources**: Open-Meteo API for current data, AWS S3 for predefined locations
- **Interactive Charts**: Matplotlib-generated visualizations

### 📊 Data Ingestion
- **Historic Data**: 5-year historical data ingestion for predefined locations
- **Daily Updates**: Automatic daily ingestion of yesterday's weather data
- **Rate Limiting**: Respects Open-Meteo API limits (10,000 requests/day)
- **Batch Processing**: Optimized batch sizes for efficient ingestion

### ☁️ AWS Integration
- **S3 Storage**: Parquet files partitioned by location and date
- **Athena Queries**: SQL queries for historic data retrieval
- **Glue Catalog**: Automated table management
- **Predefined Locations**: Menlo Park, Walnut Creek, San Francisco

### 🔄 Airflow Orchestration
- **Historic Ingestion DAG**: Single DAG processing one batch per day
- **Daily Ingestion DAG**: Daily collection of yesterday's weather data
- **Progress Tracking**: Airflow Variables for batch progress
- **Error Handling**: Automatic retries and failure recovery

## Quick Start

### 1. Setup Environment

```bash
# Clone the repository
git clone <repository-url>
cd weather_finder

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your configuration
```

### 2. Run Web Interface

```bash
# Start the web interface
cd web_interface
python run.py

# Access at http://localhost:5000
```

### 3. Generate Historic Data Schedule

```bash
# Generate Airflow schedule for historic data
cd dags
python generate_airflow_schedule.py --show-schedule

# This creates:
# - weather_ingestion_dag.py (Airflow DAG)
# - date_pairs.json (Date pairs for ingestion)
# - airflow_schedule.csv (Schedule overview)
```

### 4. Setup Airflow (Optional)

```bash
# Copy DAGs to Airflow
cp weather_ingestion_dag.py $AIRFLOW_HOME/dags/
cp daily_weather_ingestion_dag.py $AIRFLOW_HOME/dags/
cp ingest_batch_airflow.py $AIRFLOW_HOME/dags/

# Copy date pairs
cp ../historic_data/date_pairs.json $AIRFLOW_HOME/dags/

# Set initial batch index
airflow variables set weather_ingestion_batch_index 0
```

## Configuration

### Environment Variables (.env)

```bash
# AWS Configuration
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1

# Flask Configuration
FLASK_SECRET_KEY=your_secret_key
HOST=0.0.0.0
PORT=5000
FLASK_DEBUG=True
```

### Historic Data Configuration (historic_data/ingestion_config.yaml)

```yaml
# API Configuration
api:
  daily_limit: 10000
  requests_per_location_per_day: 96
  safety_margin: 0.8

# Locations
locations:
  - name: "Menlo Park, CA"
    lat: 37.4529
    lon: -122.1817
  - name: "Walnut Creek, CA"
    lat: 37.9101
    lon: -122.0652

# Ingestion period
ingestion_period:
  start_date: "2019-01-01"
  end_date: "2024-12-31"
```

## API Endpoints

### Web Interface APIs

- `POST /api/current_weather` - Get current weather for location
- `POST /api/historic_weather` - Get historic weather data and graphs
- `GET /api/predefined_locations` - Get list of predefined locations

### Example API Usage

```javascript
// Get current weather
fetch('/api/current_weather', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    lat: 37.4529,
    lon: -122.1817,
    location_name: "Menlo Park, CA"
  })
});

// Get historic weather
fetch('/api/historic_weather', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    lat: 37.4529,
    lon: -122.1817,
    date: "2024-01-15",
    time: "14:00",
    unit: "celsius",
    location_type: "predefined"
  })
});
```

## Data Flow

### Current Weather Flow
1. User requests current weather via web interface
2. `weather_api.py` calls Open-Meteo API
3. Data is returned to user with real-time information

### Historic Data Flow
1. User requests historic weather analysis
2. For predefined locations: Query AWS S3/Athena
3. For custom locations: Query Open-Meteo API
4. Generate matplotlib charts
5. Return data and visualizations

### Data Ingestion Flow
1. **Historic Ingestion**: Airflow DAG processes one batch per day
2. **Daily Ingestion**: Airflow DAG fetches yesterday's data daily
3. Data is saved to S3 as partitioned parquet files
4. Glue catalog is updated for Athena queries

## Airflow DAGs

### Historic Data Ingestion DAG
- **Schedule**: Daily at 2 AM
- **Purpose**: Process historic data batches
- **Progress**: Tracked via Airflow Variables
- **Duration**: ~53 days for 5 years of data

### Daily Weather Ingestion DAG
- **Schedule**: Daily at 6 AM
- **Purpose**: Collect yesterday's weather data
- **Locations**: All predefined locations
- **Output**: 24 hours of data per location

## Testing

### Test Airflow Logic
```bash
cd dags
python test_airflow_logic.py
```

### Test AWS Integration
```bash
cd aws_infrastructure
python test_aws_integration.py
```

### Test Web Interface
```bash
cd web_interface
python -m pytest tests/
```

## Monitoring

### Airflow Monitoring
```bash
# Check DAG status
airflow dags list-runs weather_data_ingestion

# Check batch progress
airflow variables get weather_ingestion_batch_index

# View logs
airflow tasks logs weather_data_ingestion process_daily_batch 2024-01-01
```

### AWS Monitoring
- S3 bucket metrics
- Athena query performance
- Glue job status

## Troubleshooting

### Common Issues

1. **API Rate Limiting**
   - Check Open-Meteo API limits
   - Reduce batch sizes in config
   - Add delays between requests

2. **AWS Permissions**
   - Verify IAM roles and policies
   - Check S3 bucket access
   - Ensure Glue permissions

3. **Airflow Issues**
   - Check DAG file paths
   - Verify Python dependencies
   - Review Airflow logs

### Logs
- Web interface: Flask logs
- Airflow: Airflow task logs
- AWS: CloudWatch logs

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review Airflow and AWS logs
3. Open an issue on GitHub 
