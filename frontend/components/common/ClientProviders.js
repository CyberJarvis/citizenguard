'use client';

import dynamic from 'next/dynamic';

// Dynamic import service worker provider (avoid SSR issues)
const ServiceWorkerProvider = dynamic(
  () => import('./ServiceWorkerProvider'),
  { ssr: false }
);

/**
 * Client-side providers wrapper
 * Includes service worker registration and other client-only providers
 */
const ClientProviders = ({ children }) => {
  return (
    <ServiceWorkerProvider>
      {children}
    </ServiceWorkerProvider>
  );
};

export default ClientProviders;
