/**
 * Lightweight pub/sub for IOC lifecycle events (ioc_progress, ioc_enforced,
 * ioc_update) coming over the dashboard WebSocket.
 *
 * App.jsx feeds WS messages into `emitIocEvent`; the IOC Management page and
 * the HITL enforcement checklist subscribe by decision_id / ioc_id.
 */

const listeners = new Set();

export function emitIocEvent(event) {
  listeners.forEach((fn) => {
    try {
      fn(event);
    } catch (e) {
      console.error('[iocEvents] listener error:', e);
    }
  });
}

export function subscribeIocEvents(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

/** Map raw WS (event_type, data) pairs into ioc events. */
export function handleWsIocEvent(eventType, data) {
  if (eventType === 'ioc_progress' || eventType === 'ioc_enforced' || eventType === 'ioc_update') {
    emitIocEvent({ type: eventType, ...data });
  }
}