# FHIR Patient Data Service

A FastAPI-based service for managing patient data using the FHIR standard. This service provides endpoints for storing and retrieving patient information and their medical observations.

## Features
- FHIR R5 Integration
- Async Database Operations
- JWT Authentication
- Health Check Endpoints
- Patient Data Management
- Observation Tracking
- Postal Code Based Search

## Setup and Installation

### Prerequisites
- Python 3.9+
- Docker and Docker Compose
- PostgreSQL (if running locally without Docker)

### Getting Started

1. Clone the repository and navigate to the project directory.

2. Set up the Python environment:
```bash
# Create a virtual environment using python3
python3 -m venv venv

# Activate the virtual environment (for Linux/MacOS)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Save all dependencies to requirements.txt if more packages are installed
pip freeze > requirements.txt
```

### Docker Setup and Commands

1. Remove existing docker-compose (if outdated):
```bash
sudo rm /usr/bin/docker-compose
```

2. Install the latest version of Docker Compose:
```bash
# Download the latest version of Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Make it executable
sudo chmod +x /usr/local/bin/docker-compose

# Create a symbolic link
sudo ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose
```

3. Verify the installation:
```bash
docker-compose --version
```

4. Check your Docker configuration:
```bash
# Check Docker version
docker version

# Check Docker info
docker info
```


5. To stop any running containers:
```bash
docker-compose down -v
```

6. To rebuild and start the containers:
```bash
docker-compose up --build
```

## Authentication

The service uses JWT-based authentication for protected endpoints. To obtain a token:

1. Make a POST request to `/token` with:
```json
{
    "username": "admin",
    "password": "admin"
}
```

2. Use the returned token in subsequent requests:
```bash
Authorization: Bearer <your_token>
```
    
## API Documentation

### Health Check
- **Endpoint**: `GET /`
- **Description**: Checks the health status of the service
- **Response Example**:
```json
{
    "status": "healthy",
    "version": "1.0.0",
    "database": "connected",
    "timestamp": "2024-03-14T12:00:00.000Z"
}
```

### Populate Patient Data
- **Endpoint**: `POST /populate/{postal_code}`
- **Description**: Fetches and stores patient data for a given postal code
- **Parameters**:
  - `postal_code` (path parameter): Postal code to search for patients
- **Response Example**:
```json
{
    "message": "Data populated successfully"
}
```
- **Error Responses**:
  - 404: No patients found for postal code
  - 500: Database or FHIR service errors

### Get Patient
- **Endpoint**: `GET /patients/{search_term}`
- **Description**: Retrieves patient information by ID or first name
- **Parameters**:
  - `search_term` (path parameter): Patient ID or first name
- **Response Example**:
```json
{
    "id": "patient123",
    "first_name": "John",
    "gender": "male",
    "birth_date": "1990-01-01"
}
```
- **Error Responses**:
  - 404: Patient not found
  - 500: Database error

### Get Patient Observations
- **Endpoint**: `GET /patients/{patient_id}/observations`
- **Description**: Retrieves all observations for a specific patient
- **Parameters**:
  - `patient_id` (path parameter): Patient's unique identifier
- **Response Example**:
```json
[
    {
        "id": "obs123",
        "resource_type": "Observation",
        "status": "final",
        "patient_id": "patient123"
    }
]
```
- **Error Responses**:
  - 404: No observations found
  - 500: Database error

## Environment Variables

Create a `.env` file in the project root with the following variables:
```
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=fhir_db
POSTGRES_HOST=db
```

## Testing

To run the test suite:
```bash
pytest tests/
```

## FHIR Integration Notes

The service integrates with the HAPI FHIR server (R5) and follows the FHIR specification for handling patient data. Search responses are returned as Bundles, with the `entry` array containing the matching resources.

According to the FHIR specification, search responses are always returned as a Bundle, and the `entry` array is where the actual matching resources are stored. From [build.fhir.org/search.html](https://build.fhir.org/search.html):

> Search responses are always returned as a Bundle. Search result bundles convey a lot of metadata in addition to any possible results, using the various elements available in the bundle resource.

The `entry` array in the Bundle contains the matching resources, and each entry has a `mode` that indicates why it's included. As explained in the specification:

> Within the results bundle, there are three types of entries that MAY be present, identified by the search mode of the entry: `match`, `include`, or `outcome`.

So when we check `patients_data.get("entry")`, we're verifying that the search returned some matching results (if there are no matches, the `entry` array would be empty or missing).

This is why the code raises a 404 error if no `entry` is found:
```python:app/main.py
if not patients_data.get("entry"):
    raise HTTPException(
        status_code=404,
        detail=f"No patients found for postal code {postal_code}"
    )
```

The structure follows the standard FHIR Bundle format, which looks like:
```json
{
    "resourceType": "Bundle",
    "type": "searchset",
    "entry": [
        {
            "resource": {
                "resourceType": "Patient",
                // ... patient data ...
            }
        }
    ]
}
```