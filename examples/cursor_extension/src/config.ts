import * as vscode from 'vscode';

// API Endpoints
export const API_ENDPOINTS = {
    EPISODIC_MEMORY: '/memory/get_episodic_memory',
    PROFILE_MEMORY: '/memory/get_profile_memory',
    HEALTH: '/health',
    DEBUG: '/debug',
    LOGIN: '/auth/login',
    LOGOUT: '/auth/logout'
} as const;

export const MCP_NAME = 'MemMachine';

export function getApiBaseUrl(): string {
    return vscode.workspace.getConfiguration('memmachine').get('apiBaseUrl', 'http://18.116.238.202:8001');
}

export function getMcpUrl(): string {
    return vscode.workspace.getConfiguration('memmachine').get('mcpUrl', 'http://18.116.238.202:8001/mcp/');
}

export function getAuthToken(): string {
    return vscode.workspace.getConfiguration().get('authToken', 'your-auth-token-here');
}

export const MCP_URL = getMcpUrl();
export const API_BASE_URL = getApiBaseUrl();

export const AUTH_TOKEN = getAuthToken();



