# Sentinel Web Dashboard

Modern React web application for the Sentinel AI Security SaaS platform.

## Technology Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool & dev server
- **Tailwind CSS** - Utility-first CSS framework
- **Shadcn/ui** - Beautiful, customizable UI components
- **React Router** - Client-side routing
- **React Query** - Server state management
- **Zustand** - Global state management
- **React Hook Form** - Form handling
- **Zod** - Schema validation
- **Axios** - HTTP client
- **Lucide React** - Icon library

## Project Structure

```
web/
├── src/
│   ├── api/              # API client & endpoints
│   │   ├── client.ts     # Axios instance with interceptors
│   │   ├── auth.ts       # Authentication API
│   │   └── types.ts      # TypeScript interfaces
│   ├── components/       # React components
│   │   ├── ui/           # Shadcn/ui components
│   │   └── ProtectedRoute.tsx
│   ├── hooks/            # Custom React hooks
│   │   └── useAuth.ts    # Authentication hooks
│   ├── lib/              # Utilities
│   │   ├── utils.ts      # cn() helper
│   │   └── query-client.ts
│   ├── pages/            # Page components
│   │   ├── LoginPage.tsx
│   │   ├── RegisterPage.tsx
│   │   └── DashboardPage.tsx
│   ├── stores/           # Zustand stores
│   │   └── authStore.ts
│   ├── App.tsx           # Router setup
│   ├── main.tsx          # Entry point
│   └── index.css         # Global styles
├── public/               # Static assets
├── .env.example          # Environment variables template
├── package.json
├── tsconfig.json
├── tailwind.config.js
├── vite.config.ts
└── README.md
```

## Getting Started

### Prerequisites

- Node.js 18+ (currently using v18.19.1)
- npm 9+

### Installation

1. **Navigate to web directory:**
   ```bash
   cd web
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Create environment file:**
   ```bash
   cp .env.example .env
   ```

4. **Update `.env` with your API URL:**
   ```
   VITE_API_BASE_URL=http://localhost:8000
   ```

### Development

**Start development server:**
```bash
npm run dev
```

The app will be available at `http://localhost:5173`

**Build for production:**
```bash
npm run build
```

**Preview production build:**
```bash
npm run preview
```

## Features

### Authentication

- **User Registration** - Create new account with organization
- **Login** - Email/password authentication with JWT tokens
- **Auto Token Refresh** - Automatic access token renewal
- **Protected Routes** - Redirect to login if not authenticated
- **Persistent Sessions** - Remember user across page reloads

### Dashboard (Coming Soon)

- Real-time threat monitoring
- Risk score visualization
- Threat distribution charts
- Recent activity feed
- Policy management
- Audit log viewer

## API Integration

The frontend connects to the Sentinel API backend:

**Base URL:** `http://localhost:8000` (configurable via `VITE_API_BASE_URL`)

**Endpoints Used:**
- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `POST /auth/refresh` - Token refresh
- `GET /auth/me` - Current user info

**Authentication:**
- Access tokens stored in localStorage
- Automatic Bearer token injection
- Auto-refresh on 401 errors
- Redirect to login on auth failure

## UI Components

Built with Shadcn/ui components:

- **Button** - Various variants (default, destructive, outline, etc.)
- **Input** - Text input with validation states
- **Label** - Form labels
- **Card** - Content containers
- More components coming soon...

## State Management

**React Query** for server state:
- Automatic caching
- Background refetching
- Optimistic updates
- Error handling

**Zustand** for global state:
- User authentication state
- Persistent storage
- Simple API

## Forms

**React Hook Form + Zod:**
- Type-safe validation
- Real-time error messages
- Clean syntax
- Performance optimized

Example:
```typescript
const loginSchema = z.object({
  email: z.string().email('Invalid email'),
  password: z.string().min(1, 'Password required'),
});

const { register, handleSubmit, formState: { errors } } = useForm({
  resolver: zodResolver(loginSchema),
});
```

## Routing

**React Router** with protected routes:

```
/ → /dashboard (redirect)
/login → Login page (public)
/register → Register page (public)
/dashboard → Dashboard (protected)
```

Protected routes check for authentication and redirect to `/login` if needed.

## Styling

**Tailwind CSS** with custom theme:

- Light/dark mode support
- CSS custom properties for theming
- Utility-first approach
- Responsive design

**Theme colors:**
- Primary, secondary, destructive, muted, accent
- Automatically adjust for dark mode

## Development Tips

**Path Aliases:**
Use `@/` instead of relative imports:
```typescript
import { Button } from '@/components/ui/button';
import { useAuth } from '@/hooks/useAuth';
```

**Type Safety:**
All API responses are typed:
```typescript
const { data } = useQuery<CurrentUser>(...);
```

**Hot Module Replacement (HMR):**
Changes appear instantly without full page reload.

## Troubleshooting

**Node version warning:**
- App works with Node 18, but Vite recommends 20+
- No functionality issues

**API connection errors:**
- Check backend is running: `python -m sentinel.saas.server`
- Verify `VITE_API_BASE_URL` in `.env`
- Check CORS settings on backend

**Build errors:**
- Clear node_modules: `rm -rf node_modules && npm install`
- Clear Vite cache: `rm -rf node_modules/.vite`

## Next Steps

**Phase 2 Remaining Tasks:**

Week 3-4: Dashboard UI
- Metrics cards with real data
- Risk score over time chart
- Threat distribution chart
- Live threat feed (WebSocket)

Week 5-6: Policy Management
- Policies list page
- Policy editor form
- Policy testing interface
- Deploy/rollback controls

Week 7-8: Audit Logs & Settings
- Audit logs viewer
- Organization settings
- User management
- API key management

Week 9-10: Polish & Testing
- Mobile responsiveness
- E2E tests
- Accessibility audit
- Performance optimization

## License

MIT
