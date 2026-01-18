import withPWAInit from '@ducanh2912/next-pwa';

const withPWA = withPWAInit({
  dest: 'public',
  register: true,
  skipWaiting: true,
  disable: process.env.NODE_ENV === 'development',
  fallbacks: {
    document: '/offline',
  },
  workboxOptions: {
    runtimeCaching: [
    // Cache static assets
    {
      urlPattern: /^https:\/\/fonts\.(?:gstatic|googleapis)\.com\/.*/i,
      handler: 'CacheFirst',
      options: {
        cacheName: 'google-fonts',
        expiration: {
          maxEntries: 10,
          maxAgeSeconds: 365 * 24 * 60 * 60 // 1 year
        }
      }
    },
    // Cache images
    {
      urlPattern: /\.(?:jpg|jpeg|gif|png|svg|ico|webp)$/i,
      handler: 'StaleWhileRevalidate',
      options: {
        cacheName: 'static-images',
        expiration: {
          maxEntries: 100,
          maxAgeSeconds: 7 * 24 * 60 * 60 // 7 days
        }
      }
    },
    // Cache CSS and JS
    {
      urlPattern: /\.(?:js|css)$/i,
      handler: 'StaleWhileRevalidate',
      options: {
        cacheName: 'static-resources',
        expiration: {
          maxEntries: 50,
          maxAgeSeconds: 24 * 60 * 60 // 24 hours
        }
      }
    },
    // Cache API calls for citizen pages - User Profile
    {
      urlPattern: /\/api\/v1\/profile\/me$/i,
      handler: 'NetworkFirst',
      options: {
        cacheName: 'user-profile',
        expiration: {
          maxEntries: 1,
          maxAgeSeconds: 24 * 60 * 60 // 24 hours
        },
        networkTimeoutSeconds: 10
      }
    },
    // Cache API calls - Hazard reports list
    {
      urlPattern: /\/api\/v1\/hazards(?:\?.*)?$/i,
      handler: 'NetworkFirst',
      options: {
        cacheName: 'hazard-reports',
        expiration: {
          maxEntries: 50,
          maxAgeSeconds: 15 * 60 // 15 minutes
        },
        networkTimeoutSeconds: 10
      }
    },
    // Cache API calls - My Reports
    {
      urlPattern: /\/api\/v1\/hazards\/my-reports/i,
      handler: 'NetworkFirst',
      options: {
        cacheName: 'my-reports',
        expiration: {
          maxEntries: 100,
          maxAgeSeconds: 30 * 60 // 30 minutes
        },
        networkTimeoutSeconds: 10
      }
    },
    // Cache API calls - Active Alerts
    {
      urlPattern: /\/api\/v1\/monitoring\/alerts\/active/i,
      handler: 'NetworkFirst',
      options: {
        cacheName: 'active-alerts',
        expiration: {
          maxEntries: 20,
          maxAgeSeconds: 5 * 60 // 5 minutes
        },
        networkTimeoutSeconds: 5
      }
    },
    // Cache API calls - Notifications
    {
      urlPattern: /\/api\/v1\/notifications/i,
      handler: 'NetworkFirst',
      options: {
        cacheName: 'notifications',
        expiration: {
          maxEntries: 50,
          maxAgeSeconds: 10 * 60 // 10 minutes
        },
        networkTimeoutSeconds: 10
      }
    },
    // Cache API calls - Events
    {
      urlPattern: /\/api\/v1\/events/i,
      handler: 'StaleWhileRevalidate',
      options: {
        cacheName: 'events',
        expiration: {
          maxEntries: 100,
          maxAgeSeconds: 60 * 60 // 1 hour
        }
      }
    },
    // Cache API calls - Communities
    {
      urlPattern: /\/api\/v1\/communities/i,
      handler: 'StaleWhileRevalidate',
      options: {
        cacheName: 'communities',
        expiration: {
          maxEntries: 100,
          maxAgeSeconds: 60 * 60 // 1 hour
        }
      }
    },
    // Cache Map Tiles (OpenStreetMap)
    {
      urlPattern: /^https:\/\/[abc]\.tile\.openstreetmap\.org\/.*/i,
      handler: 'CacheFirst',
      options: {
        cacheName: 'map-tiles',
        expiration: {
          maxEntries: 500,
          maxAgeSeconds: 7 * 24 * 60 * 60 // 7 days
        }
      }
    },
    // Exclude Authority/Analyst/Admin API calls from caching
    {
      urlPattern: /\/api\/v1\/(authority|analyst|admin)\/.*/i,
      handler: 'NetworkOnly'
    }
  ]}
});

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
};

export default withPWA(nextConfig);
