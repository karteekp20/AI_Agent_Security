import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface HourlyActivity {
  hour: number;
  count: number;
}

interface AttackTimingChartProps {
  data: HourlyActivity[];
}

export function AttackTimingChart({ data }: AttackTimingChartProps) {
  const maxCount = Math.max(...data.map(d => d.count), 1);

  const getIntensityColor = (count: number) => {
    const intensity = count / maxCount;
    if (intensity === 0) return 'bg-slate-100 dark:bg-slate-800';
    if (intensity < 0.25) return 'bg-red-200 dark:bg-red-900';
    if (intensity < 0.5) return 'bg-red-300 dark:bg-red-800';
    if (intensity < 0.75) return 'bg-red-400 dark:bg-red-700';
    return 'bg-red-500 dark:bg-red-600';
  };

  // Group by 2-hour blocks for better visualization
  const blocks = Array.from({ length: 12 }, (_, i) => {
    const startHour = i * 2;
    const endHour = startHour + 1;
    const count = (data.find(d => d.hour === startHour)?.count || 0) +
                  (data.find(d => d.hour === endHour)?.count || 0);
    return { startHour, endHour, count };
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Attack Timing Pattern</CardTitle>
        <CardDescription>
          Threat activity by time of day
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          <div className="grid grid-cols-6 gap-2">
            {blocks.map((block, idx) => (
              <div key={idx} className="flex flex-col items-center">
                <div
                  className={`w-full h-20 rounded ${getIntensityColor(block.count)} flex items-center justify-center transition-colors`}
                  title={`${block.startHour}:00-${block.endHour}:59 - ${block.count} threats`}
                >
                  <span className="text-xs font-semibold">
                    {block.count > 0 ? block.count : ''}
                  </span>
                </div>
                <span className="text-xs text-muted-foreground mt-1">
                  {block.startHour}h
                </span>
              </div>
            ))}
          </div>
          <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground">
            <span>Less</span>
            <div className="flex gap-1">
              <div className="w-4 h-4 rounded bg-slate-100 dark:bg-slate-800"></div>
              <div className="w-4 h-4 rounded bg-red-200 dark:bg-red-900"></div>
              <div className="w-4 h-4 rounded bg-red-300 dark:bg-red-800"></div>
              <div className="w-4 h-4 rounded bg-red-400 dark:bg-red-700"></div>
              <div className="w-4 h-4 rounded bg-red-500 dark:bg-red-600"></div>
            </div>
            <span>More</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
