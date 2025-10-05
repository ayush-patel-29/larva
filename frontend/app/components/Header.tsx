'use client';

import { Brain, RefreshCw, Settings, HelpCircle } from 'lucide-react';

interface HeaderProps {
  totalArticles: number;
  lastUpdated?: string;
}

export function Header({ totalArticles, lastUpdated }: HeaderProps) {
  return (
    <header className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <Brain className="h-8 w-8 text-blue-600" />
            <div>
              <h1 className="text-xl font-bold text-gray-900">
                NASA Bioscience Analytics
              </h1>
              <p className="text-sm text-gray-600">
                AI-Powered Knowledge Graph Dashboard
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <div className="text-right">
            <p className="text-sm font-medium text-gray-900">
              {totalArticles.toLocaleString()} Articles
            </p>
            {lastUpdated && (
              <p className="text-xs text-gray-500">
                Updated: {new Date(lastUpdated).toLocaleDateString()}
              </p>
            )}
          </div>

          <div className="flex items-center space-x-2">
            <button className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">
              <RefreshCw className="h-5 w-5" />
            </button>
            <button className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">
              <Settings className="h-5 w-5" />
            </button>
            <button className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">
              <HelpCircle className="h-5 w-5" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
