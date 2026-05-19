// Shared frontend types for the dashboard UI and the backend API payload it consumes.

export type Category = 'Referral' | 'Incomplete' | 'Non Referral';

export type ConfidenceLevel = 'high' | 'medium' | 'low';

export type DocumentState =
  | 'VALID_REFERRAL'
  | 'REFERRAL'
  | 'INCOMPLETE_REFERRAL'
  | 'SELF_REFERRAL'
  | 'LOW_CONFIDENCE_REFERRAL'
  | 'NON_REFERRAL_MEDICAL'
  | 'NON_MEDICAL_DOCUMENT'
  | 'BLANK_DOCUMENT'
  | 'CORRUPTED_DOCUMENT';

export interface Document {
  id: string;
  filename: string;
  category: Category;
  confidence: number;
  status: 'processing' | 'completed' | 'error';
  issues: string[];
  data: ReferralData | null;
  error?: string;
}

export interface PatientInformation {
  patient_name?: string;
  dob?: string;
  gender?: string;
  phone?: string;
}

export interface ProviderInformation {
  provider_name?: string;
  provider_phone?: string;
  provider_fax?: string;
}

export interface InsuranceInformation {
  insurance_name?: string;
  member_id?: string;
}

export interface ClinicalInformation {
  referral_reason?: string;
  specialty?: string;
  priority?: string;
  is_urgent?: boolean;
  diagnosis?: string;
  icd_codes?: string[];
  cpt_codes?: string[];
}

export interface ValidationInformation {
  is_complete_referral: boolean;
  missing_fields: string[];
  warnings: string[];
  needs_human_review: boolean;
}

export interface ConfidenceScores {
  overall?: number;
  rule?: number;
  llm?: number;
  classification?: number;
  ocr?: number;
  validation?: number;
  completeness?: number;
  classifier_agreement?: number;
  patient_info?: number;
  provider_info?: number;
  clinical_info?: number;
  [key: string]: number | undefined;
}

export interface ReferralData {
  // This mirrors the backend's dashboard-compatible response shape.
  is_referral_document: boolean;
  document_type: string;
  document_state: DocumentState;           // ← add this
  document_category: string;        // ← add this
  patient_information: PatientInformation;
  provider_information: ProviderInformation;
  insurance_information: InsuranceInformation;
  clinical_information: ClinicalInformation;
  validation: ValidationInformation;
  confidence_scores: ConfidenceScores;
}

export interface ApiResponse {
  summary: {
    total_files: number;
    successful: number;
    failed: number;
  };
  results: ApiDocument[];
}

export interface ApiDocument {
  filename: string;
  status: 'success' | 'error' | 'skipped';
  data: ReferralData | null;
  error: string | null;
}
