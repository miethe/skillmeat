# SkillMeat Web Interface

Next.js 15 App Router web interface for SkillMeat collection manager.

## Features

- Modern React 19 with Next.js 15 App Router
- Tailwind CSS for styling
- shadcn/ui component library
- TypeScript with strict mode
- ESLint and Prettier configured
- Responsive design with mobile-first approach
- Integration with FastAPI backend

## Prerequisites

- Node.js >= 18.18.0
- pnpm >= 8.0.0

## Getting Started

### Install Dependencies

```bash
pnpm install
```

### Development Server

```bash
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser to see the application.

### Build for Production

```bash
pnpm build
```

### Start Production Server

```bash
pnpm start
```

## Available Scripts

- `pnpm dev` - Start development server with hot reload
- `pnpm build` - Build production bundle
- `pnpm start` - Start production server
- `pnpm lint` - Run ESLint
- `pnpm format` - Format code with Prettier
- `pnpm format:check` - Check code formatting
- `pnpm type-check` - Run TypeScript type checking

## Environment Variables

Copy `.env.example` to `.env.local` and configure:

```bash
cp .env.example .env.local
```

### Available Variables

- `NEXT_PUBLIC_API_URL` - FastAPI backend URL (default: http://localhost:8000)
- `NEXT_PUBLIC_APP_NAME` - Application name
- `NEXT_PUBLIC_APP_VERSION` - Application version

## Project Structure

```
skillmeat/web/
├── app/                    # Next.js App Router pages
│   ├── layout.tsx         # Root layout with header and navigation
│   ├── page.tsx           # Dashboard home page
│   └── globals.css        # Global styles and Tailwind CSS
├── components/            # React components
│   ├── ui/               # shadcn/ui components
│   ├── header.tsx        # Header component
│   └── navigation.tsx    # Navigation sidebar
├── lib/                   # Utility functions
│   └── utils.ts          # cn() for className merging
├── public/               # Static assets
└── package.json          # Dependencies and scripts
```

## Integration with Backend

The web interface connects to the FastAPI backend running at `http://localhost:8000` (configurable via `NEXT_PUBLIC_API_URL`).

API requests are proxied through Next.js using the `/api/*` route prefix.

## Tech Stack

- **Framework**: Next.js 15 (App Router)
- **UI Library**: React 19
- **Styling**: Tailwind CSS 3.4
- **Components**: shadcn/ui
- **Icons**: Lucide React
- **Language**: TypeScript 5.6 (strict mode)
- **Code Quality**: ESLint, Prettier
- **Package Manager**: pnpm 8.15

## Accessibility

All components follow WCAG 2.1 AA standards:

- Semantic HTML
- Keyboard navigation support
- ARIA labels and roles
- Color contrast compliance
- Screen reader compatibility

## Performance

- Server-side rendering (SSR) with Next.js
- Optimized bundle splitting
- Image optimization
- Core Web Vitals monitoring
