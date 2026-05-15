import { X, User, Stethoscope, FileText, AlertTriangle, CheckCircle, Shield, Activity } from 'lucide-react';
import type { Document } from '../types';
import { getConfidenceColor, getConfidenceBgColor, getCategoryIcon } from '../utils/helpers';

interface DocumentDetailProps {
  document: Document;
  onClose: () => void;
}

export default function DocumentDetail({ document, onClose }: DocumentDetailProps) {
  const data = document.data;
  const patient = data?.patient_information;
  const provider = data?.provider_information;
  const insurance = data?.insurance_information;
  const clinical = data?.clinical_information;
  const validation = data?.validation;
  const confidence = data?.confidence_scores;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="bg-gray-50 px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <FileText className="w-6 h-6 text-gray-600" />
            <div>
              <h2 className="text-lg font-semibold text-gray-900">{document.filename}</h2>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-sm">{getCategoryIcon(document.category)}</span>
                <span className="text-sm text-gray-600">{document.category}</span>
                {data?.document_type && (
                  <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-gray-200 text-gray-700">
                    {data.document_type}
                  </span>
                )}
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getConfidenceColor(document.confidence)}`}>
                  {document.confidence}% confidence
                </span>
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-200 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-80px)]">
          {/* Confidence Scores */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-700">Overall Confidence</span>
              <span className={`text-sm font-bold ${document.confidence >= 90 ? 'text-green-600' : document.confidence >= 70 ? 'text-yellow-600' : 'text-red-600'}`}>
                {document.confidence}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-3">
              <div
                className={`h-3 rounded-full transition-all ${getConfidenceBgColor(document.confidence)}`}
                style={{ width: `${document.confidence}%` }}
              />
            </div>
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <span>🔴 Manual Review</span>
              <span>🟡 Review</span>
              <span>🟢 Auto Approve</span>
            </div>
            
            {/* Individual Confidence Scores */}
            {confidence && Object.keys(confidence).length > 1 && (
              <div className="mt-4 grid grid-cols-3 gap-2">
                {Object.entries(confidence).map(([key, value]) => {
                  if (key === 'overall' || typeof value !== 'number') return null;
                  return (
                    <div key={key} className="bg-gray-50 p-2 rounded-lg text-center">
                      <p className="text-xs text-gray-500 capitalize">{key.replace(/_/g, ' ')}</p>
                      <p className={`text-sm font-bold ${value >= 90 ? 'text-green-600' : value >= 70 ? 'text-yellow-600' : 'text-red-600'}`}>
                        {value}%
                      </p>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Issues */}
          {document.issues.length > 0 && (
            <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-xl">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className="w-5 h-5 text-yellow-600" />
                <span className="font-medium text-yellow-800">Issues Found ({document.issues.length})</span>
              </div>
              <ul className="space-y-1">
                {document.issues.map((issue, idx) => (
                  <li key={idx} className="text-sm text-yellow-700 flex items-center gap-2">
                    <span className="w-1.5 h-1.5 bg-yellow-500 rounded-full" />
                    {issue}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {data ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Patient Info */}
              <div className="bg-blue-50 p-4 rounded-xl border border-blue-100">
                <div className="flex items-center gap-2 mb-3">
                  <User className="w-5 h-5 text-blue-600" />
                  <h3 className="font-semibold text-blue-900">Patient Information</h3>
                </div>
                <div className="space-y-2 text-sm">
                  <InfoRow label="Name" value={patient?.patient_name} />
                  <InfoRow label="DOB" value={patient?.dob} />
                  <InfoRow label="Gender" value={patient?.gender} />
                  <InfoRow label="Phone" value={patient?.phone} />
                </div>
              </div>

              {/* Insurance */}
              <div className="bg-purple-50 p-4 rounded-xl border border-purple-100">
                <div className="flex items-center gap-2 mb-3">
                  <Shield className="w-5 h-5 text-purple-600" />
                  <h3 className="font-semibold text-purple-900">Insurance</h3>
                </div>
                <div className="space-y-2 text-sm">
                  <InfoRow label="Insurance" value={insurance?.insurance_name} />
                  <InfoRow label="Member ID" value={insurance?.member_id} />
                </div>
              </div>

              {/* Provider Info */}
              <div className="bg-green-50 p-4 rounded-xl border border-green-100">
                <div className="flex items-center gap-2 mb-3">
                  <Stethoscope className="w-5 h-5 text-green-600" />
                  <h3 className="font-semibold text-green-900">Provider Information</h3>
                </div>
                <div className="space-y-2 text-sm">
                  <InfoRow label="Provider" value={provider?.provider_name} />
                  <InfoRow label="Phone" value={provider?.provider_phone} />
                  <InfoRow label="Fax" value={provider?.provider_fax} />
                </div>
              </div>

              {/* Clinical Info - Specialty */}
              <div className="bg-orange-50 p-4 rounded-xl border border-orange-100">
                <div className="flex items-center gap-2 mb-3">
                  <Activity className="w-5 h-5 text-orange-600" />
                  <h3 className="font-semibold text-orange-900">Referral Details</h3>
                </div>
                <div className="space-y-2 text-sm">
                  <InfoRow label="Specialty" value={clinical?.specialty} />
                  <InfoRow label="Priority" value={clinical?.priority} />
                  <InfoRow label="Urgent" value={clinical?.is_urgent ? '🔴 Yes' : 'No'} />
                </div>
              </div>

              {/* Clinical Info - Full */}
              <div className="md:col-span-2 bg-gray-50 p-4 rounded-xl border border-gray-200">
                <div className="flex items-center gap-2 mb-3">
                  <FileText className="w-5 h-5 text-gray-600" />
                  <h3 className="font-semibold text-gray-900">Clinical Information</h3>
                </div>
                <div className="space-y-2 text-sm">
                  <InfoRow label="Diagnosis" value={clinical?.diagnosis} />
                  <InfoRow label="ICD Codes" value={clinical?.icd_codes?.join(', ')} />
                  <InfoRow label="CPT Codes" value={clinical?.cpt_codes?.join(', ')} />
                  <div className="pt-2 border-t border-gray-200 mt-2">
                    <p className="text-gray-500 mb-1">Reason for Referral:</p>
                    <p className="text-gray-900">{clinical?.referral_reason || '—'}</p>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              <AlertTriangle className="w-12 h-12 mx-auto mb-4 text-gray-300" />
              <p>No data extracted from this document</p>
              {document.error && (
                <p className="text-red-500 mt-2 text-sm">{document.error}</p>
              )}
            </div>
          )}

          {/* Validation Status */}
          {validation && (
            <div className={`mt-6 p-4 rounded-xl border ${validation.is_complete_referral ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {validation.is_complete_referral ? (
                    <CheckCircle className="w-5 h-5 text-green-600" />
                  ) : (
                    <AlertTriangle className="w-5 h-5 text-red-600" />
                  )}
                  <span className={`font-medium ${validation.is_complete_referral ? 'text-green-800' : 'text-red-800'}`}>
                    {validation.is_complete_referral ? 'Complete Referral' : 'Incomplete Referral'}
                  </span>
                </div>
                {validation.needs_human_review && (
                  <span className="px-2 py-1 bg-yellow-100 text-yellow-800 text-xs font-medium rounded-full">
                    Needs Human Review
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string | undefined }) {
  return (
    <div className="flex">
      <span className="text-gray-500 w-24 flex-shrink-0">{label}:</span>
      <span className="text-gray-900 font-medium">{value || '—'}</span>
    </div>
  );
}
