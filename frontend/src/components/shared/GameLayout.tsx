import type { ReactNode } from "react";

interface GameLayoutProps {
  title: string;
  subtitle?: string; // Added optional subtitle
  onExit: () => void;
  showScore?: boolean; // Optional
  score?: number;      // Optional
  userId?: string | number;
  children: ReactNode;
}

export function GameLayout({
  title,
  subtitle,
  onExit,
  showScore = false, // Default false
  score = 0,         // Default 0
  userId,
  children,
}: GameLayoutProps) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-8">
      
      {/* Header */}
      <div className="max-w-4xl mx-auto mb-8 flex justify-between items-center">
        
        {/* Title Section */}
        <div>
          <h1 className="text-3xl font-bold text-gray-800">{title}</h1>
          {subtitle && (
            <p className="text-gray-600 mt-1 text-sm">{subtitle}</p>
          )}
        </div>

        {/* Controls Section */}
        <div className="flex gap-4 items-center">
          <div className="bg-white px-6 py-3 rounded-lg shadow-md">
            <span className="text-sm text-gray-600">User: </span>
            <span className="text-lg font-bold text-gray-800">
              {userId ?? 'Guest'}
            </span>
          </div>

          {showScore && (
            <div className="bg-white px-6 py-3 rounded-lg shadow-md">
              <span className="text-sm text-gray-600">Score: </span>
              <span className="text-2xl font-bold text-blue-600">{score}</span>
            </div>
          )}

          <button
            onClick={onExit}
            className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
          >
            Exit
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto bg-white rounded-xl shadow-lg p-8">
        {children}
      </div>
    </div>
  );
}