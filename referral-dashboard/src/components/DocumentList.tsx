// Tabular list for the currently selected document category in the dashboard.

import { Eye, FileText, AlertCircle } from 'lucide-react';
import type { Category, Document } from '../types';
import { getConfidenceColor, getConfidenceBgColor, getPatientName, getProviderName } from '../utils/helpers';

interface DocumentListProps {
  documents: Document[];
  category: Category;
  onViewDocument: (doc: Document) => void;
  searchQuery: string;
}

export default function DocumentList({ documents, category, onViewDocument, searchQuery }: DocumentListProps) {
  const filteredDocs = documents
    .filter((d) => d.category === category)
    .filter((d) => {
      // Search works across file name, patient name, and provider name for quick triage.
      if (searchQuery === '') return true;
      const query = searchQuery.toLowerCase();
      const patientName = getPatientName(d.data).toLowerCase();
      const providerName = getProviderName(d.data).toLowerCase();
      return (
        d.filename.toLowerCase().includes(query) ||
        patientName.includes(query) ||
        providerName.includes(query)
      );
    });

  if (filteredDocs.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
        <FileText className="w-12 h-12 mx-auto text-gray-300 mb-4" />
        <p className="text-gray-500 text-lg">No documents in this category</p>
        <p className="text-gray-400 text-sm mt-1">Upload files to get started</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <table className="w-full">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
              Document
            </th>
            <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
              Confidence
            </th>
            <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
              Issues
            </th>
            <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
              Status
            </th>
            <th className="px-6 py-4 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">
              Action
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {filteredDocs.map((doc) => (
            <tr key={doc.id} className="hover:bg-gray-50 transition-colors">
              <td className="px-6 py-4">
                <div className="flex items-center gap-3">
                  <FileText className="w-5 h-5 text-gray-400" />
                  <div>
                    <p className="font-medium text-gray-900 truncate max-w-xs">
                      {doc.filename}
                    </p>
                    {doc.data?.patient_information?.patient_name && (
                      <p className="text-sm text-gray-500">
                        Patient: {doc.data.patient_information.patient_name}
                      </p>
                    )}
                  </div>
                </div>
              </td>
              <td className="px-6 py-4">
                <div className="flex items-center gap-2">
                  <div className="w-24 bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${getConfidenceBgColor(doc.confidence)}`}
                      style={{ width: `${doc.confidence}%` }}
                    />
                  </div>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getConfidenceColor(doc.confidence)}`}>
                    {doc.confidence}%
                  </span>
                </div>
              </td>
              <td className="px-6 py-4">
                {doc.issues.length > 0 ? (
                  <div className="flex items-center gap-1">
                    <AlertCircle className="w-4 h-4 text-yellow-500" />
                    <span className="text-sm text-gray-600">
                      {doc.issues.length} issue{doc.issues.length > 1 ? 's' : ''}
                    </span>
                  </div>
                ) : (
                  <span className="text-sm text-green-600">✓ Complete</span>
                )}
              </td>
              <td className="px-6 py-4">
                <span className={`
                  px-2 py-1 rounded-full text-xs font-medium
                  ${doc.status === 'completed' ? 'bg-green-100 text-green-700' : ''}
                  ${doc.status === 'processing' ? 'bg-blue-100 text-blue-700' : ''}
                  ${doc.status === 'error' ? 'bg-red-100 text-red-700' : ''}
                `}>
                  {doc.status === 'completed' ? 'OK' : doc.status}
                </span>
              </td>
              <td className="px-6 py-4 text-right">
                <button
                  onClick={() => onViewDocument(doc)}
                  className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                  title="View Details"
                >
                  <Eye className="w-5 h-5" />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
