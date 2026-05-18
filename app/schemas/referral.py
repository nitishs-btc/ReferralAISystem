"""Pydantic models shared across OCR, classification, extraction, validation, and API responses."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DocumentState(str, Enum):
    VALID_REFERRAL = "VALID_REFERRAL"
    INCOMPLETE_REFERRAL = "INCOMPLETE_REFERRAL"
    SELF_REFERRAL = "SELF_REFERRAL"
    NON_REFERRAL_MEDICAL = "NON_REFERRAL_MEDICAL"
    NON_MEDICAL_DOCUMENT = "NON_MEDICAL_DOCUMENT"
    LOW_CONFIDENCE_REFERRAL = "LOW_CONFIDENCE_REFERRAL"
    BLANK_DOCUMENT = "BLANK_DOCUMENT"
    CORRUPTED_DOCUMENT = "CORRUPTED_DOCUMENT"


class DocumentCategory(str, Enum):
    REFERRAL = "Referral"
    MEDICAL_SUPPORTING_DOCUMENT = "Medical Supporting Document"
    NON_MEDICAL = "Non Medical Document"
    UNKNOWN = "Unknown"


class ReferralType(str, Enum):
    PROVIDER_REFERRAL = "PROVIDER_REFERRAL"
    SELF_REFERRAL = "SELF_REFERRAL"
    UNKNOWN = "UNKNOWN"


class ReviewPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class FileMetadata(BaseModel):
    filename: str
    source_filename: str
    content_type: str | None = None
    file_extension: str
    file_size_bytes: int
    is_archive_member: bool = False


class OCRQualityMetrics(BaseModel):
    average_confidence: float = 0.0
    text_density: float = 0.0
    blank_page_ratio: float = 0.0
    poor_quality: bool = False


class OCRResult(BaseModel):
    raw_text: str = ""
    markdown: str = ""
    total_pages: int = 0
    average_confidence: float = 0.0
    quality: OCRQualityMetrics = Field(default_factory=OCRQualityMetrics)
    blank_document: bool = False
    corrupted_document: bool = False


class ClassificationEvidence(BaseModel):
    rule_score: float = 0.0
    llm_score: float = 0.0
    layout_score: float = 0.0
    ocr_score: float = 0.0
    passed_rule_threshold: bool = False
    passed_llm_threshold: bool = False
    agreement_score: float = 0.0
    agreement_within_threshold: bool = False
    positive_signals: list[str] = Field(default_factory=list)
    negative_signals: list[str] = Field(default_factory=list)
    explanation: str = ""


class ClassificationResult(BaseModel):
    document_state: DocumentState = DocumentState.LOW_CONFIDENCE_REFERRAL
    document_type: str = "Unknown"
    document_category: DocumentCategory = DocumentCategory.UNKNOWN
    referral_type: ReferralType = ReferralType.UNKNOWN
    is_referral_candidate: bool = False
    confidence: float = 0.0
    evidence: ClassificationEvidence = Field(default_factory=ClassificationEvidence)
    llm_available: bool = True


class PatientInformation(BaseModel):
    patient_name: str | None = None
    dob: str | None = None
    gender: str | None = None
    phone: str | None = None


class ProviderInformation(BaseModel):
    provider_name: str | None = None
    provider_phone: str | None = None
    provider_fax: str | None = None


class InsuranceInformation(BaseModel):
    insurance_name: str | None = None
    member_id: str | None = None


class ClinicalInformation(BaseModel):
    referral_reason: str | None = None
    specialty: str | None = None
    priority: str | None = None
    is_urgent: bool = False
    diagnosis: str | None = None
    icd_codes: list[str] = Field(default_factory=list)
    cpt_codes: list[str] = Field(default_factory=list)


class ValidationInformation(BaseModel):
    is_complete_referral: bool = False
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    needs_human_review: bool = False
    validation_confidence: float = 0.0
    completeness_score: float = 0.0
    required_fields_count: int = 0
    found_required_fields_count: int = 0
    applied_rule_profile: str = "non_referral"


class ExtractedReferralData(BaseModel):
    is_referral_document: bool = False
    document_type: str = "Unknown"
    document_category: str = DocumentCategory.UNKNOWN.value
    referral_type: str = ReferralType.UNKNOWN.value
    patient_information: PatientInformation = Field(default_factory=PatientInformation)
    provider_information: ProviderInformation = Field(default_factory=ProviderInformation)
    insurance_information: InsuranceInformation = Field(default_factory=InsuranceInformation)
    clinical_information: ClinicalInformation = Field(default_factory=ClinicalInformation)
    validation: ValidationInformation = Field(default_factory=ValidationInformation)
    confidence_scores: dict[str, float] = Field(default_factory=dict)


class ApiReferralData(BaseModel):
    # This schema mirrors the legacy dashboard payload while carrying extra sections for new features.
    is_referral_document: bool = False
    document_type: str = "Unknown"
    document_state: str = DocumentState.LOW_CONFIDENCE_REFERRAL.value
    document_category: str = DocumentCategory.UNKNOWN.value
    referral_type: str = ReferralType.UNKNOWN.value
    patient_information: PatientInformation = Field(default_factory=PatientInformation)
    provider_information: ProviderInformation = Field(default_factory=ProviderInformation)
    insurance_information: InsuranceInformation = Field(default_factory=InsuranceInformation)
    clinical_information: ClinicalInformation = Field(default_factory=ClinicalInformation)
    validation: ValidationInformation = Field(default_factory=ValidationInformation)
    confidence_scores: dict[str, float] = Field(default_factory=dict)
    classification: dict[str, Any] = Field(default_factory=dict)
    ocr: dict[str, Any] = Field(default_factory=dict)
    review: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConfidenceFusionResult(BaseModel):
    final_confidence_score: float = 0.0
    component_scores: dict[str, float] = Field(default_factory=dict)
    classifier_disagreement: float = 0.0
    needs_human_review: bool = False


class ReviewRoutingResult(BaseModel):
    needs_human_review: bool = False
    priority: ReviewPriority = ReviewPriority.LOW
    queue: str = "straight_through"
    reasons: list[str] = Field(default_factory=list)


class ProcessingTimings(BaseModel):
    intake_ms: float = 0.0
    ocr_ms: float = 0.0
    classification_ms: float = 0.0
    extraction_ms: float = 0.0
    validation_ms: float = 0.0
    fusion_ms: float = 0.0
    review_ms: float = 0.0
    total_ms: float = 0.0


class DocumentAnalysisResult(BaseModel):
    document_id: str
    status: str
    file: FileMetadata
    total_pages: int = 0
    document_state: DocumentState = DocumentState.LOW_CONFIDENCE_REFERRAL
    document_type: str = "Unknown"
    document_category: str = DocumentCategory.UNKNOWN.value
    referral_type: str = ReferralType.UNKNOWN.value
    ocr: OCRResult = Field(default_factory=OCRResult)
    classification: ClassificationResult = Field(default_factory=ClassificationResult)
    extracted_data: ExtractedReferralData = Field(default_factory=ExtractedReferralData)
    validation: ValidationInformation = Field(default_factory=ValidationInformation)
    confidence: ConfidenceFusionResult = Field(default_factory=ConfidenceFusionResult)
    review: ReviewRoutingResult = Field(default_factory=ReviewRoutingResult)
    timings: ProcessingTimings = Field(default_factory=ProcessingTimings)
    errors: list[str] = Field(default_factory=list)
    audit: dict[str, Any] = Field(default_factory=dict)


class BatchSummary(BaseModel):
    total_files: int
    successful: int
    failed: int
    human_review_required: int = 0


class BatchFileResult(BaseModel):
    filename: str
    status: str
    data: ApiReferralData | None = None
    error: str | None = None
    analysis: dict[str, Any] | None = None


class BatchProcessingResult(BaseModel):
    summary: BatchSummary
    results: list[BatchFileResult]


ReferralExtractionSchema = ExtractedReferralData
