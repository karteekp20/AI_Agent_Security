import { Badge } from '@/components/ui/badge';
import type { PIIEntityDetail } from '@/api/types';

interface PIIEntitiesTableProps {
  entities: PIIEntityDetail[];
  showMaskedValues: boolean;
}

export function PIIEntitiesTable({ entities, showMaskedValues }: PIIEntitiesTableProps) {
  if (!entities || entities.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        No PII entities detected
      </div>
    );
  }

  const getEntityBadgeVariant = (entityType: string): string => {
    const type = entityType.toLowerCase();
    if (type.includes('credit_card') || type.includes('ssn') || type.includes('passport')) {
      return 'bg-red-600 text-white';
    }
    if (type.includes('email') || type.includes('phone')) {
      return 'bg-orange-600 text-white';
    }
    if (type.includes('api_key') || type.includes('aws') || type.includes('jwt')) {
      return 'bg-purple-600 text-white';
    }
    return 'bg-blue-600 text-white';
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse">
        <thead>
          <tr className="border-b border-gray-200 dark:border-gray-700">
            <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700 dark:text-gray-300">
              Entity Type
            </th>
            <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700 dark:text-gray-300">
              Position
            </th>
            <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700 dark:text-gray-300">
              Confidence
            </th>
            <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700 dark:text-gray-300">
              Detection
            </th>
            {showMaskedValues && (
              <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700 dark:text-gray-300">
                Masked Value
              </th>
            )}
          </tr>
        </thead>
        <tbody>
          {entities.map((entity, idx) => (
            <tr
              key={idx}
              className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-900/50"
            >
              <td className="py-3 px-4">
                <Badge className={getEntityBadgeVariant(entity.entity_type)}>
                  {entity.entity_type}
                </Badge>
              </td>
              <td className="py-3 px-4 text-sm text-gray-600 dark:text-gray-400">
                {entity.start_position}-{entity.end_position}
              </td>
              <td className="py-3 px-4">
                <div className="flex items-center gap-2">
                  <div className="w-16 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <div
                      className="bg-green-600 h-2 rounded-full transition-all"
                      style={{ width: `${entity.confidence * 100}%` }}
                    />
                  </div>
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    {(entity.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              </td>
              <td className="py-3 px-4">
                <Badge variant="outline" className="text-xs">
                  {entity.detection_method}
                </Badge>
              </td>
              {showMaskedValues && (
                <td className="py-3 px-4">
                  {entity.masked_value ? (
                    <code className="text-xs bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">
                      {entity.masked_value}
                    </code>
                  ) : (
                    <span className="text-xs text-gray-400">N/A</span>
                  )}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
