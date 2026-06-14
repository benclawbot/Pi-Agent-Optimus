# React Component Library Scaffold

## Setup

```bash
npm init -y
npm install react react-dom typescript @types/react @types/react-dom
npm install -D vite vitest @vitest/ui
npx tsc --init
```

## Key Files

```
src/
├── components/           # Exportable components
│   ├── Button/
│   │   ├── Button.tsx
│   │   ├── Button.test.tsx
│   │   └── index.ts
│   └── index.ts         # Main export
├── hooks/                # Custom hooks
│   └── useCounter.ts
├── utils/                # Utilities
│   └── cn.ts            # classname helper
└── index.ts             # Entry point
```

## tsconfig.json

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "declaration": true,
    "declarationDir": "./dist",
    "outDir": "./dist",
    "esModuleInterop": true
  },
  "include": ["src"],
  "exclude": ["node_modules", "dist"]
}
```

## Vite Config (vite.config.ts)

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: "jsdom",
  },
});
```

## Export Pattern (src/index.ts)

```ts
export { Button } from "./components/Button";
// Add all exports here
```

## Scripts (package.json)

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "test": "vitest",
    "test:ui": "vitest --ui",
    "lint": "eslint src"
  }
}
```

## Common Patterns

### Component Pattern
```tsx
import { cn } from "../utils/cn";

interface ButtonProps {
  variant?: "primary" | "secondary";
  children: React.ReactNode;
  className?: string;
}

export function Button({ variant = "primary", children, className }: ButtonProps) {
  return (
    <button className={cn("btn", `btn-${variant}`, className)}>
      {children}
    </button>
  );
}
```

### Hook Pattern
```ts
export function useCounter(initial = 0) {
  const [count, setCount] = useState(initial);
  const increment = () => setCount(c => c + 1);
  const decrement = () => setCount(c => c - 1);
  return { count, increment, decrement };
}
```

## package.json exports (for publishing)

```json
{
  "name": "@your-org/ui",
  "main": "./dist/index.js",
  "module": "./dist/index.js",
  "types": "./dist/index.d.ts",
  "exports": {
    ".": {
      "import": "./dist/index.js",
      "types": "./dist/index.d.ts"
    }
  }
}
```