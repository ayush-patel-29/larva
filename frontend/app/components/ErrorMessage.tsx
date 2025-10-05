'use client';

import { AlertCircle, RefreshCw } from 'lucide-react';

interface ErrorMessageProps {
  message: string;
  onRetry: () => void;
}

export function ErrorMessage({ message, onRetry }: ErrorMessageProps) {
  return (
    <div className="flex flex-col items-center justify-center space-y-4 p-8">
      <div className="flex items-center space-x-2 text-red-600">
        <AlertCircle className="h-8 w-8" />
        <h2 className="text-xl font-semibold">Error Loading Dashboard</h2>
      </div>
      
      <p className="text-gray-600 text-center max-w-md">
        {message}
      </p>
      
      <button
        onClick={onRetry}
        className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
      >
        <RefreshCw className="h-4 w-4" />
        <span>Try Again</span>
      </button>
    </div>
  );
}
