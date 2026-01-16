import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { AlertTriangle, Shield, Info, ChevronLeft, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ThreatEvent } from '@/api/types';

interface RecentThreatsProps {
  threats: ThreatEvent[];
}

export function RecentThreats({ threats }: RecentThreatsProps) {
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  const totalPages = Math.ceil(threats.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const currentThreats = threats.slice(startIndex, endIndex);
  const getThreatIcon = (threatType: string) => {
    if (threatType.toLowerCase().includes('injection')) {
      return <AlertTriangle className="h-4 w-4" />;
    }
    if (threatType.toLowerCase().includes('pii')) {
      return <Shield className="h-4 w-4" />;
    }
    return <Info className="h-4 w-4" />;
  };

  const getThreatColor = (riskScore: number, blocked: boolean) => {
    if (blocked) return 'text-destructive';
    if (riskScore > 0.7) return 'text-orange-500';
    if (riskScore > 0.4) return 'text-yellow-500';
    return 'text-muted-foreground';
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Threats</CardTitle>
        <CardDescription>
          Latest detected security events
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {threats.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Shield className="h-12 w-12 mx-auto mb-2 opacity-50" />
              <p>No threats detected</p>
            </div>
          ) : (
            <>
              <div className="space-y-3">
                {currentThreats.map((threat, index) => (
              <div
                key={index}
                className="flex items-start space-x-3 p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors"
              >
                <div className={cn("mt-0.5", getThreatColor(threat.risk_score, threat.blocked))}>
                  {getThreatIcon(threat.threat_type)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium">{threat.threat_type}</p>
                    <span className="text-xs text-muted-foreground">
                      {new Date(threat.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground truncate mt-0.5">
                    {threat.user_input}
                  </p>
                  <div className="flex items-center flex-wrap gap-2 mt-2">
                    {/* Threat Count Badges */}
                    {threat.threat_count_by_type && (
                      <div className="flex items-center gap-1">
                        {threat.threat_count_by_type.pii && threat.threat_count_by_type.pii > 0 && (
                          <Badge variant="destructive" className="text-xs">
                            {threat.threat_count_by_type.pii} PII
                          </Badge>
                        )}
                        {threat.threat_count_by_type.injection && threat.threat_count_by_type.injection > 0 && (
                          <Badge className="text-xs bg-orange-600">
                            {threat.threat_count_by_type.injection} Injection
                          </Badge>
                        )}
                        {threat.threat_count_by_type.content_violation && threat.threat_count_by_type.content_violation > 0 && (
                          <Badge className="text-xs bg-yellow-600">
                            {threat.threat_count_by_type.content_violation} Violation
                          </Badge>
                        )}
                      </div>
                    )}
                    <span className="text-xs">
                      Risk: <span className="font-medium">{threat.risk_score.toFixed(2)}</span>
                    </span>
                    {threat.blocked && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-destructive/10 text-destructive font-medium">
                        Blocked
                      </span>
                    )}
                    {threat.user_id && (
                      <span className="text-xs text-muted-foreground">
                        User: {threat.user_id}
                      </span>
                    )}
                  </div>
                </div>
              </div>
                ))}
              </div>

              {/* Pagination Controls */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between pt-4 border-t">
                  <p className="text-xs text-muted-foreground">
                    Page {currentPage} of {totalPages} ({threats.length} total)
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                      disabled={currentPage === 1}
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                      disabled={currentPage === totalPages}
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
