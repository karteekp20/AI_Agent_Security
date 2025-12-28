import { ReactNode, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Shield, LayoutDashboard, Shield as ShieldIcon, FileText, FileBarChart, Settings, LogOut, Menu, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface AppLayoutProps {
  children: ReactNode;
}

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Policies', href: '/policies', icon: ShieldIcon },
  { name: 'Audit Logs', href: '/audit-logs', icon: FileText },
  { name: 'Reports', href: '/reports', icon: FileBarChart },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export function AppLayout({ children }: AppLayoutProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      {/* Mobile Header */}
      <header className="lg:hidden fixed top-0 left-0 right-0 h-16 bg-white dark:bg-slate-900 border-b flex items-center justify-between px-4 z-50">
        <div className="flex items-center space-x-3">
          <Shield className="h-6 w-6 text-primary" />
          <div>
            <h1 className="text-lg font-bold">Sentinel</h1>
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setSidebarOpen(!sidebarOpen)}
        >
          {sidebarOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </Button>
      </header>

      {/* Sidebar Overlay for Mobile */}
      {sidebarOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/50 z-40"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed top-0 bottom-0 w-64 bg-white dark:bg-slate-900 border-r flex flex-col z-50 transition-transform duration-300',
          'lg:translate-x-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* Logo */}
        <div className="p-6 border-b">
          <div className="flex items-center space-x-3">
            <Shield className="h-8 w-8 text-primary" />
            <div>
              <h1 className="text-xl font-bold">Sentinel</h1>
              <p className="text-xs text-muted-foreground">AI Security Platform</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1">
          {navigation.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.href;

            return (
              <button
                key={item.name}
                onClick={() => {
                  navigate(item.href);
                  setSidebarOpen(false);
                }}
                className={cn(
                  'w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors',
                  isActive
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-foreground'
                )}
              >
                <Icon className="h-5 w-5" />
                <span className="font-medium">{item.name}</span>
              </button>
            );
          })}
        </nav>

        {/* Logout */}
        <div className="p-4 border-t">
          <Button
            variant="ghost"
            className="w-full justify-start"
            onClick={handleLogout}
          >
            <LogOut className="h-5 w-5 mr-3" />
            Logout
          </Button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="lg:ml-64 pt-16 lg:pt-0">
        {children}
      </main>
    </div>
  );
}
