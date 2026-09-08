from typing import Optional
from pydantic import BaseModel


class ApplicationCreate(BaseModel):
    farmer_name: str
    mobile: str
    service_type: str
    survey_number: str
    village: str


class ApplicationResponse(BaseModel):
    application_id: str
    farmer_name: str
    mobile: str
    service_type: str
    survey_number: str
    village: str
    status: str
    verification_score: float
    decision: str
    government_application_id: Optional[str] = None

    class Config:
        orm_mode = True
