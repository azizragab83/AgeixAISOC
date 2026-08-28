const STYLES = {
  '🟢': 'bg-green-100 dark:bg-green-500/10 text-green-700 dark:text-green-400',
  '🟡': 'bg-yellow-100 dark:bg-yellow-500/10 text-yellow-700 dark:text-yellow-400',
  '⚪': 'bg-slate-100 dark:bg-slate-500/10 text-slate-600 dark:text-slate-400',
  '🔵': 'bg-blue-100 dark:bg-blue-500/10 text-blue-700 dark:text-blue-400',
};

export default function DataSourceBadge({ label, className = '' }) {
  const icon = label?.charAt(0) || '⚪';
  const style = STYLES[icon] || STYLES['⚪'];
  return (
    <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-semibold whitespace-nowrap ${style} ${className}`}>
      {label}
    </span>
  );
}
