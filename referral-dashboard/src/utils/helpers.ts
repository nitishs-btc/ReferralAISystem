// UI helper functions for confidence styling, categorization, and API response normalization.

import type { Category, ConfidenceLevel, Document, DocumentState, ApiDocument, ReferralData } from '../types';

export const getConfidenceLevel = (confidence: number): ConfidenceLevel => {
  if (confidence >= 90) return 'high';
  if (confidence >= 70) return 'medium';
  return 'low';
};

export const getConfidenceColor = (confidence: number): string => {
  if (confidence >= 90) return 'text-green-600 bg-green-100';
  if (confidence >= 70) return 'text-yellow-600 bg-yellow-100';
  return 'text-red-600 bg-red-100';
};

export const getConfidenceBgColor = (confidence: number): string => {
  if (confidence >= 90) return 'bg-green-500';
  if (confidence >= 70) return 'bg-yellow-500';
  return 'bg-red-500';
};

export const getCategoryColor = (category: Category): string => {
  switch (category) {
    case 'Referral':
      return 'text-green-700 bg-green-100 border-green-300';
    case 'Incomplete':
      return 'text-yellow-700 bg-yellow-100 border-yellow-300';
    case 'Not Referral':
      return 'text-red-700 bg-red-100 border-red-300';
  }
};

export const getCategoryIcon = (category: Category): string => {
  switch (category) {
    case 'Referral':
      return '✅';
    case 'Incomplete':
      return '⚠️';
    case 'Not Referral':
      return '❌';
  }
};

const STATE_TO_CATEGORY: Record<string, Category> = {
  VALID_REFERRAL:          'Referral',
  REFERRAL:                'Referral',
  INCOMPLETE_REFERRAL:     'Incomplete',
  SELF_REFERRAL:           'Incomplete',
  LOW_CONFIDENCE_REFERRAL: 'Incomplete',
  NON_REFERRAL_MEDICAL:    'Not Referral',
  NON_MEDICAL_DOCUMENT:    'Not Referral',
  BLANK_DOCUMENT:          'Not Referral',
  CORRUPTED_DOCUMENT:      'Not Referral',
};

export const classifyDocument = (data: ReferralData | null, status: string): { category: Category; confidence: number; issues: string[] } => {
  if (status === 'error' || !data) {
    return { category: 'Not Referral', confidence: 0, issues: ['Processing failed'] };
  }

  // Non-referrals are surfaced immediately so operators can ignore them or route them elsewhere.
  if (!data.is_referral_document) {
    return { 
      category: 'Not Referral', 
      confidence: data.confidence_scores?.overall || 0, 
      issues: ['Not a referral document'] 
    };
  }

  const issues: string[] = [];
  
  // Get confidence from backend
  let confidence = data.confidence_scores?.overall || 0;
  
  // If no overall confidence, calculate from components
  if (!confidence && data.confidence_scores) {
    const scores = Object.values(data.confidence_scores).filter((v): v is number => typeof v === 'number');
    if (scores.length > 0) {
      confidence = Math.round(scores.reduce((a, b) => a + b, 0) / scores.length);
    }
  }

  // Add validation issues from backend
  if (data.validation) {
    if (data.validation.missing_fields && data.validation.missing_fields.length > 0) {
      issues.push(...data.validation.missing_fields.map(f => `Missing: ${f}`));
    }
    if (data.validation.warnings && data.validation.warnings.length > 0) {
      issues.push(...data.validation.warnings);
    }
  }

  if (data.review?.reasons && data.review.reasons.length > 0) {
    issues.push(...data.review.reasons);
  }

  // The dashboard keeps a simple 3-state view even though the backend has more detailed document states.
const category: Category = data.document_state
    ? (STATE_TO_CATEGORY[data.document_state] ?? 'Not Referral')
    : data.validation?.is_complete_referral && issues.length === 0
      ? 'Referral'
      : data.is_referral_document
        ? 'Incomplete'
        : 'Not Referral';

  // Override if needs human review
  if ((data.review?.needs_human_review || data.validation?.needs_human_review) && category === 'Referral') {
    issues.push('Needs human review');
  }

  return { category, confidence, issues: [...new Set(issues)] };
};

export const transformApiResponse = (results: ApiDocument[]): Document[] => {
  // Convert backend batch results into the view model consumed by table/cards/detail components.
  return results.map((result, index) => {
    const { category, confidence, issues } = classifyDocument(result.data, result.status);

    return {
      id: `doc-${index}-${Date.now()}`,
      filename: result.filename,
      category,
      confidence,
      status: result.status === 'success' ? 'completed' : 'error',
      issues,
      data: result.data,
      error: result.error || undefined,
    };
  });
};

export const formatDate = (date: string): string => {
  if (!date) return '—';
  try {
    return new Date(date).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return date;
  }
};

export const getPatientName = (data: ReferralData | null): string => {
  return data?.patient_information?.patient_name || '—';
};

export const getProviderName = (data: ReferralData | null): string => {
  return data?.provider_information?.provider_name || '—';
};
