import { useState } from 'react';
import type { Category, Document } from './types';
import { uploadFiles } from './api/referralApi';
import { transformApiResponse } from './utils/helpers';
import Header from './components/Header';
import FolderUpload from './components/FolderUpload';
import CategoryCards from './components/CategoryCards';
import DocumentList from './components/DocumentList';
import DocumentDetail from './components/DocumentDetail';

function App() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<Category>('Referral');
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  const handleUpload = async (files: FileList) => {
    setIsUploading(true);
    setUploadProgress(0);

    try {
      const response = await uploadFiles(files, (progress) => {
        setUploadProgress(Math.min(progress, 50));
      });

      setUploadProgress(75);

      const newDocuments = transformApiResponse(response.results);

      setUploadProgress(100);
      setDocuments((prev) => [...prev, ...newDocuments]);

      // Auto-select category with most documents
      const referralCount = newDocuments.filter(d => d.category === 'Referral').length;
      const incompleteCount = newDocuments.filter(d => d.category === 'Incomplete').length;
      const notReferralCount = newDocuments.filter(d => d.category === 'Not Referral').length;

      if (incompleteCount > referralCount && incompleteCount > notReferralCount) {
        setSelectedCategory('Incomplete');
      } else if (notReferralCount > referralCount) {
        setSelectedCategory('Not Referral');
      } else {
        setSelectedCategory('Referral');
      }

    } catch (error) {
      console.error('Upload failed:', error);
      alert('Upload failed. Please check if the backend is running.');
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  const handleViewDocument = (doc: Document) => {
    setSelectedDocument(doc);
  };

  const handleCloseDetail = () => {
    setSelectedDocument(null);
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <Header
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        totalDocs={documents.length}
        isProcessing={isUploading}
      />

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {/* Upload Section */}
        <section>
          <FolderUpload
            onUpload={handleUpload}
            isUploading={isUploading}
            progress={uploadProgress}
          />
        </section>

        {/* Category Cards */}
        {documents.length > 0 && (
          <>
            <section>
              <h2 className="text-lg font-semibold text-gray-800 mb-4">Classification Results</h2>
              <CategoryCards
                documents={documents}
                selectedCategory={selectedCategory}
                onSelectCategory={setSelectedCategory}
              />
            </section>

            {/* Document List */}
            <section>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-800">
                  {selectedCategory} Documents
                </h2>
                <span className="text-sm text-gray-500">
                  {documents.filter(d => d.category === selectedCategory).length} items
                </span>
              </div>
              <DocumentList
                documents={documents}
                category={selectedCategory}
                onViewDocument={handleViewDocument}
                searchQuery={searchQuery}
              />
            </section>
          </>
        )}

        {/* Empty State */}
        {documents.length === 0 && !isUploading && (
          <div className="text-center py-12">
            <p className="text-gray-500 text-lg">
              Upload a folder or files to start processing referrals
            </p>
          </div>
        )}
      </main>

      {/* Document Detail Modal */}
      {selectedDocument && (
        <DocumentDetail
          document={selectedDocument}
          onClose={handleCloseDetail}
        />
      )}
    </div>
  );
}

export default App;
