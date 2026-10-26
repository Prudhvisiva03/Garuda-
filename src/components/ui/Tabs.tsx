interface Tab {
  id: string;
  label: string;
  disabled?: boolean;
  disabledReason?: string;
}

interface TabsProps {
  tabs: Tab[];
  activeTab: string;
  onTabChange: (tabId: string) => void;
}

export function Tabs({ tabs, activeTab, onTabChange }: TabsProps) {
  return (
    <div className="flex gap-1 border-b border-slate-200">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => !tab.disabled && onTabChange(tab.id)}
          disabled={tab.disabled}
          title={tab.disabled ? tab.disabledReason : undefined}
          className={`px-4 py-2.5 text-sm font-medium transition-colors duration-150 border-b-2 -mb-px
            focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500
            ${activeTab === tab.id
              ? 'border-cyan-500 text-cyan-600'
              : 'border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-400'
            }
            ${tab.disabled ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'}
          `}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
