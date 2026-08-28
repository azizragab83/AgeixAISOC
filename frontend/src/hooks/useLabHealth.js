import { useState, useEffect, useCallback } from 'react';
import { labApi } from '../api';

export function useLabHealth(intervalMs = 15000) {
  const [labStatus, setLabStatus] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetch = useCallback(async () => {
    try {
      const res = await labApi.getStatus();
      setLabStatus(res.data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch();
    const interval = setInterval(fetch, intervalMs);
    return () => clearInterval(interval);
  }, [fetch, intervalMs]);

  return { labStatus, loading, error, refresh: fetch };
}
