import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Presentation as PresentationIcon,
  Briefcase,
  FileSearch,
  Microscope,
  Film,
  Mic,
  FileText,
  ScrollText,
  Settings,
  X,
} from 'lucide-react';

export interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  mobileOpen: boolean;
  onMobileClose: () => void;
}

interface NavItem {
  label: string;
  path: string;
  icon: typeof LayoutDashboard;
}

const navItems: NavItem[] = [
  { label: 'Dashboard', path: '/', icon: LayoutDashboard },
  { label: 'Presentation (PPT)', path: '/presentation', icon: PresentationIcon },
  { label: 'Cases', path: '/cases', icon: Briefcase },
  { label: 'Evidence', path: '/evidence', icon: FileSearch },
  { label: 'Image Analysis', path: '/analysis', icon: Microscope },
  { label: 'Video Forensics', path: '/video', icon: Film },
  { label: 'Audio Forensics', path: '/audio', icon: Mic },
  { label: 'Reports', path: '/reports', icon: FileText },
  { label: 'Audit Trail', path: '/audit', icon: ScrollText },
  { label: 'Settings', path: '/settings', icon: Settings },
];

export function Sidebar({ collapsed, mobileOpen, onMobileClose }: SidebarProps) {
  return (
    <aside
      className={`
        fixed inset-y-0 left-0 z-40 flex flex-col bg-white border-r border-slate-200 transition-all duration-200 ease-in-out
        ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}
        md:translate-x-0 md:static md:z-auto
        ${collapsed ? 'md:w-16' : 'md:w-64'}
        w-64
      `}
    >
      {/* Brand / Logo Area */}
      <div className="h-14 px-4 flex items-center justify-between border-b border-slate-200">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-9 h-9 rounded-xl bg-slate-950 border border-cyan-500/30 shadow-xs flex items-center justify-center flex-shrink-0 p-1 overflow-hidden group">
            <img src="/garuda-logo.svg" alt="Garuda Forensics" className="w-7 h-7 object-contain transition-transform group-hover:scale-105" />
          </div>
          {(!collapsed || mobileOpen) && (
            <div className="flex flex-col min-w-0">
              <span className="text-sm font-bold text-slate-900 tracking-wide truncate">Garuda</span>
              <span className="text-[10px] text-cyan-600 font-mono font-semibold tracking-wider uppercase">Forensics</span>
            </div>
          )}
        </div>

        {/* Mobile close button */}
        <button
          type="button"
          onClick={onMobileClose}
          className="md:hidden p-1.5 rounded-md text-slate-500 hover:text-slate-900 hover:bg-slate-100 transition-colors"
          aria-label="Close sidebar"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              onClick={onMobileClose}
              title={collapsed && !mobileOpen ? item.label : undefined}
              className={({ isActive }) =>
                `nav-link ${isActive ? 'nav-link-active' : ''} ${
                  collapsed && !mobileOpen ? 'justify-center px-2' : 'px-3'
                }`
              }
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {(!collapsed || mobileOpen) && (
                <span className="truncate">{item.label}</span>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Bottom Area — Version Info */}
      <div className="p-3 border-t border-slate-200">
        {collapsed && !mobileOpen ? (
          <div className="flex justify-center" title="Garuda Forensics v2.4">
            <span className="px-1.5 py-0.5 text-[10px] font-mono text-cyan-600 bg-slate-100 rounded border border-slate-200">
              v2.4
            </span>
          </div>
        ) : (
          <div className="flex items-center justify-between px-2.5 py-2 rounded-md bg-slate-50 border border-slate-200 text-xs text-slate-500">
            <span className="text-slate-500 font-medium truncate">Garuda Core</span>
            <span className="font-mono text-cyan-600 text-[11px] bg-white px-1.5 py-0.5 rounded border border-slate-200 flex-shrink-0">
              v2.4-saas
            </span>
          </div>
        )}
      </div>
    </aside>
  );
}
