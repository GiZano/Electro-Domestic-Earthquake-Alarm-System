import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../client';
import { usePreferencesStore } from '../../store/usePreferencesStore';

interface SensorStatisticsResponse {
  sensor_id: number;
  total_readings: number;
}

const fetchSensorStatistics = async (id: number): Promise<SensorStatisticsResponse> => {
  const { data } = await apiClient.get(`/sensors/${id}/statistics`);
  return data;
};

export const useSensorStatistics = (id: number) => {
  const isOfflineMode = usePreferencesStore((state) => state.isOfflineMode);

  return useQuery({
    queryKey: ['sensorStatistics', id], 
    queryFn: () => fetchSensorStatistics(id),
    staleTime: 5000, 
    retry: 2, 
    enabled: !isOfflineMode,
  });
};