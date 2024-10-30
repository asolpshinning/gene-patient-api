import requests
from datetime import datetime
from requests.exceptions import HTTPError, ConnectionError, Timeout, JSONDecodeError
from typing import Dict, Any, Optional

class FHIRService:
    BASE_URL = "https://hapi.fhir.org/baseR5"

    @staticmethod
    def get_patients_by_postal_code(postal_code: str) -> Dict[str, Any]:
        try:
            response = requests.get(
                f"{FHIRService.BASE_URL}/Patient?address-postalcode={postal_code}",
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Timeout:
            raise Exception("FHIR server request timed out")
        except ConnectionError:
            raise Exception("Failed to connect to FHIR server")
        except HTTPError as e:
            raise Exception(f"FHIR server returned an error: {e.response.status_code}")
        except JSONDecodeError:
            raise Exception("Invalid JSON response from FHIR server")
        except Exception as e:
            raise Exception(f"Unexpected error while fetching patients: {str(e)}")

    @staticmethod
    def get_observations_by_patient_id(patient_id: str) -> Dict[str, Any]:
        try:
            response = requests.get(
                f"{FHIRService.BASE_URL}/Observation?subject=Patient/{patient_id}",
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Timeout:
            raise Exception("FHIR server request timed out")
        except ConnectionError:
            raise Exception("Failed to connect to FHIR server")
        except HTTPError as e:
            raise Exception(f"FHIR server returned an error: {e.response.status_code}")
        except JSONDecodeError:
            raise Exception("Invalid JSON response from FHIR server")
        except Exception as e:
            raise Exception(f"Unexpected error while fetching observations: {str(e)}")

    @staticmethod
    def parse_patient(patient_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            return {
                "id": patient_data["id"],
                "first_name": patient_data.get("name", [{}])[0].get("given", [""])[0],
                "gender": patient_data.get("gender"),
                "birth_date": datetime.strptime(
                    patient_data.get("birthDate", "1900-01-01"), 
                    "%Y-%m-%d"
                ).date()
            }
        except (KeyError, IndexError) as e:
            raise Exception(f"Invalid patient data structure: {str(e)}")
        except ValueError as e:
            raise Exception(f"Invalid date format in patient data: {str(e)}")

    @staticmethod
    def parse_observation(observation_data):
        return {
            "id": observation_data.get("id"),
            "resource_type": observation_data.get("resourceType"),
            "status": observation_data.get("status")
        } 