import * as https from 'https';
import * as http from 'http';
import { API_BASE_URL, API_ENDPOINTS } from './config';

export interface ApiResponse<T = any> {
    data: T;
    status: number;
    statusText: string;
}

export interface ApiError {
    message: string;
    status?: number;
    statusText?: string;
}

export class ApiClient {
    private baseUrl: string;

    constructor(baseUrl: string = API_BASE_URL) {
        this.baseUrl = baseUrl;
    }

    /**
     * Generic HTTP request method
     */
    private async request<T = any>(
        endpoint: string,
        options: {
            method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
            headers?: Record<string, string>;
            body?: any;
        } = {}
    ): Promise<ApiResponse<T>> {
        const { method = 'GET', headers = {}, body } = options;
        
        return new Promise((resolve, reject) => {
            const url = new URL(endpoint, this.baseUrl);
            
            const requestOptions = {
                hostname: url.hostname,
                port: url.port || (url.protocol === 'https:' ? 443 : 80),
                path: url.pathname + url.search,
                method,
                headers: {
                    'Content-Type': 'application/json',
                    ...headers
                }
            };

            const protocol = url.protocol === 'https:' ? https : http;
            
            const req = protocol.request(requestOptions, (res) => {
                let data = '';
                
                res.on('data', (chunk) => {
                    data += chunk;
                });
                
                res.on('end', () => {
                    try {
                        const jsonData = data ? JSON.parse(data) : {};
                        resolve({
                            data: jsonData,
                            status: res.statusCode || 200,
                            statusText: res.statusMessage || 'OK'
                        });
                    } catch (error) {
                        reject({
                            message: 'Failed to parse response: ' + data,
                            status: res.statusCode,
                            statusText: res.statusMessage
                        });
                    }
                });
            });

            req.on('error', (error) => {
                reject({
                    message: 'Request failed: ' + error.message
                });
            });

            if (body) {
                req.write(JSON.stringify(body));
            }

            req.end();
        });
    }

    /**
     * GET request
     */
    async get<T = any>(endpoint: string, headers?: Record<string, string>): Promise<ApiResponse<T>> {
        return this.request<T>(endpoint, { method: 'GET', headers });
    }

    /**
     * POST request
     */
    async post<T = any>(endpoint: string, body?: any, headers?: Record<string, string>): Promise<ApiResponse<T>> {
        return this.request<T>(endpoint, { method: 'POST', headers, body });
    }

    /**
     * PUT request
     */
    async put<T = any>(endpoint: string, body?: any, headers?: Record<string, string>): Promise<ApiResponse<T>> {
        return this.request<T>(endpoint, { method: 'PUT', headers, body });
    }

    /**
     * DELETE request
     */
    async delete<T = any>(endpoint: string, headers?: Record<string, string>): Promise<ApiResponse<T>> {
        return this.request<T>(endpoint, { method: 'DELETE', headers });
    }

    // Specific API methods
    async getEpisodicMemory(): Promise<ApiResponse> {
        return this.get(API_ENDPOINTS.EPISODIC_MEMORY);
    }

    async getProfileMemory(): Promise<ApiResponse> {
        return this.get(API_ENDPOINTS.PROFILE_MEMORY);
    }

    async healthCheck(): Promise<ApiResponse> {
        return this.get(API_ENDPOINTS.HEALTH);
    }

    async getDebugInfo(): Promise<ApiResponse> {
        return this.get(API_ENDPOINTS.DEBUG);
    }

    async login(credentials: { username: string; password: string }): Promise<ApiResponse> {
        return this.post(API_ENDPOINTS.LOGIN, credentials);
    }

    async logout(): Promise<ApiResponse> {
        return this.post(API_ENDPOINTS.LOGOUT);
    }
}

// Export a default instance
export const apiClient = new ApiClient();
