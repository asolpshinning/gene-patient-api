from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from . import models, database
from .services.fhir_service import FHIRService
from sqlalchemy import or_

app = FastAPI()

# Create tables
try:
    models.Base.metadata.create_all(bind=database.engine)
except SQLAlchemyError as e:
    print(f"Failed to create database tables: {str(e)}")
    raise

@app.post("/populate/{postal_code}")
async def populate_data(postal_code: str, db: Session = Depends(database.get_db)):
    try:
        fhir_service = FHIRService()
        
        # Get patients by postal code
        patients_data = fhir_service.get_patients_by_postal_code(postal_code)
        
        if not patients_data.get("entry"):
            raise HTTPException(
                status_code=404,
                detail=f"No patients found for postal code {postal_code}"
            )

        for entry in patients_data.get("entry", []):
            try:
                patient_data = entry.get("resource", {})
                patient_dict = fhir_service.parse_patient(patient_data)
                
                # Create patient
                patient = models.Patient(**patient_dict)
                db.merge(patient)
                
                # Get and create observations
                observations_data = fhir_service.get_observations_by_patient_id(patient.id)
                if observations_data.get("entry"):
                    first_observation = observations_data["entry"][0]["resource"]
                    observation_dict = fhir_service.parse_observation(first_observation)
                    observation_dict["patient_id"] = patient.id
                    
                    observation = models.Observation(**observation_dict)
                    db.merge(observation)
            
            except Exception as e:
                # Log the error but continue processing other patients
                print(f"Error processing patient: {str(e)}")
                continue
        
        try:
            db.commit()
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Database error while saving data: {str(e)}"
            )
            
        return {"message": "Data populated successfully"}
        
    except Exception as e:
        # Ensure database session is rolled back
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.get("/patients/{search_term}")
async def get_patient(search_term: str, db: Session = Depends(database.get_db)):
    try:
        patient = db.query(models.Patient).filter(
            or_(
                models.Patient.id == search_term,
                models.Patient.first_name == search_term
            )
        ).first()
        
        if not patient:
            raise HTTPException(
                status_code=404,
                detail=f"Patient not found with ID or name: {search_term}"
            )
        return patient
        
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )

@app.get("/patients/{patient_id}/observations")
async def get_patient_observations(patient_id: str, db: Session = Depends(database.get_db)):
    try:
        observations = db.query(models.Observation).filter(
            models.Observation.patient_id == patient_id
        ).all()
        
        if not observations:
            raise HTTPException(
                status_code=404,
                detail=f"No observations found for patient ID: {patient_id}"
            )
        return observations
        
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )