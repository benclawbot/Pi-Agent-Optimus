# Node.js API Scaffold

## Setup

```bash
mkdir src && npm init -y
npm install express typescript ts-node @types/node @types/express
npx tsc --init
```

## Key Files

```
src/
├── index.ts              # Entry point
├── routes/               # Express routes
│   └── example.ts
├── middleware/           # Custom middleware
│   └── auth.ts
├── services/             # Business logic
│   └── example.ts
├── types/                # TypeScript types
│   └── index.ts
└── utils/                # Helpers
    └── logger.ts
```

## tsconfig.json

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true
  }
}
```

## Scripts (package.json)

```json
{
  "scripts": {
    "dev": "tsx watch src/index.ts",
    "build": "tsc",
    "start": "node dist/index.js",
    "test": "vitest"
  }
}
```

## Structure Pattern

### index.ts
```ts
import express from "express";
import { exampleRouter } from "./routes/example";

const app = express();
app.use(express.json());
app.use("/api/example", exampleRouter);

app.listen(3000, () => {
  console.log("Server running on port 3000");
});
```

### Route Pattern
```ts
import { Router } from "express";

export const exampleRouter = Router();

exampleRouter.get("/", (req, res) => {
  res.json({ message: "Hello" });
});

exampleRouter.post("/", async (req, res) => {
  const { data } = req.body;
  // process...
  res.status(201).json({ data });
});
```

## Common Middleware

```ts
// Error handler
app.use((err: Error, req: express.Request, res: express.Response, next: express.NextFunction) => {
  console.error(err.stack);
  res.status(500).json({ error: "Internal server error" });
});
```

## Env Pattern (.env)

```
PORT=3000
NODE_ENV=development
DATABASE_URL=
```