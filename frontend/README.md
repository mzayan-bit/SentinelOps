# SentinelOps Frontend

Production-grade Next.js 15 application providing the user interface for the SentinelOps PPE Safety Monitoring platform.

## Architecture & Stack

The frontend follows a clean architecture built for high performance and strict type safety.

- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript (`strict` mode)
- **Styling**: TailwindCSS v4 with a custom Glassmorphism design system
- **State**: React Context + Custom Hooks
- **Formatting**: Prettier (`prettier-plugin-tailwindcss`)
- **Linting**: ESLint

## Directory Structure

```text
frontend/
├── src/
│   ├── app/           # Next.js App Router pages and layouts
│   ├── components/    # Reusable UI elements (Layout, Cards, Tiles)
│   ├── config/        # Static app configuration (Navigation, Constants)
│   ├── hooks/         # Custom React hooks (API polling, WebSocket, Debounce)
│   ├── lib/           # Core utilities (Typed Fetch Client, Env Validation)
│   ├── stores/        # Global state contexts (Camera, Alerts, Theme)
│   └── types/         # TypeScript definitions mirroring backend Pydantic models
├── public/            # Static assets
└── .env.local         # Environment variables (API/WS URLs)
```

## Getting Started

1. **Install Dependencies**

   ```bash
   npm install
   ```

2. **Environment Variables**
   Copy the example environment file:

   ```bash
   cp .env.local.example .env.local
   ```

   Ensure `NEXT_PUBLIC_API_URL` points to your running FastAPI backend.

3. **Development Server**
   ```bash
   npm run dev
   ```
   The application will be available at [http://localhost:3000](http://localhost:3000).

## Code Quality

To maintain consistency and catch errors early:

- **Format Code**: `npm run format`
- **Lint Code**: `npm run lint`
- **Check Types**: `npm run build`
