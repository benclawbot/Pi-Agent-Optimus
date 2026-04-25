# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

"""
Phase 3: Validation & Guardrails

Validates skill updates against size limits and semantic preservation.
"""

import json
import re
import sys
from pathlib import Path
from typing import Optional

# Configuration
SKILLS_DIR = Path.home() / ".pi" / "agent" / "skills"

# Size limits (in bytes unless noted)
LIMITS = {
    "skill_md_kb": 15,
    "tool_description_chars": 500,
    "reference_md_kb": 50,
    "frontmatter_description_chars": 1024
}


def load_skill(skill_name: str) -> Optional[dict]:
    """Load skill files."""
    skill_dir = SKILLS_DIR / skill_name
    if not skill_dir.exists():
        return None
    
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return None
    
    with open(skill_md) as f:
        content = f.read()
    
    # Parse frontmatter
    lines = content.split("\n")
    frontmatter = {}
    body_lines = []
    in_frontmatter = False
    
    for line in lines:
        if line.strip() == "---":
            in_frontmatter = not in_frontmatter
            continue
        if in_frontmatter and ":" in line:
            key, value = line.split(":", 1)
            frontmatter[key.strip()] = value.strip()
        elif not in_frontmatter:
            body_lines.append(line)
    
    return {
        "name": skill_name,
        "frontmatter": frontmatter,
        "body": "\n".join(body_lines),
        "content": content,
        "size_bytes": len(content.encode('utf-8')),
        "size_kb": len(content) / 1024,
        "lines": len(lines)
    }


def check_size_limits(skill: dict) -> dict:
    """Check skill against size limits."""
    issues = []
    
    # SKILL.md size
    if skill["size_kb"] > LIMITS["skill_md_kb"]:
        issues.append({
            "type": "size_exceeded",
            "target": "SKILL.md",
            "limit_kb": LIMITS["skill_md_kb"],
            "actual_kb": round(skill["size_kb"], 2),
            "severity": "error" if skill["size_kb"] > LIMITS["skill_md_kb"] * 1.2 else "warning"
        })
    
    # Description length
    desc = skill["frontmatter"].get("description", "")
    if len(desc) > LIMITS["frontmatter_description_chars"]:
        issues.append({
            "type": "description_too_long",
            "target": "frontmatter.description",
            "limit_chars": LIMITS["frontmatter_description_chars"],
            "actual_chars": len(desc),
            "severity": "warning"
        })
    
    # Check references
    skill_dir = SKILLS_DIR / skill["name"]
    for ref_dir in ["references", "scripts", "assets"]:
        ref_path = skill_dir / ref_dir
        if ref_path.exists():
            for md_file in ref_path.rglob("*.md"):
                with open(md_file) as f:
                    content = f.read()
                size_kb = len(content) / 1024
                if size_kb > LIMITS["reference_md_kb"]:
                    issues.append({
                        "type": "reference_too_large",
                        "target": str(md_file.relative_to(skill_dir)),
                        "limit_kb": LIMITS["reference_md_kb"],
                        "actual_kb": round(size_kb, 2),
                        "severity": "warning"
                    })
    
    return {
        "skill": skill["name"],
        "total_size_kb": round(skill["size_kb"], 2),
        "size_limit_kb": LIMITS["skill_md_kb"],
        "within_limit": len([i for i in issues if i["type"] == "size_exceeded"]) == 0,
        "issues": issues
    }


def check_semantic_preservation(original: str, evolved: str) -> dict:
    """
    Check if evolved text preserves core semantics.
    
    In production, this would use embeddings or LLM comparison.
    Here we use heuristics.
    """
    issues = []
    warnings = []
    
    # Extract key elements from original
    orig_lines = original.split("\n")
    orig_lower = original.lower()
    
    evolved_lines = evolved.split("\n")
    evolved_lower = evolved.lower()
    
    # Check frontmatter name match
    orig_name = re.search(r'^name:\s*(.+)$', original, re.MULTILINE)
    evolved_name = re.search(r'^name:\s*(.+)$', evolved, re.MULTILINE)
    
    if orig_name and evolved_name:
        if orig_name.group(1).strip() != evolved_name.group(1).strip():
            issues.append({
                "type": "name_mismatch",
                "original": orig_name.group(1).strip(),
                "evolved": evolved_name.group(1).strip()
            })
    
    # Check for removed trigger phrases
    trigger_keywords = ["use when", "trigger", "when the user"]
    for keyword in trigger_keywords:
        if keyword in orig_lower and keyword not in evolved_lower:
            warnings.append(f"Trigger phrase '{keyword}' may be missing")
    
    # Check for removed sections
    section_patterns = [
        (r'##\s+\w+', 'section headers'),
        (r'```[\s\S]*?```', 'code blocks'),
        (r'\|.+\|', 'tables')
    ]
    
    for pattern, name in section_patterns:
        orig_count = len(re.findall(pattern, original))
        evolved_count = len(re.findall(pattern, evolved))
        
        # Allow some removal, but flag significant changes
        if orig_count > 0 and evolved_count < orig_count * 0.5:
            warnings.append(f"Significant reduction in {name} ({orig_count} -> {evolved_count})")
    
    # Check name field consistency
    skill_name = None
    if orig_name:
        skill_name = orig_name.group(1).strip()
        # Check if skill name still appears in content
        if skill_name not in evolved:
            issues.append({
                "type": "name_not_in_content",
                "skill_name": skill_name
            })
    
    return {
        "preserved": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "summary": "OK" if len(issues) == 0 and len(warnings) == 0 
                   else "Issues found" if len(issues) > 0 
                   else "Warnings only"
    }


def check_trigger_phrases(skill: dict) -> dict:
    """Check if trigger phrases are still present."""
    content = skill["content"].lower()
    
    expected_triggers = [
        "use when",
        "trigger",
        "ask",
        "help"
    ]
    
    found_triggers = []
    missing_triggers = []
    
    for trigger in expected_triggers:
        if trigger in content:
            found_triggers.append(trigger)
        else:
            missing_triggers.append(trigger)
    
    # Check description has trigger info
    desc = skill["frontmatter"].get("description", "")
    desc_has_triggers = "when" in desc.lower() or "use" in desc.lower()
    
    return {
        "skill": skill["name"],
        "description_has_triggers": desc_has_triggers,
        "found_triggers": found_triggers,
        "missing_triggers": missing_triggers,
        "status": "good" if desc_has_triggers or found_triggers else "needs_review"
    }


def validate_skill(skill_name: str, evolved_content: Optional[str] = None) -> dict:
    """Full validation of a skill."""
    skill = load_skill(skill_name)
    if not skill:
        return {"error": f"Skill '{skill_name}' not found"}
    
    results = {
        "skill": skill_name,
        "timestamp": "",  # Add timestamp
        "size_check": check_size_limits(skill),
        "trigger_check": check_trigger_phrases(skill)
    }
    
    if evolved_content:
        results["semantic_check"] = check_semantic_preservation(skill["content"], evolved_content)
    
    # Overall status
    size_ok = results["size_check"]["within_limit"]
    triggers_ok = results["trigger_check"]["status"] == "good"
    
    if evolved_content:
        semantic_ok = results.get("semantic_check", {}).get("preserved", True)
        results["overall_status"] = "pass" if size_ok and triggers_ok and semantic_ok else "fail"
    else:
        results["overall_status"] = "pass" if size_ok and triggers_ok else "needs_review"
    
    return results


def main():
    if len(sys.argv) < 2:
        print("Usage: validate-skill.py <command> [args]")
        print("Commands:")
        print("  check-size <skill>")
        print("  check-semantic <skill> --evolved <file>")
        print("  check-triggers <skill>")
        print("  validate <skill>")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "check-size":
        skill = sys.argv[2] if len(sys.argv) > 2 else "skill-evolution"
        skill_data = load_skill(skill)
        if skill_data:
            result = check_size_limits(skill_data)
            print(json.dumps(result, indent=2))
        else:
            print(f"Skill '{skill}' not found")
    
    elif cmd == "check-semantic":
        skill = sys.argv[2] if len(sys.argv) > 2 else "skill-evolution"
        evolved_file = None
        
        if "--evolved" in sys.argv:
            idx = sys.argv.index("--evolved")
            evolved_file = sys.argv[idx + 1]
        
        if not evolved_file:
            print("Error: --evolved <file> required")
            sys.exit(1)
        
        skill_data = load_skill(skill)
        if not skill_data:
            print(f"Skill '{skill}' not found")
            sys.exit(1)
        
        with open(evolved_file) as f:
            evolved_content = f.read()
        
        result = check_semantic_preservation(skill_data["content"], evolved_content)
        print(json.dumps(result, indent=2))
    
    elif cmd == "check-triggers":
        skill = sys.argv[2] if len(sys.argv) > 2 else "skill-evolution"
        skill_data = load_skill(skill)
        if skill_data:
            result = check_trigger_phrases(skill_data)
            print(json.dumps(result, indent=2))
        else:
            print(f"Skill '{skill}' not found")
    
    elif cmd == "validate":
        skill = sys.argv[2] if len(sys.argv) > 2 else "skill-evolution"
        result = validate_skill(skill)
        print(json.dumps(result, indent=2))
    
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
