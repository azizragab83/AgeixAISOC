import { useState, useEffect, useCallback } from 'react';
import { getAlertsFeed } from '../api';

export function useAlerts(limit = 50) {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetch = useCallback(async () => {
    try {
      const res = await getAlertsFeed(limit);
      setAlerts(res.data.alerts || []);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [limit]);

  useEffect(() => {
    fetch();
    const interval = setInterval(fetch, 30000);
    return () => clearInterval(interval);
  }, [fetch]);

  return { alerts, loading, error, refresh: fetch };
}
