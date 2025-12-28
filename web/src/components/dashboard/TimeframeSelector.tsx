import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface TimeframeSelectorProps {
  value: string;
  onChange: (value: string) => void;
}

const timeframes = [
  { value: '1h', label: '1 Hour' },
  { value: '24h', label: '24 Hours' },
  { value: '7d', label: '7 Days' },
  { value: '30d', label: '30 Days' },
];

export function TimeframeSelector({ value, onChange }: TimeframeSelectorProps) {
  return (
    <div className="flex items-center space-x-2">
      {timeframes.map((timeframe) => (
        <Button
          key={timeframe.value}
          variant={value === timeframe.value ? 'default' : 'outline'}
          size="sm"
          onClick={() => onChange(timeframe.value)}
          className={cn(
            "transition-all",
            value === timeframe.value && "shadow-md"
          )}
        >
          {timeframe.label}
        </Button>
      ))}
    </div>
  );
}
