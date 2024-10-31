import httpx
from datetime import datetime
from typing import Dict, Any, Optional
from urllib3.util.retry import Retry
import asyncio

class FHIRService:
    BASE_URL = "https://hapi.fhir.org/baseR5"

    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        # Configure retry strategy
        self.retry_config = {
            "limits": 3,  # number of retries
            "backoff_factor": 1,  # wait 1, 2, 4 seconds between retries
            "status_codes": [500, 502, 503, 504]  # HTTP status codes to retry on
        }
        self.timeout = httpx.Timeout(30.0, connect=10.0)  # 30s timeout, 10s connect timeout
        self.client = client

    async def get_patients_by_postal_code(self, postal_code: str) -> Dict[str, Any]:
        """
        Asynchronously fetch patients by postal code from FHIR server
        """
        if self.client is None:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                return await self._get_patients(client, postal_code)
        else:
            return await self._get_patients(self.client, postal_code)

    async def _get_patients(self, client: httpx.AsyncClient, postal_code: str) -> Dict[str, Any]:
        try:
            response = await client.get(
                f"{self.BASE_URL}/Patient",
                params={"address-postalcode": postal_code}
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            raise Exception("FHIR server request timed out after 30 seconds")
        except httpx.ConnectError:
            raise Exception("Failed to connect to FHIR server. Please check your network connection")
        except httpx.HTTPStatusError as e:
            raise Exception(f"FHIR server returned an error: {e.response.status_code}")
        except httpx.HTTPError as e:
            raise Exception(f"HTTP error occurred: {str(e)}")
        except Exception as e:
            raise Exception(f"Unexpected error while fetching patients: {str(e)}")

    async def get_observations_by_patient_id(self, patient_id: str) -> Dict[str, Any]:
        """
        Asynchronously fetch observations for a specific patient
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/Observation",
                    params={"subject": f"Patient/{patient_id}"}
                )
                response.raise_for_status()
                return response.json()
            except httpx.TimeoutException:
                raise Exception("FHIR server request timed out")
            except httpx.ConnectError:
                raise Exception("Failed to connect to FHIR server")
            except httpx.HTTPStatusError as e:
                raise Exception(f"FHIR server returned an error: {e.response.status_code}")
            except httpx.HTTPError as e:
                raise Exception(f"HTTP error occurred: {str(e)}")
            except Exception as e:
                raise Exception(f"Unexpected error while fetching observations: {str(e)}")

    @staticmethod
    async def parse_patient(patient_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse patient data asynchronously
        Note: While this method is marked async for consistency,
        it doesn't perform any I/O operations
        """
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
    async def parse_observation(observation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse observation data asynchronously
        Note: While this method is marked async for consistency,
        it doesn't perform any I/O operations
        """
        return {
            "id": observation_data.get("id"),
            "resource_type": observation_data.get("resourceType"),
            "status": observation_data.get("status")
        }

    async def batch_get_observations(self, patient_ids: list[str]) -> Dict[str, Any]:
        """
        Method to fetch observations for multiple patients concurrently
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            tasks = []
            for patient_id in patient_ids:
                tasks.append(
                    client.get(
                        f"{self.BASE_URL}/Observation",
                        params={"subject": f"Patient/{patient_id}"}
                    )
                )
            
            # Gather all responses
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            results = {}
            for patient_id, response in zip(patient_ids, responses):
                if isinstance(response, Exception):
                    results[patient_id] = {"error": str(response)}
                else:
                    try:
                        response.raise_for_status()
                        results[patient_id] = response.json()
                    except Exception as e:
                        results[patient_id] = {"error": str(e)}
            
            return results