import requests
from datetime import datetime
from requests.exceptions import HTTPError, ConnectionError, Timeout, JSONDecodeError
from typing import Dict, Any, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class FHIRService:
    BASE_URL = "https://hapi.fhir.org/baseR5"

    def __init__(self):
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,  # number of retries
            backoff_factor=1,  # wait 1, 2, 4 seconds between retries
            status_forcelist=[500, 502, 503, 504]  # HTTP status codes to retry on
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def get_patients_by_postal_code(self, postal_code: str) -> Dict[str, Any]:
        try:
            response = self.session.get(
                f"{self.BASE_URL}/Patient?address-postalcode={postal_code}",
                timeout=30  # increased timeout to 30 seconds
            )
            response.raise_for_status()
            return response.json()
        except Timeout:
            raise Exception("FHIR server request timed out after 30 seconds")
        except ConnectionError:
            raise Exception("Failed to connect to FHIR server. Please check your network connection")
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