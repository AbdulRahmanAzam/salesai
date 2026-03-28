import { useState, useEffect, useCallback } from 'react';

/**
 * Generic hook for managing agent sessions via the API.
 * @param {object} api - An API object with getSessions, getSession, saveSession, deleteSession
 */
export function useSessions(api) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeSession, setActiveSession] = useState(null);
  const [loadingSession, setLoadingSession] = useState(false);

  const fetchSessions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getSessions();
      setSessions(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const loadSession = useCallback(async (id) => {
    setLoadingSession(true);
    try {
      const data = await api.getSession(id);
      setActiveSession(data);
      return data;
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setLoadingSession(false);
    }
  }, [api]);

  const saveSession = useCallback(async (data) => {
    try {
      const saved = await api.saveSession(data);
      setSessions(prev => [saved, ...prev]);
      setActiveSession(saved);
      return saved;
    } catch (err) {
      setError(err.message);
      return null;
    }
  }, [api]);

  const deleteSession = useCallback(async (id) => {
    try {
      await api.deleteSession(id);
      setSessions(prev => prev.filter(s => s._id !== id));
      if (activeSession?._id === id) setActiveSession(null);
    } catch (err) {
      setError(err.message);
    }
  }, [api, activeSession]);

  const clearActive = useCallback(() => setActiveSession(null), []);

  return {
    sessions,
    loading,
    error,
    activeSession,
    loadingSession,
    fetchSessions,
    loadSession,
    saveSession,
    deleteSession,
    clearActive,
  };
}
