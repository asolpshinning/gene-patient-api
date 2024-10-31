import time
import traceback
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from . import models, database
from .services.fhir_service import FHIRService
from sqlalchemy import or_
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from contextlib import asynccontextmanager
from fastapi.security import OAuth2PasswordRequestForm
from .auth import authenticate_user, create_access_token, get_current_user
from datetime import timedelta
from fastapi import status

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        async with database.engine.begin() as conn:
            await conn.run_sync(models.Base.metadata.create_all)
    except SQLAlchemyError as e:
        print(f"Failed to create database tables: {str(e)}")
        raise
    yield
    # Shutdown
    pass

app = FastAPI(lifespan=lifespan)

# Function to wait for the database to be ready and create tables
def wait_for_db(max_retries=5, retry_interval=5):
    for i in range(max_retries):
        try:
            # Try to create tables
            models.Base.metadata.create_all(bind=database.engine)
            return
        except OperationalError as e:
            if i == max_retries - 1:  # Last retry
                raise e
            print(f"Database not ready, waiting {retry_interval} seconds... (Attempt {i+1}/{max_retries})")
            time.sleep(retry_interval)

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": user["username"]},
        expires_delta=timedelta(minutes=30)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/populate/{postal_code}")
async def populate_data(
    postal_code: str,
    db: AsyncSession = Depends(database.get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        fhir_service = FHIRService()
        
        # Get patients by postal code
        patients_data = await fhir_service.get_patients_by_postal_code(postal_code)
        
        if not patients_data.get("entry"):
            raise HTTPException(
                status_code=404,
                detail=f"No patients found for postal code {postal_code}"
            )

        for entry in patients_data.get("entry", []):
            try:
                patient_data = entry.get("resource", {})
                patient_dict = await fhir_service.parse_patient(patient_data)
                patient_dict["postal_code"] = postal_code
                
                # Check if patient exists
                query = select(models.Patient).filter(models.Patient.id == patient_dict["id"])
                result = await db.execute(query)
                existing_patient = result.scalar_one_or_none()
                
                if existing_patient:
                    # Update existing patient
                    for key, value in patient_dict.items():
                        setattr(existing_patient, key, value)
                else:
                    # Create new patient
                    patient = models.Patient(**patient_dict)
                    db.add(patient)
                
                # Get and create observations
                observations_data = await fhir_service.get_observations_by_patient_id(patient_dict["id"])
                if observations_data.get("entry"):
                    first_observation = observations_data["entry"][0]["resource"]
                    observation_dict = await fhir_service.parse_observation(first_observation)
                    observation_dict["patient_id"] = patient_dict["id"]
                    
                    # Check if observation exists
                    query = select(models.Observation).filter(
                        models.Observation.id == observation_dict["id"]
                    )
                    result = await db.execute(query)
                    existing_observation = result.scalar_one_or_none()
                    
                    if existing_observation:
                        for key, value in observation_dict.items():
                            setattr(existing_observation, key, value)
                    else:
                        observation = models.Observation(**observation_dict)
                        db.add(observation)
            
            except Exception as e:
                print(f"Error processing patient: {str(e)}")
                continue
        
        try:
            await db.commit()
        except SQLAlchemyError as e:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Database error while saving data: {str(e)}"
            )
            
        return {"message": "Data populated successfully"}
        
    except HTTPException as he:
        await db.rollback()
        raise he
    except Exception as e:
        print(f"Error in populate_data: {str(e)}")
        print("Traceback:")
        print(traceback.format_exc())
        
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error: {str(e)}"
        )

@app.get("/patients/{search_term}")
async def get_patient(search_term: str, db: AsyncSession = Depends(database.get_db)):
    try:
        # Using select() from sqlalchemy.future
        query = select(models.Patient).filter(
            or_(
                models.Patient.id == search_term,
                models.Patient.first_name == search_term
            )
        )
        result = await db.execute(query)
        patient = result.scalar_one_or_none()
        
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
async def get_patient_observations(patient_id: str, db: AsyncSession = Depends(database.get_db)):
    try:
        query = select(models.Observation).filter(
            models.Observation.patient_id == patient_id
        )
        result = await db.execute(query)
        observations = result.scalars().all()
        
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

@app.get("/patients/postal_code/{postal_code}")
async def get_patients_by_postal_code(postal_code: str, db: AsyncSession = Depends(database.get_db)):
    try:
        query = select(models.Patient.id).filter(
            models.Patient.postal_code == postal_code
        )
        result = await db.execute(query)
        patient_ids = result.scalars().all()
        
        if not patient_ids:
            raise HTTPException(
                status_code=404,
                detail=f"No patients found for postal code: {postal_code}"
            )
            
        return {"patient_ids": patient_ids}
        
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )

@app.get("/")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "database": "connected" if database.engine else "disconnected",
        "timestamp": datetime.utcnow().isoformat()
    }