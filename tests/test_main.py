import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

# 1. Mock 'wait_for_db' before importing the app
with patch('app.main.wait_for_db') as mock_wait:
    mock_wait.return_value = None  # Prevent actual DB connection
    from fastapi.testclient import TestClient
    from app.main import app
    from app import models

# 2. Initialize TestClient after mocking
client = TestClient(app)

# 3. Fixture to mock the database session
@pytest.fixture
def mock_db_session():
    with patch('app.database.get_db') as mock_get_db:
        mock_session = MagicMock(spec=Session)
        mock_get_db.return_value = mock_session
        yield mock_session

# 4. Fixture to mock the FHIRService
@pytest.fixture
def mock_fhir_service():
    with patch('app.main.FHIRService') as mock_service:
        instance = mock_service.return_value
        yield instance

# 5. Define your tests

def test_health_check(mock_db_session, mock_fhir_service):
    response = client.get("/")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "healthy"
    assert json_data["version"] == "1.0.0"
    assert json_data["database"] == "connected"
    assert "timestamp" in json_data

def test_get_patient_success(mock_db_session, mock_fhir_service):
    # Arrange
    patient = MagicMock()
    patient.id = "123"
    patient.first_name = "John"
    # More specific mock setup
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_query.filter.return_value = mock_filter
    mock_filter.first.return_value = patient
    mock_db_session.query.return_value = mock_query

    # Act
    response = client.get("/patients/123")

    # Assert
    assert response.status_code == 200
    assert response.json() == {"id": "123", "first_name": "John"}

def test_get_patient_not_found(mock_db_session, mock_fhir_service):
    # Arrange
    mock_db_session.query.return_value.filter.return_value.first.return_value = None

    # Act
    response = client.get("/patients/999")

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "Patient not found with ID or name: 999"}

def test_get_patient_database_error(mock_db_session, mock_fhir_service):
    # Arrange
    mock_db_session.query.side_effect = SQLAlchemyError("Database error")

    # Act
    response = client.get("/patients/123")

    # Assert
    assert response.status_code == 500
    assert response.json() == {"detail": "Database error: Database error"}

def test_get_patient_observations_success(mock_db_session, mock_fhir_service):
    # Arrange
    observation = MagicMock()
    observation.id = "obs1"
    observation.patient_id = "123"
    observation.value = "Test Observation"
    # More specific mock setup
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_query.filter.return_value = mock_filter
    mock_filter.all.return_value = [observation]
    mock_db_session.query.return_value = mock_query

    # Act
    response = client.get("/patients/123/observations")

    # Assert
    assert response.status_code == 200
    assert response.json() == [
        {"id": "obs1", "patient_id": "123", "value": "Test Observation"}
    ]

def test_get_patient_observations_not_found(mock_db_session, mock_fhir_service):
    # Arrange
    mock_db_session.query.return_value.filter.return_value.all.return_value = []

    # Act
    response = client.get("/patients/123/observations")

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "No observations found for patient ID: 123"}

def test_get_patient_observations_database_error(mock_db_session, mock_fhir_service):
    # Arrange
    mock_db_session.query.side_effect = Exception("Database error")

    # Act
    response = client.get("/patients/123/observations")

    # Assert
    assert response.status_code == 500
    assert response.json() == {"detail": "Database error"}

def test_populate_data_success(mock_db_session, mock_fhir_service):
    # Arrange
    mock_fhir_service.get_patients_by_postal_code.return_value = {
        "entry": [
            {"resource": {"id": "p1", "name": "John Doe"}}
        ]
    }
    mock_fhir_service.parse_patient.return_value = {"id": "p1", "first_name": "John"}
    mock_fhir_service.get_observations_by_patient_id.return_value = {
        "entry": [
            {"resource": {"id": "o1", "value": "Blood Pressure"}}
        ]
    }
    mock_fhir_service.parse_observation.return_value = {"id": "o1", "value": "Blood Pressure"}

    # Mock the database session to avoid actual DB operations
    mock_db_session.merge.return_value = None
    mock_db_session.commit.return_value = None

    # Act
    response = client.post("/populate/12345")

    # Assert
    assert response.status_code == 200
    assert response.json() == {"message": "Data populated successfully"}
    assert mock_db_session.merge.call_count == 2  # 1 patient + 1 observation

def test_populate_data_no_patients_found(mock_db_session, mock_fhir_service):
    # Arrange
    mock_fhir_service.get_patients_by_postal_code.return_value = {}

    # Act
    response = client.post("/populate/12345")

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "No patients found for postal code 12345"}

def test_populate_data_fhir_service_error(mock_db_session, mock_fhir_service):
    # Arrange
    mock_fhir_service.get_patients_by_postal_code.side_effect = Exception("FHIR Service error")

    # Act
    response = client.post("/populate/12345")

    # Assert
    assert response.status_code == 500
    assert response.json() == {"detail": "Error: FHIR Service error"}

def test_populate_data_database_commit_error(mock_db_session, mock_fhir_service):
    # Arrange
    mock_fhir_service.get_patients_by_postal_code.return_value = {
        "entry": [
            {"resource": {"id": "p1", "name": "John Doe"}}
        ]
    }
    mock_fhir_service.parse_patient.return_value = {"id": "p1", "first_name": "John"}
    mock_fhir_service.get_observations_by_patient_id.return_value = {}
    
    # Mock the database error
    mock_db_session.commit.side_effect = SQLAlchemyError("Commit failed")
    mock_db_session.rollback.return_value = None

    # Act
    response = client.post("/populate/12345")

    # Assert
    assert response.status_code == 500
    assert response.json() == {"detail": "Database error while saving data: Commit failed"}