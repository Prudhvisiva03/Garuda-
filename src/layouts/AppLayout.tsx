import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Menu, ChevronLeft, ChevronRight, Bell } from 'lucide-react';
import { SystemStatusBar } from '@/components/DemoBanner';
import { Sidebar } from '@/components/navigation/Sidebar';

export function AppLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-700">
      {/* Platform Operational Status Bar */}
      <SystemStatusBar />

      <div className="flex flex-1 relative overflow-hidden">
        {/* Mobile backdrop */}
        {mobileOpen && (
          <div
            className="fixed inset-0 bg-black/20 backdrop-blur-sm z-30 md:hidden transition-opacity"
            onClick={() => setMobileOpen(false)}
            aria-label="Close navigation overlay"
          />
        )}

        {/* Sidebar */}
        <Sidebar
          collapsed={collapsed}
          onToggle={() => setCollapsed(!collapsed)}
          mobileOpen={mobileOpen}
          onMobileClose={() => setMobileOpen(false)}
        />

        {/* Main Workspace Area */}
        <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
          {/* Top Bar */}
          <header className="sticky top-0 z-20 h-14 bg-white/90 backdrop-blur border-b border-slate-200 px-4 sm:px-6 flex items-center justify-between">
            <div className="flex items-center gap-3">
              {/* Mobile menu toggle */}
              <button
                type="button"
                onClick={() => setMobileOpen(!mobileOpen)}
                className="md:hidden p-2 rounded-md text-slate-500 hover:text-slate-900 hover:bg-slate-100 transition-colors"
                aria-label="Toggle navigation menu"
              >
                <Menu className="w-5 h-5" />
              </button>

              {/* Desktop collapse toggle */}
              <button
                type="button"
                onClick={() => setCollapsed(!collapsed)}
                className="hidden md:flex p-1.5 rounded-md text-slate-500 hover:text-slate-900 hover:bg-slate-100 transition-colors"
                title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
                aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
              >
                {collapsed ? <ChevronRight className="w-5 h-5" /> : <ChevronLeft className="w-5 h-5" />}
              </button>

              {/* Breadcrumb / Platform Indicator */}
              <div className="hidden sm:flex items-center gap-2 text-xs">
                <span className="text-slate-500 font-medium">Platform</span>
                <span className="text-slate-300">/</span>
                <span className="text-slate-700 font-medium">Digital Forensics Workspace</span>
              </div>
            </div>

            {/* Right Action Icons */}
            <div className="flex items-center gap-2">
              <button
                type="button"
                title="System notifications active"
                className="p-2 rounded-md text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-colors"
                aria-label="Notifications"
              >
                <Bell className="w-4 h-4" />
              </button>
            </div>
          </header>

          {/* Page Content Viewport */}
          <main className="flex-1 p-4 sm:p-6 lg:p-8 bg-slate-50">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}
