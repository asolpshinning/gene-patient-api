import requests
from datetime import datetime

class FHIRService:
    BASE_URL = "https://hapi.fhir.org/baseR5"

    @staticmethod
    def get_patients_by_postal_code(postal_code: str):
        response = requests.get(f"{FHIRService.BASE_URL}/Patient?address-postalcode={postal_code}")
        response.raise_for_status()
        return response.json()

    @staticmethod
    def get_observations_by_patient_id(patient_id: str):
        response = requests.get(f"{FHIRService.BASE_URL}/Observation?subject=Patient/{patient_id}")
        response.raise_for_status()
        return response.json()

    @staticmethod
    def parse_patient(patient_data):
        return {
            "id": patient_data.get("id"),
            "first_name": patient_data.get("name", [{}])[0].get("given", [""])[0],
            "gender": patient_data.get("gender"),
            "birth_date": datetime.strptime(patient_data.get("birthDate", "1900-01-01"), "%Y-%m-%d").date()
        }

    @staticmethod
    def parse_observation(observation_data):
        return {
            "id": observation_data.get("id"),
            "resource_type": observation_data.get("resourceType"),
            "status": observation_data.get("status")
        } 