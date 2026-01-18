from pydantic import BaseModel, HttpUrl, EmailStr, Field, validator
from typing import Optional, List

class LeadModel(BaseModel):
    id: Optional[str] = None
    business_name: str = Field(..., min_length=2)
    website_url: HttpUrl
    contact_email: Optional[EmailStr] = None
    rating: Optional[float] = Field(None, ge=0, le=5)
    city: str
    niche: str
    email_valid: bool = False
    email_type: str = "unknown"
    status: str = "scouted"
    email_subject: Optional[str] = None
    email_draft: Optional[str] = None
    analysis_thinking: Optional[str] = None
    review_context: Optional[str] = None
    sentiment_score: Optional[float] = Field(None, ge=-1, le=1)
    sentiment_label: Optional[str] = None
    sentiment_confidence: Optional[float] = Field(None, ge=0, le=1)
    key_emotions: Optional[List[str]] = None
    cluster_id: Optional[int] = Field(None, ge=0)

    @validator('business_name')
    def name_must_not_be_placeholder(cls, v):
        placeholders = ["pendiente", "n/a", "unknown", "unknown business", "negocio desconocido"]
        if v.lower() in placeholders:
            raise ValueError(f"Business name cannot be a placeholder: {v}")
        return v

    @validator('email_subject')
    def subject_must_not_be_placeholder(cls, v):
        if v and v.lower() in ["pendiente", "subject", "none"]:
            raise ValueError(f"Email subject cannot be a placeholder: {v}")
        return v
