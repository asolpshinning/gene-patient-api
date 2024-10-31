from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class Patient(Base):
    __tablename__ = "patients"

    id = Column(String, primary_key=True)
    first_name = Column(String)
    gender = Column(String)
    birth_date = Column(Date)
    postal_code = Column(String)
    observations = relationship("Observation", back_populates="patient")

class Observation(Base):
    __tablename__ = "observations"

    id = Column(String, primary_key=True)
    resource_type = Column(String)
    status = Column(String)
    patient_id = Column(String, ForeignKey("patients.id"))
    patient = relationship("Patient", back_populates="observations") 