# Common Dev Server Patterns

## JavaScript/TypeScript

### Vite
```bash
npm run dev    # or: npx vite
# Default port: 5173
```

### Next.js
```bash
npm run dev
# Default port: 3000
```

### Create React App
```bash
npm start
# Default port: 3000
```

### SvelteKit
```bash
npm run dev
# Default port: 5173 (or 3000)
```

### Nuxt
```bash
npm run dev
# Default port: 3000
```

### Astro
```bash
npm run dev
# Default port: 4321
```

## Python

### Flask
```bash
flask run
# Default port: 5000
```

### Django
```bash
python manage.py runserver
# Default port: 8000
```

### FastAPI
```bash
uvicorn main:app --reload
# Default port: 8000
```

### Jupyter
```bash
jupyter notebook
# Default port: 8888
```

## Rust

### Cargo
```bash
cargo run
# Usually port: 8080 (check main.rs for .bind())
```

## Go

### Go Dev Server
```bash
go run .
# Usually port: 8080
```

### Air (live reload)
```bash
air
```

## .NET

### ASP.NET Core
```bash
dotnet run
# Default port: 5000-5100 (check launchSettings.json)
```

## Java

### Spring Boot
```bash
./mvnw spring-boot:run
# Default port: 8080
```

## Process Detection

### Common Dev Server Ports
| Port | Frameworks |
|------|------------|
| 3000 | Next.js, CRA, Remix |
| 3001 | Next.js (alt) |
| 4000 | SvelteKit, Nuxt |
| 4321 | Astro |
| 5000 | Flask |
| 5173 | Vite, SvelteKit |
| 5174 | Vite (alt) |
| 5175+ | Vite (additional) |
| 5174 | Bun |
| 5175-5199 | Vite (additional instances) |
| 8000 | Django |
| 8080 | Java, Go, Spring |
| 8888 | Jupyter |
| 9229 | Node debugger |

### Windows Process Commands
```bash
# Find process on port
netstat -ano | findstr ":5173"

# Kill by PID
taskkill /F /PID <pid>

# List Node processes
tasklist /FI "IMAGENAME eq node.exe"
```

### Find Process by Port (PowerShell)
```powershell
Get-NetTCPConnection -LocalPort 5173 | Select-Object OwningProcess
```
