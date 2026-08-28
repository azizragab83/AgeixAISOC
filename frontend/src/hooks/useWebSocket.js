import { useState, useEffect, useRef, useCallback } from 'react';
import { SOCWebSocket } from '../api';

const MAX_BUFFER = 100;
const DEFAULT_THROTTLE_MS = 500;
const INITIAL_RECONNECT_DELAY = 1000;
const MAX_RECONNECT_DELAY = 30000;

export function useWebSocket(throttleMs = DEFAULT_THROTTLE_MS) {
  const [wsConnected, setWsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const wsRef = useRef(null);
  const handlersRef = useRef([]);
  const bufferRef = useRef([]);
  const throttleTimerRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimerRef = useRef(null);

  const processMessage = useCallback((data) => {
    // Add to buffer
    bufferRef.current.push(data);
    if (bufferRef.current.length > MAX_BUFFER) {
      bufferRef.current.shift();
    }

    // Throttle state updates
    if (!throttleTimerRef.current) {
      throttleTimerRef.current = setTimeout(() => {
        throttleTimerRef.current = null;
        // Flush buffer — take the latest message for state
        const latest = bufferRef.current[bufferRef.current.length - 1];
        if (latest) {
          setLastMessage(latest);
        }
        // Notify all handlers with all buffered messages
        const buffered = [...bufferRef.current];
        bufferRef.current = [];
        handlersRef.current.forEach((h) => {
          buffered.forEach((msg) => h(msg));
        });
      }, throttleMs);
    }
  }, [throttleMs]);

  const createSocket = useCallback(() => {
    setConnectionStatus('connecting');
    const socket = new SOCWebSocket(
      (data) => processMessage(data),
      () => {
        setWsConnected(true);
        setConnectionStatus('connected');
        reconnectAttemptsRef.current = 0;
      },
      () => {
        setWsConnected(false);
        setConnectionStatus('disconnected');
        // Schedule reconnection with exponential backoff
        const delay = Math.min(
          INITIAL_RECONNECT_DELAY * Math.pow(2, reconnectAttemptsRef.current),
          MAX_RECONNECT_DELAY
        );
        reconnectAttemptsRef.current += 1;
        setConnectionStatus('reconnecting');
        reconnectTimerRef.current = setTimeout(() => {
          createSocket();
        }, delay);
      }
    );
    wsRef.current = socket;
  }, [processMessage]);

  useEffect(() => {
    createSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.disconnect();
      }
      if (throttleTimerRef.current) {
        clearTimeout(throttleTimerRef.current);
      }
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
    };
  }, [createSocket]);

  const addHandler = useCallback((handler) => {
    handlersRef.current.push(handler);
    return () => {
      handlersRef.current = handlersRef.current.filter((h) => h !== handler);
    };
  }, []);

  return { ws: wsRef.current, wsConnected, lastMessage, addHandler, connectionStatus };
}