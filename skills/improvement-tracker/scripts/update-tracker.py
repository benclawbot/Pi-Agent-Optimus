#!/usr/bin/env python3
"""
Improvement Tracker — update status, mark done, check completion.
Usage:
  python update-tracker.py --mark 1 --note "built proactive-context skill"
  python update-tracker.py --progress
  python update-tracker.py --done 12 --note "built skill-chain skill"
"""
import os
import re
import sys
from datetime import datetime

TRACKER = os.path.expanduser("~/.pi/agent/improvement-tracker.md")
SUMMARY = os.path.expanduser("~/.pi/agent/improvement-summary.md")

SECTIONS = [
    ("Memory & Continuity", 7),
    ("Context & Retrieval", 4),
    ("Skills & Interoperability", 5),
    ("Reasoning & Delivery Quality", 5),
    ("Speed & Token Efficiency", 4),
    ("Productivity & Workflow", 5),
]

def read_tracker():
    if not os.path.exists(TRACKER):
        print("Tracker not found. All improvements may be complete.")
        if os.path.exists(SUMMARY):
            print(f"Summary exists at {SUMMARY}")
        return None
    with open(TRACKER) as f:
        return f.read()

def write_tracker(content):
    with open(TRACKER, "w") as f:
        f.write(content)

def count_progress():
    content = read_tracker()
    if content is None:
        return 0, 0
    done = content.count("**DONE**")
    todo = content.count("**TODO**")
    return done, todo

def mark_done(num, note=""):
    content = read_tracker()
    if content is None:
        print("Tracker not found.")
        return
    today = datetime.now().strftime("%Y-%m-%d")
    lines = content.split("\n")
    new_lines = []
    updated = False
    
    for line in lines:
        if f"| {num} |" in line and "**TODO**" in line:
            # Mark it done
            parts = line.split("|")
            parts[3] = " **DONE** "
            parts[4] = f" {today} "
            if note:
                parts[-1] = f" {note} "
            line = "|".join(parts)
            updated = True
        new_lines.append(line)
    
    if updated:
        content = "\n".join(new_lines)
        done, todo = count_progress()
        content = re.sub(
            r"Progress: \d+/\d+ DONE",
            f"Progress: {done}/{done + todo} DONE",
            content
        )
        write_tracker(content)
        
        if todo == 0:
            print(f"✓ All 30 improvements complete! Running completion protocol...")
            complete_protocol()
        else:
            print(f"✓ Improvement #{num} marked DONE. {todo} remaining.")
    else:
        print(f"✗ Improvement #{num} not found or already done.")

def show_progress():
    done, todo = count_progress()
    content = read_tracker()
    
    if content is None:
        return
    
    print(f"\n{'='*55}")
    print(f"  PI AGENT IMPROVEMENTS — {done}/30 DONE | {todo} remaining")
    print(f"{'='*55}")
    
    # Parse improvement rows
    done_items = []
    todo_items = []
    
    in_table = False
    for line in content.split("\n"):
        if "| # |" in line:
            in_table = True
            continue
        if in_table and line.startswith("---"):
            break
        if in_table and " | " in line:
            # Split only on first 4 pipes to get num, desc, status
            # Then rest is the note
            line = line.strip()
            if line.startswith('|'):
                line = line[1:]
            parts = line.split('|')
            if len(parts) >= 4:
                num = parts[0].strip()
                desc = parts[1].strip()
                status = parts[2].strip()
                # Notes are everything after parts[3] (Applied date)
                note = parts[4].strip() if len(parts) > 4 else ""
                if note == '—':
                    note = ""
                if "DONE" in status:
                    done_items.append((num, desc, note))
                elif "TODO" in status:
                    todo_items.append((num, desc))
    
    # Show DONE with notes
    if done_items:
        print(f"\n  DONE:")
        for num, desc, note in done_items:
            short_desc = desc[:40]
            short_note = f"→ {note}" if note and note != "—" else ""
            print(f"  #{num:>2}: {short_desc:<42} {short_note}")
    
    # Show next TODO
    if todo_items:
        print(f"\n  NEXT:")
        num, desc = todo_items[0]
        print(f"  #{num:>2}: {desc}")
        if len(todo_items) > 1:
            print(f"  +{len(todo_items)-1} more")
    
    # Progress bar
    pct = int(100 * done / 30)
    bar_len = 30
    filled = int(bar_len * done / 30)
    bar = "█" * filled + "░" * (bar_len - filled)
    print(f"\n  [{bar}] {pct}%")
    
    # Done items with notes
    done_with_notes = [(n, d, no) for n, d, no in done_items if no and no != "—"]
    if done_with_notes:
        print(f"\n  Applied:")
        for num, desc, note in done_with_notes:
            short_note = note[:50]
            print(f"  #{num}: {short_note}")
    
    print()
    return done, todo

def complete_protocol():
    """Run when all 30 are done."""
    content = read_tracker()
    if content is None:
        return
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Build summary
    done_items = []
    for line in content.split("\n"):
        if "**DONE**" in line and " | " in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 4:
                num = parts[1]
                desc = parts[2]
                note = parts[-1].strip()
                done_items.append((num, desc, note))
    
    summary = f"""# Pi Agent Improvements — Complete

**Completed:** {today}

All 30 improvements implemented.

## Done Items

"""
    for num, desc, note in done_items:
        summary += f"\n### #{num}: {desc}\n"
        if note and note != "—":
            summary += f"Applied: {note}\n"
    
    summary += """
## Skills Created

- `proactive-context` — loads vault context at startup
- `quick-context` — wikilink-style `[[context]]` resolution
- `skill-chain` — skills activate together based on context

## Remaining Improvements (for future sessions)

When continuing work on the agent, check this file's history for context.
"""
    
    with open(SUMMARY, "w") as f:
        f.write(summary)
    
    os.remove(TRACKER)
    print(f"✓ Tracker complete. Summary saved to {SUMMARY}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        show_progress()
    elif sys.argv[1] == "--progress":
        show_progress()
    elif sys.argv[1] in ("--done", "--mark"):
        num = sys.argv[2] if len(sys.argv) > 2 else ""
        note = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else ""
        if num:
            mark_done(num, note)
        else:
            print("Usage: --done <number> [--note 'description']")
    elif sys.argv[1] == "--help":
        print("Usage: update-tracker.py [--progress|--done N [--note 'text']]")
