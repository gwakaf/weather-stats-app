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

