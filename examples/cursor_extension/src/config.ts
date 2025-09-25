// API Configuration
export const API_BASE_URL = 'http://18.116.238.202:8001';

// API Endpoints
export const API_ENDPOINTS = {
    EPISODIC_MEMORY: '/memory/get_episodic_memory',
    PROFILE_MEMORY: '/memory/get_profile_memory',
    HEALTH: '/health',
    DEBUG: '/debug',
    LOGIN: '/auth/login',
    LOGOUT: '/auth/logout'
} as const;
