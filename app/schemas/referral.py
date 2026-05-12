from typing import Optional
from typing import List

from pydantic import BaseModel


class PatientInformation(BaseModel):
    patient_name: Optional[str] = None
    dob: Optional[str] = None
    gender: Optional[str] = None
    phone: Optional[str] = None


class ProviderInformation(BaseModel):
    provider_name: Optional[str] = None
    provider_phone: Optional[str] = None
    provider_fax: Optional[str] = None


class InsuranceInformation(BaseModel):
    insurance_name: Optional[str] = None
    member_id: Optional[str] = None


class ClinicalInformation(BaseModel):
    referral_reason: Optional[str] = None
    specialty: Optional[str] = None
    priority: Optional[str] = None
    diagnosis: Optional[str] = None
    icd_codes: List[str] = []
    cpt_codes: List[str] = []


class ValidationInformation(BaseModel):
    is_complete_referral: bool
    missing_fields: List[str]
    warnings: List[str]
    needs_human_review: bool


class ReferralExtractionSchema(BaseModel):
    is_referral_document: bool
    document_type: str

    patient_information: PatientInformation
    provider_information: ProviderInformation
    insurance_information: InsuranceInformation
    clinical_information: ClinicalInformation

    validation: ValidationInformation

    confidence_scores: dict