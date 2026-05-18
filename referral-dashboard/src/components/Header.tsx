// Dashboard header with search input and live processing status indicator.

import { Search, Activity } from 'lucide-react';

interface HeaderProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  totalDocs: number;
  isProcessing: boolean;
}

export default function Header({ searchQuery, onSearchChange, totalDocs, isProcessing }: HeaderProps) {
  return (
    <header className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center">
            <Activity className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">Referral Intake Dashboard</h1>
            <p className="text-sm text-gray-500">AI-Powered Document Classification</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Search */}
          <div className="relative">
            <Search className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search patient, provider..."
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              className="pl-10 pr-4 py-2 w-64 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Status */}
          <div className="flex items-center gap-2 px-4 py-2 bg-gray-100 rounded-lg">
            <div className={`w-2 h-2 rounded-full ${isProcessing ? 'bg-yellow-500 animate-pulse' : 'bg-green-500'}`} />
            <span className="text-sm text-gray-600">
              {isProcessing ? 'Processing...' : `${totalDocs} Documents`}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}
