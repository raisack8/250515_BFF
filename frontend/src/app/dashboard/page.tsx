'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import Link from 'next/link';

// BFF API URL
const BFF_API_URL = 'http://localhost:8001';

interface Item {
  id: number;
  name: string;
  description: string | null;
}

export default function Dashboard() {
  const { user, isLoading, isAuthenticated, logout } = useAuth();
  const [items, setItems] = useState<Item[]>([]);
  const [itemsLoading, setItemsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    // Redirect to login if not authenticated
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, isLoading, router]);

  useEffect(() => {
    // Fetch items from the BFF API
    const fetchItems = async () => {
      if (!isAuthenticated) return;

      setItemsLoading(true);
      try {
        const response = await fetch(`${BFF_API_URL}/api/items`, {
          method: 'GET',
          credentials: 'include', // Important for cookies
          headers: {
            'Content-Type': 'application/json',
          },
        });

        if (response.ok) {
          const data = await response.json();
          setItems(data);
        } else {
          setError('Failed to fetch items');
        }
      } catch (err) {
        console.error('Error fetching items:', err);
        setError('An error occurred while fetching items');
      } finally {
        setItemsLoading(false);
      }
    };

    if (isAuthenticated) {
      fetchItems();
    }
  }, [isAuthenticated]);

  const handleLogout = async () => {
    await logout();
    router.push('/login');
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-xl">Loading...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null; // Will redirect in useEffect
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <nav className="bg-white shadow">
        <div className="px-4 mx-auto max-w-7xl sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <Link href="/" className="text-xl font-bold text-gray-800">
                BFF Demo
              </Link>
            </div>
            <div className="flex items-center">
              <span className="mr-4 text-sm text-gray-600">
                Welcome, <span className="font-bold">{user?.username}</span>
              </span>
              <button
                onClick={handleLogout}
                className="px-3 py-1 text-sm text-white bg-red-600 rounded hover:bg-red-700"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>

      <main className="py-8">
        <div className="px-4 mx-auto max-w-7xl sm:px-6 lg:px-8">
          <div className="p-6 bg-white rounded-lg shadow">
            <h1 className="text-2xl font-bold text-gray-800">Dashboard</h1>
            <div className="mt-4 p-4 bg-blue-50 rounded-md">
              <h2 className="text-xl font-semibold text-blue-700">User Information</h2>
              <p className="mt-2 text-gray-600">User ID: {user?.user_id}</p>
              <p className="text-gray-600">Username: {user?.username}</p>
              <p className="text-gray-600">
                Roles: {user?.roles.join(', ')}
              </p>
            </div>

            <div className="mt-8">
              <h2 className="text-xl font-semibold text-gray-800">Items</h2>
              {itemsLoading ? (
                <p className="mt-4 text-gray-600">Loading items...</p>
              ) : error ? (
                <p className="mt-4 text-red-600">{error}</p>
              ) : (
                <div className="mt-4 overflow-hidden border border-gray-200 rounded-md shadow-sm">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-xs font-medium tracking-wider text-left text-gray-500 uppercase">
                          ID
                        </th>
                        <th className="px-6 py-3 text-xs font-medium tracking-wider text-left text-gray-500 uppercase">
                          Name
                        </th>
                        <th className="px-6 py-3 text-xs font-medium tracking-wider text-left text-gray-500 uppercase">
                          Description
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {items.map((item) => (
                        <tr key={item.id}>
                          <td className="px-6 py-4 text-sm text-gray-500 whitespace-nowrap">
                            {item.id}
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-900 whitespace-nowrap">
                            {item.name}
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-500 whitespace-nowrap">
                            {item.description}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
} 