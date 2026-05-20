import axios from 'axios';
import { API_BASE_URL, IOT_API_KEY } from '../constants/config'; 

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': IOT_API_KEY 
  },
});