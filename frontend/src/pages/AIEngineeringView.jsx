import { useState, useEffect } from 'react';
import {
  Cpu, Database, BookOpen, ExternalLink, Network, Layers,
  Loader2, CheckCircle2, XCircle, Brain, FileText, GitBranch,
  Server, Zap, Shield
} from 'lucide-react';
import { api } from '../api';

function StatusBadge({ status }) {
  if (status === true || status === 'online' || status === 'Ready' || status === 'Online') {
    return <span className="flex items-center gap-1 text-xs text-green-400"><CheckCircle2 className="w-3 h-3" /> Online</span>;
  }
  if (status === false || status === 'offline' || status === 'Offline') {
    return <span className="flex items-center gap-1 text-xs text-red-400"><XCircle className="w-3 h-3" /> Offline</span>;
  }
  return <span className="flex items-center gap-1 text-xs text-slate-500"><Loader2 className="w-3 h-3 animate-spin" /> Checking...</span>;
}

function StatCard({ icon: Icon, label, value, sub, color }) {
  return (
    <div className="soc-card">
      <div className="flex items-center gap-3 mb-2">
        <div className={`p-2 rounded-lg ${color || 'bg-slate-800'}`}>
          <Icon className={`w-5 h-5 ${color ? 'text-white' : 'text-slate-400'}`} />
        </div>
        <span className="text-xs font-medium text-slate-400 uppercase">{label}</span>
      </div>
      <div className="text-2xl font-bold text-white mb-1">{value}</div>
      {sub && <div className="text-xs text-slate-500">{sub}</div>}
    </div>
  );
}

function LinkCard({ title, url, description }) {
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-start gap-3 p-3 rounded-lg bg-slate-800/50 border border-slate-700/50 hover:bg-slate-800 hover:border-cyan-500/30 transition-all group"
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-white group-hover:text-cyan-400 transition-colors">{title}</span>
          <ExternalLink className="w-3 h-3 text-slate-500 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>
        {description && <div className="text-xs text-slate-500 mt-0.5">{description}</div>}
      </div>
    </a>
  );
}

export default function AIEngineeringView() {
  const [health, setHealth] = useState(null);
  const [ragStats, setRagStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetch = async () => {
      setLoading(true);
      try {
        const [healthRes, ragRes] = await Promise.allSettled([
          api.get('/api/health'),
          api.get('/api/rag/stats'),
        ]);
        if (healthRes.status === 'fulfilled') setHealth(healthRes.value.data);
        if (ragRes.status === 'fulfilled') setRagStats(ragRes.value.data);
      } catch {}
      setLoading(false);
    };
    fetch();
    const interval = setInterval(fetch, 30000);
    return () => clearInterval(interval);
  }, []);

  const ollamaOnline = health?.ollama_configured || false;
  const chromaReady = ragStats?.chroma_ready || false;
  const totalDocs = ragStats?.total_documents ?? 0;

  return (
    <div className="h-full flex flex-col p-4 gap-4 overflow-y-auto">
      <h1 className="text-lg font-bold text-white flex items-center gap-2">
        <Cpu className="w-5 h-5 text-cyan-400" />
        AI Engineering Hub
      </h1>

      {/* Section 1: Live AI Stack */}
      <div className="soc-card">
        <div className="flex items-center gap-2 mb-4">
          <Server className="w-5 h-5 text-cyan-400" />
          <h2 className="text-sm font-bold text-white">Live AI Stack Status</h2>
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-24 text-slate-500 gap-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            Fetching live AI stack status...
          </div>
        ) : (
          <>
            <div className="grid grid-cols-3 gap-3 mb-4">
              <StatCard
                icon={Brain}
                label="Ollama"
                value={<StatusBadge status={ollamaOnline} />}
                sub="LLM Runtime"
                color="bg-purple-600/20"
              />
              <StatCard
                icon={Database}
                label="ChromaDB"
                value={<StatusBadge status={chromaReady} />}
                sub="Vector Database"
                color="bg-green-600/20"
              />
              <StatCard
                icon={FileText}
                label="Total Documents"
                value={totalDocs}
                sub="Across all KBs"
                color="bg-blue-600/20"
              />
            </div>

            {/* Active LLMs */}
            <div className="mt-4">
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Active Language Models</h3>
              <div className="grid grid-cols-2 gap-3">
                <div className="flex items-center gap-3 p-3 rounded-lg bg-slate-800/30 border border-slate-700/50">
                  <div className="p-2 rounded-lg bg-purple-600/10">
                    <Cpu className="w-4 h-4 text-purple-400" />
                  </div>
                  <div>
                    <div className="text-sm font-medium text-white">qwen2.5:14b</div>
                    <div className="text-xs text-slate-500">General purpose LLM • 14B params</div>
                    <StatusBadge status={ollamaOnline ? 'online' : 'offline'} />
                  </div>
                </div>
                <div className="flex items-center gap-3 p-3 rounded-lg bg-slate-800/30 border border-slate-700/50">
                  <div className="p-2 rounded-lg bg-purple-600/10">
                    <Cpu className="w-4 h-4 text-purple-400" />
                  </div>
                  <div>
                    <div className="text-sm font-medium text-white">llama3.1</div>
                    <div className="text-xs text-slate-500">Threat analysis LLM • 8B params</div>
                    <StatusBadge status={ollamaOnline ? 'online' : 'offline'} />
                  </div>
                </div>
              </div>
            </div>

            {/* RAG Collections */}
            <div className="mt-4">
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">RAG Knowledge Bases</h3>
              <div className="grid grid-cols-3 gap-3">
                {['past_incidents', 'threat_intel', 'sigma_rules', 'cve_kev', 'learned_decisions'].map((kb) => (
                  <div key={kb} className="flex items-center gap-2 p-2 rounded-lg bg-slate-800/20">
                    <div className={`w-2 h-2 rounded-full ${chromaReady ? 'bg-green-500' : 'bg-red-500'}`} />
                    <span className="text-xs text-slate-400 font-mono">{kb}</span>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>

      {/* Section 2: AI Learning Roadmaps */}
      <div className="soc-card">
        <div className="flex items-center gap-2 mb-4">
          <BookOpen className="w-5 h-5 text-amber-400" />
          <h2 className="text-sm font-bold text-white">Recommended AI Engineering Roadmaps</h2>
        </div>

        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">LLM Runtimes</h3>
        <div className="grid grid-cols-2 gap-2 mb-4">
          <LinkCard title="Ollama" url="https://github.com/ollama/ollama" description="Local LLM runtime — runs qwen2.5, llama3.1, and 100+ models" />
          <LinkCard title="Hugging Face Transformers" url="https://github.com/huggingface/transformers" description="Industry-standard transformer library for NLP" />
        </div>

        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Frameworks</h3>
        <div className="grid grid-cols-3 gap-2 mb-4">
          <LinkCard title="LangChain" url="https://github.com/langchain-ai/langchain" description="LLM application framework with chains & agents" />
          <LinkCard title="CrewAI" url="https://github.com/crewAIInc/crewAI" description="Multi-agent orchestration framework" />
          <LinkCard title="LangGraph" url="https://github.com/langchain-ai/langgraph" description="Graph-based agent pipelines (used in AgeixAISOC)" />
        </div>

        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Fine-Tuning</h3>
        <div className="grid grid-cols-2 gap-2 mb-4">
          <LinkCard title="Unsloth" url="https://github.com/unslothai/unsloth" description="2x faster LLM fine-tuning with lower memory" />
          <LinkCard title="PEFT" url="https://github.com/huggingface/peft" description="Parameter-Efficient Fine-Tuning (LoRA, Adapters)" />
        </div>

        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">RAG & Vector Databases</h3>
        <div className="grid grid-cols-2 gap-2">
          <LinkCard title="Chroma" url="https://github.com/chroma-core/chroma" description="Open-source embedding database (used in AgeixAISOC)" />
        </div>
      </div>

      {/* Section 3: System Design & Architecture */}
      <div className="soc-card">
        <div className="flex items-center gap-2 mb-4">
          <GitBranch className="w-5 h-5 text-green-400" />
          <h2 className="text-sm font-bold text-white">System Design & Architecture</h2>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <LinkCard
            title="system-design-primer"
            url="https://github.com/donnemartin/system-design-primer"
            description="Learn how to design large-scale systems (120k+ stars)"
          />
          <LinkCard
            title="awesome-scalability"
            url="https://github.com/binhnguyennus/awesome-scalability"
            description="Best practices for building scalable, reliable systems"
          />
        </div>
      </div>

      {/* Tech Stack Summary */}
      <div className="soc-card">
        <div className="flex items-center gap-2 mb-3">
          <Zap className="w-5 h-5 text-cyan-400" />
          <h2 className="text-sm font-bold text-white">AgeixAISOC Tech Stack</h2>
        </div>
        <div className="grid grid-cols-4 gap-3 text-xs">
          {[
            { icon: Server, label: 'FastAPI', sub: 'Python backend' },
            { icon: Layers, label: 'React + Vite', sub: 'Frontend' },
            { icon: Database, label: 'ChromaDB', sub: 'Vector store' },
            { icon: Cpu, label: 'Ollama', sub: 'LLM runtime' },
            { icon: GitBranch, label: 'LangGraph', sub: 'AI pipeline' },
            { icon: Network, label: 'n8n', sub: 'SOAR automation' },
            { icon: Shield, label: 'FortiGate', sub: 'Firewall API' },
            { icon: Brain, label: 'CrewAI', sub: 'Agent framework' },
          ].map((item, idx) => (
            <div key={idx} className="flex items-center gap-2 p-2 rounded-lg bg-slate-800/30">
              <item.icon className="w-4 h-4 text-cyan-400 shrink-0" />
              <div>
                <div className="text-white font-medium">{item.label}</div>
                <div className="text-slate-500">{item.sub}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}