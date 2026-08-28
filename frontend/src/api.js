import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || '';

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' }
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    console.error('[API Error]', err.response?.data || err.message);
    return Promise.reject(err);
  }
);

export class SOCWebSocket {
  constructor(onMessage, onOpen, onClose) {
    this.onMessage = onMessage;
    this.onOpen = onOpen;
    this.onClose = onClose;
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 10;
    this.reconnectDelay = 2000;
    this.intentionalClose = false;
    this.connect();
  }

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return;
    
    try {
      const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsHost = API_BASE ? API_BASE.replace(/^https?:\/\//, '') : window.location.host;
      this.ws = new WebSocket(`${proto}//${wsHost}/ws/dashboard`);
      this.ws.onopen = () => {
        console.log('[WS] Connected to dashboard');
        this.reconnectAttempts = 0;
        this.onOpen?.();
      };
      
      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.onMessage?.(data);
        } catch (e) {
          console.error('[WS] Parse error:', e);
        }
      };
      
      this.ws.onclose = (event) => {
        console.log('[WS] Disconnected:', event.code, event.reason);
        this.onClose?.();
        if (!this.intentionalClose) this.scheduleReconnect();
      };
      
      this.ws.onerror = (err) => console.error('[WS] Error:', err);
    } catch (err) {
      console.error('[WS] Connection failed:', err);
      this.scheduleReconnect();
    }
  }

  scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[WS] Max reconnect attempts reached');
      return;
    }
    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.min(this.reconnectAttempts, 5);
    console.log(`[WS] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
    setTimeout(() => this.connect(), delay);
  }

  send(data) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  disconnect() {
    this.intentionalClose = true;
    this.ws?.close(1000, 'Client disconnect');
  }
}

export const triggerAttack = (attackType, customCommand = null) =>
  api.post('/api/trigger-attack', { attack_type: attackType, custom_command: customCommand });

export const launchAttack = (attackType, target) =>
  api.post('/api/lab/launch-attack', { attack_type: attackType, target });

export const toggleAutoAttack = (enabled) =>
  api.post('/api/lab/auto-attack/toggle', { enabled });

export const getAutoAttackStatus = () =>
  api.get('/api/lab/auto-attack/status');

export const getPendingReviewRules = () =>
  api.get('/api/rules/pending-review');

export const reviewRule = (ruleId, action) =>
  api.post(`/api/rules/${ruleId}/review`, { action });

export const deleteRule = (ruleId) =>
  api.delete(`/api/rules/${ruleId}`);

export const nlQuery = (query, alertId = null) =>
  api.post('/api/query/nl', { query, alert_id: alertId });

export const getForensics = (incidentId) =>
  api.get(`/api/forensics/${incidentId}`);

export const getAlertsFeed = (limit = 50, severity = null) =>
  api.get('/api/alerts', { params: { limit, severity } });

export const getAlertsHistory = (limit = 50) =>
  api.get('/api/alerts/history', { params: { limit } });

export const deployRule = (ruleData) =>
  api.post('/api/rules/deploy', ruleData);

export const labApi = {
  getStatus: () => api.get('/api/lab/status'),
  launchAttack: (attackType, target) => api.post('/api/lab/launch-attack', { attack_type: attackType, target }),
  checkNetwork: () => api.post('/api/lab/check-network')
};

export const soarApi = {
  execute: (actions) => api.post('/api/soar/execute', { actions }),
  executeReal: (action, params) => api.post('/api/soar/execute-real', { action, params })
};

export const dashboardApi = {
  getMetrics: () => api.get('/api/dashboard/metrics'),
  getKPIs: () => api.get('/api/dashboard/kpis'),
  getAlerts: (limit = 50) => api.get(`/api/alerts?limit=${limit}`)
};

export const rulesApi = {
  getRules: () => api.get('/api/rules'),
  deploy: (ruleData) => api.post('/api/rules/deploy', ruleData),
};

export const decisionApi = {
  submit: (decisionId, action, metadata = {}, addToRag = false) =>
    api.post('/api/human-decision', { decision_id: decisionId, action, metadata, add_to_rag: addToRag })
};

export const tiApi = {
  getCoverage: () => api.get('/api/ti/coverage'),
};

export const chatApi = {
  send: (message, history = []) => api.post('/api/chat', { message, history }),
};

export const dataApi = {
  getKnowledgeSources: () => api.get('/api/knowledge-sources'),
  getCMDB: () => api.get('/api/cmdb/assets'),
  getComplianceMapping: (mitreId) => api.get(`/api/compliance/mapping/${mitreId}`),
  getThreatIntelStatus: () => api.get('/api/knowledge/threat-intel/status'),
  getAlertReduction: () => api.get('/api/dashboard/alert-reduction-stats'),
  getGapClosure: () => api.get('/api/dashboard/gap-closure-stats'),
  refreshMitre: () => api.post('/api/knowledge/mitre/refresh'),
  refreshThreatIntel: () => api.post('/api/knowledge/threat-intel/refresh'),
  getToolsHealth: () => api.get('/api/health/tools'),
};
