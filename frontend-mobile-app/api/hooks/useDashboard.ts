import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../client';

export const useSensors = () => {
  return useQuery({
    queryKey: ['sensors'],
    queryFn: async () => {
      const { data } = await apiClient.get('/misurators/');
      return data;
    },
    refetchInterval: 10000, // Update sensor status every 10 seconds
  });
};

export const useRecentReadings = () => {
  return useQuery({
    queryKey: ['recentReadings'],
    queryFn: async () => {
      const { data } = await apiClient.get('/misurations/?limit=50');
      // Reverse the data so it reads left-to-right chronologically on the chart
      return data.reverse(); 
    },
    refetchInterval: 2000, // Fast 2-second refresh for the seismograph
  });
};