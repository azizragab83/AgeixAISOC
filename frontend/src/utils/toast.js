/**
 * Lightweight DOM-level toast notifications.
 *
 * Rendered outside the React tree (direct DOM) so toasts survive the
 * unmounting of the component that triggered them - critical for the HITL
 * flow where the card fades out while the confirmation toast is still visible.
 */

const TOAST_STYLES = {
  success: {
    border: 'border-green-500/50',
    bg: 'bg-gray-900/95',
    text: 'text-green-400',
    glow: 'shadow-[0_0_24px_rgba(34,197,94,0.25)]',
  },
  info: {
    border: 'border-cyan-500/50',
    bg: 'bg-gray-900/95',
    text: 'text-cyan-400',
    glow: 'shadow-[0_0_24px_rgba(6,182,212,0.25)]',
  },
  error: {
    border: 'border-red-500/50',
    bg: 'bg-gray-900/95',
    text: 'text-red-400',
    glow: 'shadow-[0_0_24px_rgba(239,68,68,0.25)]',
  },
};

let container = null;

function ensureContainer() {
  if (!container || !document.body.contains(container)) {
    container = document.createElement('div');
    container.id = 'ageix-toast-root';
    container.style.cssText =
      'position:fixed;bottom:1.5rem;right:1.5rem;z-index:9999;display:flex;flex-direction:column;gap:0.5rem;pointer-events:none;';
    document.body.appendChild(container);
  }
  return container;
}

export function showToast(message, kind = 'info', duration = 2800) {
  const style = TOAST_STYLES[kind] || TOAST_STYLES.info;
  const root = ensureContainer();

  const el = document.createElement('div');
  el.className = [
    'flex items-center gap-2 px-4 py-2.5 rounded-lg border backdrop-blur-sm font-mono text-xs font-bold',
    style.border, style.bg, style.text, style.glow,
  ].join(' ');
  el.style.cssText =
    'opacity:0;transform:translateY(12px) scale(0.96);transition:all 0.3s cubic-bezier(0.16,1,0.3,1);';
  el.textContent = message;

  root.appendChild(el);

  // Enter
  requestAnimationFrame(() => {
    el.style.opacity = '1';
    el.style.transform = 'translateY(0) scale(1)';
  });

  // Exit + cleanup
  setTimeout(() => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(8px) scale(0.95)';
    setTimeout(() => el.remove(), 350);
  }, duration);
}