import { toast } from 'react-hot-toast';

/**
 * カスタムAPIエラークラス
 */
export class ApiError extends Error {
  statusCode: number;
  errorData: any;
  errorCode?: string;

  constructor(statusCode: number, message: string, errorData?: any) {
    super(message);
    this.name = 'ApiError';
    this.statusCode = statusCode;
    this.errorData = errorData;
    this.errorCode = errorData?.error_code;
  }
}

/**
 * エラーに応じた通知を表示する
 */
export function showErrorNotification(message: string) {
  toast.error(message, {
    duration: 5000,
    position: 'top-center',
  });
}

/**
 * エラーハンドリング機能付きのフェッチ関数
 */
export async function fetchWithErrorHandling(url: string, options: RequestInit = {}) {
  try {
    const response = await fetch(url, {
      ...options,
      credentials: 'include', // Cookieを含める
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
    
    // レスポンスがJSONかどうかを確認
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      const data = await response.json();
      
      // エラーレスポンスの処理
      if (!response.ok) {
        // BFFからのエラーレスポンスを処理
        const errorMessage = data.message || '不明なエラーが発生しました';
        
        if (data.error_code) {
          switch (data.error_code) {
            case 'BACKEND_CONNECTION_ERROR':
              showErrorNotification('バックエンドサービスに接続できません。しばらくしてからもう一度お試しください。');
              break;
            case 'BACKEND_TIMEOUT':
              showErrorNotification('サーバーの応答に時間がかかっています。しばらくしてからもう一度お試しください。');
              break;
            case 'CIRCUIT_OPEN':
              showErrorNotification('サービスは現在一時的に利用できません。メンテナンス中の可能性があります。');
              break;
            case 'HTTP_401':
              showErrorNotification('セッションが切れました。再度ログインしてください。');
              break;
            default:
              showErrorNotification(errorMessage);
          }
        } else {
          showErrorNotification(errorMessage);
        }
        
        throw new ApiError(response.status, errorMessage, data);
      }
      
      return data;
    } else {
      // JSON以外のレスポンス処理
      if (!response.ok) {
        const errorMessage = `エラーが発生しました (${response.status})`;
        showErrorNotification(errorMessage);
        throw new ApiError(response.status, errorMessage);
      }
      return response;
    }
  } catch (error) {
    // ネットワークエラーなど
    if (error instanceof ApiError) {
      // 既に処理済みの場合は再スロー
      throw error;
    } else if (error instanceof TypeError && error.message.includes('fetch')) {
      // ネットワーク接続エラー
      const errorMessage = 'サーバーに接続できません。インターネット接続を確認してください。';
      showErrorNotification(errorMessage);
      throw new ApiError(0, errorMessage);
    } else {
      // その他の予期しないエラー
      showErrorNotification('予期しないエラーが発生しました');
      throw error;
    }
  }
}

/**
 * API呼び出し用のラッパー関数
 */
export const api = {
  get: (path: string, options?: RequestInit) => 
    fetchWithErrorHandling(`/api/${path}`, { ...options, method: 'GET' }),
  
  post: (path: string, data?: any, options?: RequestInit) => 
    fetchWithErrorHandling(`/api/${path}`, { 
      ...options, 
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    }),
  
  put: (path: string, data?: any, options?: RequestInit) => 
    fetchWithErrorHandling(`/api/${path}`, { 
      ...options, 
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    }),
  
  delete: (path: string, options?: RequestInit) => 
    fetchWithErrorHandling(`/api/${path}`, { ...options, method: 'DELETE' }),
}; 