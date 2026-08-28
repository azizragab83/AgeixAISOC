import { useState } from 'react';
import { Search, Terminal, Box, Cloud, ExternalLink, Wrench } from 'lucide-react';

const CATEGORIES = [
  {
    id: 'unix-tools',
    label: 'Modern Unix Power Tools',
    icon: Terminal,
    color: 'text-green-400',
    bgColor: 'bg-green-600/10',
    borderColor: 'border-green-500/30',
    hoverBorder: 'hover:border-green-500/50',
    items: [
      { name: 'eza', url: 'https://github.com/eza-community/eza', description: 'Modern ls replacement with icons, colors, and tree view' },
      { name: 'bat', url: 'https://github.com/sharkdp/bat', description: 'cat clone with syntax highlighting and Git integration' },
      { name: 'zoxide', url: 'https://github.com/ajeetdsouza/zoxide', description: 'Smarter cd command — learns your navigation habits' },
      { name: 'ripgrep', url: 'https://github.com/BurntSushi/ripgrep', description: 'Fastest text search tool — recursively searches directories' },
      { name: 'btop', url: 'https://github.com/aristocratos/btop', description: 'High-performance system monitor with GPU support' },
    ],
  },
  {
    id: 'terminal-shell',
    label: 'Terminal & Shell Experience',
    icon: Terminal,
    color: 'text-purple-400',
    bgColor: 'bg-purple-600/10',
    borderColor: 'border-purple-500/30',
    hoverBorder: 'hover:border-purple-500/50',
    items: [
      { name: 'Alacritty', url: 'https://github.com/alacritty/alacritty', description: 'GPU-accelerated terminal emulator' },
      { name: 'Oh My Zsh', url: 'https://github.com/ohmyzsh/ohmyzsh', description: 'Community-driven Zsh framework with 300+ plugins' },
      { name: 'Starship', url: 'https://github.com/starship/starship', description: 'Minimal, blazing-fast prompt for any shell' },
      { name: 'Fastfetch', url: 'https://github.com/fastfetch-cli/fastfetch', description: 'Neofetch replacement — system info at lightning speed' },
    ],
  },
  {
    id: 'devops-cloud',
    label: 'DevOps & Cloud Native',
    icon: Cloud,
    color: 'text-cyan-400',
    bgColor: 'bg-cyan-600/10',
    borderColor: 'border-cyan-500/30',
    hoverBorder: 'hover:border-cyan-500/50',
    items: [
      { name: 'Docker', url: 'https://github.com/docker', description: 'Container platform — build, ship, and run anywhere' },
      { name: 'Kubernetes', url: 'https://github.com/kubernetes/kubernetes', description: 'Production-grade container orchestration system' },
      { name: 'Ansible', url: 'https://github.com/ansible/ansible', description: 'Agentless IT automation and configuration management' },
      { name: 'Terraform', url: 'https://github.com/hashicorp/terraform', description: 'Infrastructure as Code for multi-cloud provisioning' },
      { name: 'Coolify', url: 'https://github.com/coollabsio/coolify', description: 'Self-hostable Heroku alternative with one-click deploy' },
      { name: 'Grafana', url: 'https://github.com/grafana/grafana', description: 'Observability platform — metrics, logs, and traces' },
    ],
  },
];

export default function DevOpsResourcesView() {
  const [searchQuery, setSearchQuery] = useState('');

  const filteredCategories = CATEGORIES.map((cat) => ({
    ...cat,
    items: cat.items.filter(
      (item) =>
        item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.description.toLowerCase().includes(searchQuery.toLowerCase())
    ),
  })).filter((cat) => cat.items.length > 0);

  const totalVisible = filteredCategories.reduce((sum, cat) => sum + cat.items.length, 0);

  return (
    <div className="h-full flex flex-col p-4 gap-4 overflow-y-auto">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-bold text-white flex items-center gap-2">
          <Wrench className="w-5 h-5 text-cyan-400" />
          SysAdmin & DevOps Resources
        </h1>
      </div>

      {/* Search Input */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search tools (e.g., bat, docker, terminal)..."
          className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-10 pr-4 py-3 text-sm text-slate-300 placeholder-slate-500 focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/20 transition-all"
        />
        {searchQuery && (
          <button
            onClick={() => setSearchQuery('')}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-500 hover:text-slate-300 transition-colors"
          >
            Clear
          </button>
        )}
      </div>

      {/* Results count */}
      {searchQuery && (
        <div className="text-xs text-slate-500">
          Found {totalVisible} tool{totalVisible !== 1 ? 's' : ''} matching "{searchQuery}"
        </div>
      )}

      {/* No results */}
      {filteredCategories.length === 0 && (
        <div className="flex flex-col items-center justify-center h-48 text-slate-600">
          <Search className="w-10 h-10 mb-3 opacity-30" />
          <span className="text-sm">No tools found matching "{searchQuery}"</span>
          <span className="text-xs mt-1">Try a different search term</span>
        </div>
      )}

      {/* Categories */}
      {filteredCategories.map((cat) => (
        <div key={cat.id} className="soc-card">
          <div className="flex items-center gap-2 mb-4">
            <div className={`p-2 rounded-lg ${cat.bgColor}`}>
              <cat.icon className={`w-5 h-5 ${cat.color}`} />
            </div>
            <h2 className="text-sm font-bold text-white">{cat.label}</h2>
            <span className="text-xs text-slate-500 ml-auto">{cat.items.length} tools</span>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {cat.items.map((tool) => (
              <a
                key={tool.name}
                href={tool.url}
                target="_blank"
                rel="noopener noreferrer"
                className={`flex items-start gap-3 p-3 rounded-lg bg-slate-800/50 border border-slate-700/50 ${cat.hoverBorder} transition-all group`}
              >
                <div className={`p-2 rounded-lg ${cat.bgColor} shrink-0`}>
                  <Box className={`w-4 h-4 ${cat.color}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-white group-hover:text-cyan-400 transition-colors">{tool.name}</span>
                    <ExternalLink className="w-3 h-3 text-slate-500 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </div>
                  <div className="text-xs text-slate-500 mt-0.5">{tool.description}</div>
                </div>
              </a>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}