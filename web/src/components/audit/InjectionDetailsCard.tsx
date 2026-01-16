import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { InjectionDetail } from '@/api/types';

interface InjectionDetailsCardProps {
  injections: InjectionDetail[];
}

export function InjectionDetailsCard({ injections }: InjectionDetailsCardProps) {
  if (!injections || injections.length === 0) return null;

  const getSeverityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical':
        return 'bg-red-600 text-white';
      case 'high':
        return 'bg-orange-600 text-white';
      case 'medium':
        return 'bg-yellow-600 text-white';
      case 'low':
        return 'bg-blue-600 text-white';
      default:
        return 'bg-gray-600 text-white';
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <svg
            className="h-5 w-5 text-orange-600"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
          Injection Attempts ({injections.length})
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {injections.map((injection, idx) => (
            <div
              key={idx}
              className="p-4 border rounded-lg bg-gray-50 dark:bg-gray-900/50"
            >
              <div className="flex items-center justify-between mb-3">
                <Badge variant="destructive" className="text-sm font-semibold">
                  {injection.injection_type.toUpperCase()}
                </Badge>
                <div className="flex items-center gap-2">
                  <Badge className={getSeverityColor(injection.severity)}>
                    {injection.severity}
                  </Badge>
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    Confidence: {(injection.confidence * 100).toFixed(1)}%
                  </span>
                </div>
              </div>

              {injection.matched_patterns && injection.matched_patterns.length > 0 && (
                <div className="mt-3">
                  <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Matched Patterns:
                  </p>
                  <ul className="list-disc list-inside space-y-1 text-sm text-gray-600 dark:text-gray-400">
                    {injection.matched_patterns.map((pattern, i) => (
                      <li key={i} className="font-mono bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">
                        {pattern}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Confidence bar */}
              <div className="mt-3">
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                  <div
                    className="bg-orange-600 h-2 rounded-full transition-all"
                    style={{ width: `${injection.confidence * 100}%` }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
