## Scope of Testing
Code components, main functionality, data pipelines

## Testing Objectives
Make using, updating and debugging the app as easier as possible. Make sure the app data integrity.

## Test Approach and Tools
Unit tests:	pytest
Mocking AWS:	moto, botocore.stubber
Flask testing:	app.test_client()
DAG tests:	airflow.models.DAG
Coverage:	pytest-cov