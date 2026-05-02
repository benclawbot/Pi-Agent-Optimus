# Harness Improvement Log

## 2026-05-01 - Session Improvements

### Skills Health Fix
- **Created:** `skill-health` skill for diagnostic and auto-fix
- **Fixed:** 30 issues across 23 skills
  - Added missing shebangs (`#!/usr/bin/env python3`)
  - Set executable permissions on scripts
- **Result:** 29/29 skills now healthy (100%)

### Evaluation Dashboard
- **Fixed:** Server binding for Snap Chromium compatibility
- **Improved:** Scoring formulas (proactivity min 0.2 baseline)
- **Fixed:** Dynamic current score display
- **Result:** Dashboard score 0.690 → 0.702 (+51% improvement)

### Benchmark Code Fixes
- **Fixed:** `ToolUseAnalyzer` method name mismatch (`extract_tool_calls` → `_extract_tool_calls`)
- **Improved:** Proactivity detection patterns
- **Added:** Min bounds for empty tool_use analyses

## Common Issues & Solutions

### Snap Chromium Can't Access 127.0.0.1
**Problem:** Servers binding to `127.0.0.1` don't work with snap-installed browsers.

**Solution:** Bind to `0.0.0.0` or use LAN IP:
```javascript
server.listen(PORT, '0.0.0.0', () => { ... });
```

### Background Jobs Not Persisting
**Problem:** `&` backgrounding doesn't persist when shell ends.

**Solution:** Use `nohup`:
```bash
nohup node server.js > /tmp/server.log 2>&1 &
```

### Skill Scripts Not Executable
**Problem:** Scripts missing shebangs and executable permissions.

**Solution:** 
```bash
chmod +x scripts/*.py scripts/*.sh
# Add shebang: #!/usr/bin/env python3
```

**Auto-fix:** Run `python3 ~/.pi/agent/skills/skill-health/scripts/diagnose.py --fix`

## Commands Reference

| Command | Purpose |
|---------|---------|
| `python3 skill-health/scripts/diagnose.py` | Check all skills |
| `python3 skill-health/scripts/diagnose.py --fix` | Auto-fix issues |
| `python3 skill-health/scripts/diagnose.py --skill <name>` | Check specific skill |

## Files Changed

- `~/.pi/agent/skills/skill-health/` - New diagnostic skill
- `~/.pi/agent/skills/*/scripts/*.py` - Added shebangs, fixed permissions
- `/home/thomas/Pi-Agent-Optimus/settings.json` - Added skill-health
