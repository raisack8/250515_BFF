// Authentication related types and utilities
import { useState, useEffect, createContext, useContext, ReactNode } from 'react';
import { fetchWithErrorHandling, ApiError } from './api';

// BFF API URL
const BFF_API_URL = 'http://localhost:8001';

export interface User {
  user_id: string;
  username: string;
  roles: string[];
}

// BFFからのエラーレスポンスの型定義
export interface BffErrorResponse {
  status_code: number;
  message: string;
  details?: any;
  error_code?: string;
}

export interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  error: string | null;
}

// Create auth context
export const AuthContext = createContext<AuthContextType>({
  user: null,
  isLoading: true,
  isAuthenticated: false,
  login: async () => {},
  logout: async () => {},
  error: null,
});

// Auth provider props
export interface AuthProviderProps {
  children: ReactNode;
}

// Function to check if user is authenticated
export const checkAuth = async (): Promise<User | null> => {
  try {
    const user = await fetchWithErrorHandling(`${BFF_API_URL}/auth/me`);
    return user;
  } catch (error) {
    // 401エラーは通常のフローとして扱う（未認証）
    if (error instanceof ApiError && error.statusCode === 401) {
      return null;
    }
    // その他のエラーはコンソールに記録
    console.error('Auth check error:', error);
    return null;
  }
};

// Login function
export const loginUser = async (username: string, password: string): Promise<User | null> => {
  try {
    const data = await fetchWithErrorHandling(`${BFF_API_URL}/auth/login`, {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
    
    return data.user;
  } catch (error) {
    console.error('Login error:', error);
    throw error;
  }
};

// Logout function
export const logoutUser = async (): Promise<void> => {
  try {
    await fetchWithErrorHandling(`${BFF_API_URL}/auth/logout`);
  } catch (error) {
    // ログアウト失敗はエラーとして扱わない（セッションが既に切れている可能性）
    console.warn('Logout error (non-critical):', error);
  }
};

// Hook to use auth context
export const useAuth = () => useContext(AuthContext); 