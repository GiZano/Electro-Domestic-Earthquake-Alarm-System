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