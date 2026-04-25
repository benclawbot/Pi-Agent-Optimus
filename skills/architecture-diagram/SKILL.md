---
name: architecture-diagram
description: Create professional, dark-themed architecture diagrams as standalone HTML files with SVG graphics. Use when "architecture diagram", "system diagram", "infrastructure diagram", "cloud diagram", "system design", or "component map" is requested. Generates self-contained HTML files.
location: C:\Users\thoma\.pi\agent\skills\architecture-diagram\SKILL.md
---

# Architecture Diagram Skill

Create professional dark-themed architecture diagrams as standalone HTML files.

## When to Use

- User requests "architecture diagram", "system diagram", "system design"
- User asks for "component map", "infrastructure diagram"
- Planning phase needs visual representation of system design

## Output

Single self-contained HTML file with:
- Dark background (#0d1117)
- SVG graphics
- Responsive layout
- Downloadable as .html

## How to Create

### 1. Analyze Request
- What system needs to be diagrammed?
- What components exist?
- How do they interact?
- What's the data flow?

### 2. Design the Diagram
Use standard shapes:
- **Rounded rectangles** for services/components
- **Rectangles with color** for databases/storage
- **Arrows** for data flow (solid = sync, dashed = async)
- **Labels** on arrows for operations
- **Groups** with colored borders for containers/cloud boundaries

### 3. Generate HTML
Create a complete HTML file with inline CSS and SVG:

```html
<!DOCTYPE html>
<html>
<head>
  <style>
    body { background: #0d1117; color: #e6edf3; font-family: system-ui; padding: 20px; }
    svg { max-width: 100%; height: auto; }
    .component { fill: #161b22; stroke: #30363d; stroke-width: 2; rx: 8; }
    .database { fill: #1c2128; stroke: #58a6ff; stroke-width: 2; rx: 4; }
    .arrow { stroke: #8b949e; stroke-width: 2; fill: none; marker-end: url(#arrowhead); }
    .label { fill: #8b949e; font-size: 12px; }
    .title { fill: #e6edf3; font-size: 20px; font-weight: bold; }
    .group { fill: none; stroke: #30363d; stroke-width: 1; stroke-dasharray: 5,5; rx: 8; }
  </style>
</head>
<body>
  <!-- SVG diagram here -->
</body>
</html>
```

### 4. Key Patterns

#### Service Box
```html
<rect x="50" y="50" width="120" height="60" class="component"/>
<text x="110" y="85" text-anchor="middle" fill="#e6edf3">Service</text>
```

#### Database
```html
<ellipse cx="350" cy="80" rx="50" ry="20" class="database"/>
<rect x="300" y="80" width="100" height="40" class="database"/>
<ellipse cx="350" cy="120" rx="50" ry="20" class="database"/>
```

#### Arrow with Label
```html
<defs>
  <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
    <polygon points="0 0, 10 3.5, 0 7" fill="#8b949e"/>
  </marker>
</defs>
<line x1="170" y1="80" x2="300" y2="80" class="arrow"/>
<text x="235" y="70" text-anchor="middle" class="label">GET /api</text>
```

#### Cloud Group
```html
<rect x="40" y="30" width="720" height="140" class="group"/>
<text x="60" y="50" fill="#58a6ff" font-size="14px">AWS Cloud</text>
```

## Examples

### Web App Architecture
```
┌─────────────────────────────────────────────────────┐
│                     AWS Cloud                        │
│                                                     │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐      │
│  │  Client  │───▶│   LB     │───▶│  Server  │      │
│  └──────────┘    └──────────┘    └──────────┘      │
│                                          │          │
│                         ┌────────────────┼────────┐ │
│                         ▼                ▼        │ │
│                  ┌──────────┐    ┌──────────┐ │ │
│                  │    DB    │    │   Cache  │ │ │
│                  └──────────┘    └──────────┘ │ │
│                                            └───┘ │
└─────────────────────────────────────────────────────┘
```

### Data Pipeline
```
┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐
│ Source │───▶│ Transform│───▶│  Store │───▶│  Sink  │
└────────┘    └────────┘    └────────┘    └────────┘
```

## Rules

- **Dark theme only** — dark background, light text, colored accents
- **Self-contained** — no external dependencies except system fonts
- **SVG-based** — use SVG for all graphics (no canvas/images)
- **Responsive** — works on mobile and desktop
- **Readable labels** — font size at least 12px
- **Consistent spacing** — use grid alignment

## Tools

Use the `write` tool to create the HTML file, `read` to review, `edit` to modify.

## Exit

After creating the diagram, show the user:
- File path where it was saved
- A brief description of what the diagram shows
- How to open/view it in a browser
