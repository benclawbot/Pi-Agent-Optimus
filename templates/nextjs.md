# Next.js App Scaffold

## Setup

```bash
npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm
```

## Key Files

```
src/
├── app/                    # App Router pages
│   ├── layout.tsx         # Root layout
│   ├── page.tsx           # Home page
│   └── globals.css        # Global styles
├── components/            # Reusable components
│   ├── ui/               # Base UI components
│   └── layout/           # Layout components
├── lib/                   # Utilities
│   └── utils.ts          # Helper functions
└── types/                 # TypeScript types
```

## Scripts (package.json)

```json
{
  "dev": "next dev",
  "build": "next build",
  "start": "next start",
  "lint": "next lint"
}
```

## Env Pattern (.env.local)

```
# Database
DATABASE_URL=

# Auth
NEXTAUTH_SECRET=
NEXTAUTH_URL=

# API Keys
OPENAI_API_KEY=
```

## Common Patterns

### Server Component (default)
```tsx
export default async function Page() {
  const data = await fetchData();
  return <div>{data}</div>;
}
```

### Client Component
```tsx
"use client";
export function Component() {
  const [state, setState] = useState();
  return <button onClick={() => setState(!state)}>...</button>;
}
```

### API Route (app/api/route.ts)
```ts
export async function POST(req: Request) {
  const body = await req.json();
  // process...
  return Response.json({ data });
}
```