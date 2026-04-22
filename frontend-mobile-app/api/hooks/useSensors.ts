import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../client';

// Define the shape of the data we expect from the backend
interface SensorStatisticsResponse {
  sensor_id: number;
  total_readings: number;
}

// The actual Axios fetcher function
const fetchSensorStatistics = async (id: number): Promise<SensorStatisticsResponse> => {
  const { data } = await apiClient.get(`/sensors/${id}/statistics`);
  return data;
};

// The Custom Hook exported to your components
export const useSensorStatistics = (id: number) => {
  return useQuery({
    queryKey: ['sensorStatistics', id], // Unique cache key
    queryFn: () => fetchSensorStatistics(id),
    staleTime: 5000, // Data is considered "fresh" for 5 seconds
    retry: 2, // Automatically retry failed requests twice (great for spotty connections)
  });
};