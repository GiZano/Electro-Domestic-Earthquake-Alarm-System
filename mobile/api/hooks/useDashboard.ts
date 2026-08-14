import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../client';
import { usePreferencesStore } from '../../store/usePreferencesStore';

export const useSensors = () => {
  const isOfflineMode = usePreferencesStore((state) => state.isOfflineMode);

  return useQuery({
    queryKey: ['sensors'],
    queryFn: async () => {
      const { data } = await apiClient.get('/sensors/');
      return data;
    },
    refetchInterval: 10000,
    enabled: !isOfflineMode,
  });
};

/** PostGIS zones for the per-zone dashboard selector. */
export const useZones = () => {
  const isOfflineMode = usePreferencesStore((state) => state.isOfflineMode);

  return useQuery({
    queryKey: ['zones'],
    queryFn: async () => {
      const { data } = await apiClient.get('/zones/');
      return data;
    },
    refetchInterval: 15000,
    enabled: !isOfflineMode,
  });
};

/**
 * Live per-zone seismograph feed: the latest N readings emitted by sensors
 * belonging to one PostGIS zone. Polls every second so the sliding window
 * scrolls smoothly.
 */
export const useZoneReadings = (zoneId: number | undefined, limit = 60) => {
  const isOfflineMode = usePreferencesStore((state) => state.isOfflineMode);

  return useQuery({
    queryKey: ['zoneReadings', zoneId, limit],
    queryFn: async () => {
      const { data } = await apiClient.get(`/zones/${zoneId}/readings`, {
        params: { limit },
      });
      // Newest-first from the API; the dashboard maintains its own sliding
      // window in chronological order.
      return data;
    },
    refetchInterval: 1000,
    enabled: !isOfflineMode && zoneId != null,
    placeholderData: (prev) => prev,
  });
};

export const useRecentReadings = () => {
  const isOfflineMode = usePreferencesStore((state) => state.isOfflineMode);

  return useQuery({
    queryKey: ['recentReadings'],
    queryFn: async () => {
      const { data } = await apiClient.get('/readings/?limit=50');
      return data.reverse();
    },
    refetchInterval: 2000,
    enabled: !isOfflineMode,
  });
};
