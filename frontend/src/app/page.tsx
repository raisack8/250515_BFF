'use client';

import Link from 'next/link';
import { useAuth } from '@/lib/auth';

export default function Home() {
  const { isAuthenticated, isLoading } = useAuth();

  return (
    <div className="flex flex-col items-center justify-center min-h-screen py-2">
      <main className="flex flex-col items-center justify-center flex-1 w-full px-20 text-center">
        <h1 className="text-6xl font-bold">
          Welcome to{' '}
          <span className="text-blue-600">
            BFF Architecture Demo
          </span>
        </h1>

        <p className="mt-3 text-2xl">
          Backend For Frontend pattern with FastAPI and Next.js
        </p>

        <div className="flex flex-wrap items-center justify-around max-w-4xl mt-6 sm:w-full">
          {isLoading ? (
            <p className="mt-4 text-xl">Loading authentication status...</p>
          ) : isAuthenticated ? (
            <Link
              href="/dashboard"
              className="p-6 mt-6 text-left border w-96 rounded-xl hover:text-blue-600 focus:text-blue-600"
            >
              <h3 className="text-2xl font-bold">Dashboard &rarr;</h3>
              <p className="mt-4 text-xl">
                Go to your dashboard to see your data
              </p>
            </Link>
          ) : (
            <Link
              href="/login"
              className="p-6 mt-6 text-left border w-96 rounded-xl hover:text-blue-600 focus:text-blue-600"
            >
              <h3 className="text-2xl font-bold">Login &rarr;</h3>
              <p className="mt-4 text-xl">
                Login to access protected resources
              </p>
            </Link>
          )}

          <a
            href="https://github.com/your-username/bff-architecture-demo"
            className="p-6 mt-6 text-left border w-96 rounded-xl hover:text-blue-600 focus:text-blue-600"
            target="_blank"
            rel="noopener noreferrer"
          >
            <h3 className="text-2xl font-bold">Documentation &rarr;</h3>
            <p className="mt-4 text-xl">
              Learn about the BFF architecture and how it works
            </p>
          </a>
        </div>
      </main>

      <footer className="flex items-center justify-center w-full h-24 border-t">
        <p>
          BFF Architecture Demo - {new Date().getFullYear()}
        </p>
      </footer>
    </div>
  );
}
