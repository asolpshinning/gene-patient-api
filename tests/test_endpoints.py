import pytest
from app.models import Patient, Observation
from sqlalchemy import select
from unittest.mock import patch

pytestmark = pytest.mark.asyncio

class TestEndpoints:
    async def test_health_check(self, client):
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "database" in data
        assert "timestamp" in data

    async def test_get_patient(self, client, test_db):
        # Create test patient
        patient = Patient(
            id="test123",
            first_name="John",
            postal_code="12345"
        )
        test_db.add(patient)
        await test_db.commit()
        await test_db.refresh(patient)

        # Test get patient by ID
        response = await client.get("/patients/test123")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test123"
        assert data["first_name"] == "John"

        # Test patient not found
        response = await client.get("/patients/nonexistent")
        assert response.status_code == 404

    async def test_get_patient_observations(self, client, test_db):
        # Create test patient
        patient = Patient(
            id="test456",
            first_name="John",
            postal_code="12345"
        )
        test_db.add(patient)
        await test_db.commit()
        
        observation = Observation(
            id="obs123",
            patient_id="test456",
            resource_type="Observation",
            status="final"
        )
        test_db.add(observation)
        await test_db.commit()

        # Test get observations
        response = await client.get("/patients/test456/observations")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "obs123"

    async def test_populate_data(self, client, test_db):
        postal_code = "12345"
        mock_patient_data = {
            "entry": [
                {
                    "resource": {
                        "id": "test789",
                        "name": [{"given": ["John"]}],
                        "gender": "male",
                        "birthDate": "1990-01-01"
                    }
                }
            ]
        }

        # Mock FHIR service responses
        with patch('app.services.fhir_service.FHIRService.get_patients_by_postal_code') as mock_get_patients:
            mock_get_patients.return_value = mock_patient_data
            
            response = await client.post(f"/populate/{postal_code}")
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Data populated successfully"

            # Verify database state
            result = await test_db.execute(
                select(Patient).filter_by(postal_code=postal_code)
            )
            patients = result.scalars().all()
            assert len(patients) == 1
            assert patients[0].id == "test789"