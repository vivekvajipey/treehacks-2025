import React from 'react';
import { Brain } from 'lucide-react';

interface RuminateButtonProps {
  isRuminating: boolean;
  error?: string | null;
  status?: 'pending' | 'complete' | 'error';
  onRuminate: () => void;
}

export default function RuminateButton({ isRuminating, error, status, onRuminate }: RuminateButtonProps) {
  const getButtonText = () => {
    if (error) return 'Error';
    if (status === 'complete') return 'Rumination Complete';
    if (isRuminating) return 'Ruminating...';
    return 'Ruminate';
  };

  const getButtonStyle = () => {
    if (error) return 'bg-red-600 hover:bg-red-700';
    if (status === 'complete') return 'bg-green-600 hover:bg-green-700';
    if (isRuminating) return 'bg-primary-400 cursor-not-allowed';
    return 'bg-primary-600 hover:bg-primary-700 hover:shadow-md';
  };

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={onRuminate}
        disabled={isRuminating || status === 'complete'}
        className={`
          px-4 py-2 rounded-lg text-white
          flex items-center gap-2
          transition-all duration-200
          ${getButtonStyle()}
        `}
      >
        <Brain className={`w-5 h-5 ${isRuminating ? 'animate-pulse' : ''}`} />
        <span>{getButtonText()}</span>
      </button>
      {error && (
        <span className="text-red-600 text-sm">{error}</span>
      )}
    </div>
  );
} 