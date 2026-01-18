# CoastGuardian Frontend

Modern, responsive frontend application for the CoastGuardian Ocean Hazard Reporting Platform built with Next.js 16, React 19, and Tailwind CSS 4.

## ✨ Features

### Authentication System

- ✅ **Email/Password Authentication** - Secure login and signup with password validation
- ✅ **Google OAuth 2.0** - One-click social login
- ✅ **JWT Token Management** - Automatic token refresh and session handling
- ✅ **Protected Routes** - Route guards for authenticated pages
- ✅ **Persistent Sessions** - State persisted in sessionStorage
- ✅ **Form Validation** - Real-time validation with Zod schemas

### UI/UX

- ✅ **Modern Design** - Clean, professional interface with Poppins font
- ✅ **Responsive Layout** - Mobile-first design that works on all devices
- ✅ **Smooth Animations** - Polished transitions and hover effects
- ✅ **Toast Notifications** - Real-time feedback for user actions
- ✅ **Loading States** - Spinners for better UX
- ✅ **Gradient Themes** - Ocean-inspired color scheme

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ installed
- Backend API running on `http://localhost:8000`

### Installation

1. **Install dependencies**:

   ```bash
   npm install
   ```

2. **Start development server**:

   ```bash
   npm run dev
   ```

3. **Open browser**:
   Navigate to [http://localhost:3000](http://localhost:3000)

The environment variables are already configured in `.env.local`.

## 🛠️ Tech Stack

- **Framework**: Next.js 16.0.3 with App Router
- **React**: 19.2.0 (Latest)
- **Styling**: Tailwind CSS 4 (CSS-based configuration)
- **State Management**: Zustand with persistence
- **Form Handling**: React Hook Form with Zod validation
- **HTTP Client**: Axios with interceptors
- **Icons**: Lucide React
- **Notifications**: React Hot Toast

## 📁 Project Structure

```
frontend/
├── app/
│   ├── auth/google/callback/page.js  # Google OAuth callback
│   ├── dashboard/page.js             # Protected dashboard
│   ├── login/page.js                 # Login page
│   ├── signup/page.js                # Signup page
│   ├── globals.css                   # Global styles
│   ├── layout.js                     # Root layout
│   └── page.js                       # Landing page
├── components/
│   └── ProtectedRoute.js             # Auth guard
├── context/
│   └── AuthContext.js                # Zustand auth store
├── lib/
│   └── api.js                        # Axios client
├── .env.local                        # Environment config
└── README.md
```

## 🔐 Authentication Flows

### 1. Signup

- Navigate to `/signup`
- Fill in name, email, password (must meet requirements)
- Optional: Add phone number
- Click "Create Account"
- Redirected to dashboard

### 2. Login

- Navigate to `/login`
- Enter email and password
- Click "Sign in"
- Redirected to dashboard

### 3. Google OAuth

- Click "Sign in with Google"
- Authorize with Google
- Redirected to callback, then dashboard

### 4. Logout

- Click "Logout" in dashboard
- Tokens cleared, redirected to login

## 🔧 Usage Examples

### API Integration

```javascript
import { loginWithPassword, signup, getCurrentUser } from "@/lib/api";

// Login
const { user } = await loginWithPassword("user@example.com", "password");

// Signup
const response = await signup({
  name: "John Doe",
  email: "john@example.com",
  password: "SecureP@ss123",
});

// Get current user
const user = await getCurrentUser();
```

### Auth Context

```javascript
"use client";
import useAuthStore from "@/context/AuthContext";

function MyComponent() {
  const { user, isAuthenticated, loginWithPassword } = useAuthStore();

  return (
    <div>
      {isAuthenticated ? (
        <p>Welcome, {user.name}!</p>
      ) : (
        <button onClick={() => loginWithPassword("email", "pass")}>
          Login
        </button>
      )}
    </div>
  );
}
```

### Protected Routes

```javascript
import ProtectedRoute from "@/components/ProtectedRoute";

export default function MyPage() {
  return (
    <ProtectedRoute>
      <div>Protected content</div>
    </ProtectedRoute>
  );
}
```

## 🎨 Styling

Uses Tailwind CSS 4 with custom theme in `globals.css`:

```css
@theme inline {
  --color-primary: #0ea5e9;
  --color-secondary: #06b6d4;
  --font-sans: var(--font-poppins), ui-sans-serif, system-ui;
}
```

## 📝 Available Scripts

```bash
npm run dev      # Start development server
npm run build    # Build for production
npm start        # Start production server
npm run lint     # Lint code
```

## 🔒 Security Features

- JWT tokens stored in httpOnly cookies
- CSRF protection with state parameter
- XSS prevention (React escaping)
- Password validation enforced
- Automatic token refresh
- Secure logout with token revocation

## 🐛 Troubleshooting

**Cannot connect to API**

- Ensure backend runs on `http://localhost:8000`
- Check `.env.local` has correct `NEXT_PUBLIC_API_URL`

**Google login not working**

- Verify `NEXT_PUBLIC_GOOGLE_CLIENT_ID` is set
- Check backend OAuth redirect URI

**Protected route not redirecting**

- Wrap page with `ProtectedRoute` component
- Verify auth state is initialized

## 📊 Performance

- First Load: ~150ms (Turbopack)
- Route Changes: Instant
- Token Refresh: Automatic

## 🌐 Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers

---

**Built for Smart India Hackathon 2025**
