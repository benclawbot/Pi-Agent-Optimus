---
name: architecture-diagram
description: Create professional, dark-themed architecture diagrams as standalone HTML files with SVG graphics. Use when "architecture diagram", "system diagram", "infrastructure diagram", "cloud diagram", "system design", or "component map" is requested. Generates self-contained HTML files.
license: MIT
allowed-tools: Read,Bash,write
metadata:
  version: "1.0"
  source: https://github.com/Cocoon-AI/architecture-diagram-generator
---

# Architecture Diagram Generator

Create professional architecture diagrams as self-contained HTML files.

## Quick Use

1. Describe your system in plain text
2. I generate an HTML file with SVG diagram
3. Open in any browser

## Design System

### Color Palette

| Component | Fill | Stroke |
|-----------|------|--------|
| Frontend | `rgba(8, 51, 68, 0.4)` | `#22d3ee` |
| Backend | `rgba(6, 78, 59, 0.4)` | `#34d399` |
| Database | `rgba(76, 29, 149, 0.4)` | `#a78bfa` |
| AWS/Cloud | `rgba(120, 53, 15, 0.3)` | `#fbbf24` |
| Security | `rgba(136, 19, 55, 0.4)` | `#fb7185` |
| Message Bus | `rgba(251, 146, 60, 0.3)` | `#fb923c` |
| External | `rgba(30, 41, 59, 0.5)` | `#94a3b8` |

### Component Pattern

```svg
<rect x="X" y="Y" width="120" height="60" rx="6" fill="FILL" stroke="STROKE" stroke-width="1.5"/>
<text x="CENTER" y="Y+25" fill="white" font-size="11" text-anchor="middle">Label</text>
<text x="CENTER" y="Y+40" fill="#94a3b8" font-size="9" text-anchor="middle">Sublabel</text>
```

## Usage

When you ask for a diagram, I:
1. Extract architecture description from your input or codebase
2. Generate HTML with appropriate components
3. Save to a file (default: `architecture-diagram.html`)
4. Open for you to view

## Example

```
You: Create architecture diagram for a web app with React frontend, Node.js API, and PostgreSQL
→ Generate diagram with:
   - Frontend box (cyan)
   - Backend box (emerald)
   - Database box (violet)
   - Arrows showing connections
   - Summary cards
```

## Template

Use `assets/template.html` as the base. Customize:
- Title and subtitle
- SVG viewBox dimensions
- Component positions
- Connection arrows
- Summary cards
- Footer
