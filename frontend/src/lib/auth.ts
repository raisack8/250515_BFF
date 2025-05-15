// Authentication related types and utilities
import { useState, useEffect, createContext, useContext, ReactNode } from 'react';

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
    const response = await fetch(`${BFF_API_URL}/auth/me`, {
      method: 'GET',
      credentials: 'include', // Important for cookies
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (response.ok) {
      const user = await response.json();
      return user;
    }
    
    return null;
  } catch (error) {
    console.error('Auth check error:', error);
    return null;
  }
};

// Login function
export const loginUser = async (username: string, password: string): Promise<User | null> => {
  try {
    const response = await fetch(`${BFF_API_URL}/auth/login`, {
      method: 'POST',
      credentials: 'include', // Important for cookies
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username, password }),
    });

    if (response.ok) {
      const data = await response.json();
      return data.user;
    }
    
    // エラーレスポンスを処理
    const errorData = await response.json() as BffErrorResponse;
    throw new Error(errorData.message || 'ログインに失敗しました');
  } catch (error) {
    console.error('Login error:', error);
    throw error;
  }
};

// Logout function
export const logoutUser = async (): Promise<void> => {
  try {
    const response = await fetch(`${BFF_API_URL}/auth/logout`, {
      method: 'GET',
      credentials: 'include', // Important for cookies
    });
    
    if (!response.ok) {
      // エラーレスポンスを処理
      try {
        const errorData = await response.json() as BffErrorResponse;
        console.error('Logout error:', errorData);
      } catch (e) {
        console.error('Logout failed:', response.status, response.statusText);
      }
    }
  } catch (error) {
    console.error('Logout error:', error);
  }
};

// Hook to use auth context
export const useAuth = () => useContext(AuthContext); 