import pytest
from app.services.fhir_service import FHIRService
from unittest.mock import AsyncMock, Mock
import httpx

@pytest.mark.asyncio
class TestFHIRService:
    async def test_get_patients_by_postal_code(self):
        # Mock response data
        mock_response = {
            "entry": [
                {
                    "resource": {
                        "id": "123",
                        "name": [{"given": ["John"]}],
                        "gender": "male",
                        "birthDate": "1990-01-01"
                    }
                }
            ]
        }
        
        # Create mock client
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response_obj = Mock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status = Mock()
        mock_client.get.return_value = mock_response_obj
        
        # Initialize service with mock client
        fhir_service = FHIRService(client=mock_client)
        
        # Test
        result = await fhir_service.get_patients_by_postal_code("12345")
        
        # Verify the mock was called correctly
        mock_client.get.assert_called_once_with(
            f"{FHIRService.BASE_URL}/Patient",
            params={"address-postalcode": "12345"}
        )
        mock_response_obj.raise_for_status.assert_called_once()
        mock_response_obj.json.assert_called_once()
        assert result == mock_response

    async def test_parse_patient(self):
        fhir_service = FHIRService()
        patient_data = {
            "id": "123",
            "name": [{"given": ["John"]}],
            "gender": "male",
            "birthDate": "1990-01-01"
        }
        
        result = await fhir_service.parse_patient(patient_data)
        assert result["id"] == "123"
        assert result["first_name"] == "John"
        assert result["gender"] == "male" 