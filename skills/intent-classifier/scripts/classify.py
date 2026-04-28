#!/usr/bin/env python3
"""
Intent Classifier — detects what Thomas is trying to do, routes to relevant skills.
Usage:
  python classify.py "message text"
  python classify.py --show
  python classify.py --list
"""
import re
import sys
from typing import Optional

INTENT_PATTERNS = {
    "debugging": [
        r"\berror\b", r"\bbug\b", r"\bcrash\b", r"\bfailed\b", r"\bException\b",
        r"traceback", r"stack.*trace", r"doesn't work", r"\bbroken\b",
        r"fix this", r"what went wrong", r"\bfix\b.*\berror\b",
        r"got an?", r"something is wrong",
    ],
    "coding": [
        r"\.(py|js|ts|jsx|tsx|go|rs|java|cpp|c|h|hpp)\b",
        r"\bdef\s+\w+\(", r"\bclass\s+\w+", r"\bimport\s+\w+",
        r"\bfunction\s+\w+", r"\bconst\s+\w+\s*=", r"\blet\s+\w+\s*=",
        r"=>", r"->", r"\bfn\s+\w+", r"\bfunc\s+\w+",
        r"write.*code", r"implement", r"add.*function", r"add.*method",
    ],
    "architecture": [
        r"architecture", r"system design", r"component map",
        r"diagram", r"structure", r"design pattern",
        r"how do i structure", r"what's the best way to",
        r"high-level", r"overview", r"data flow",
    ],
    "research": [
        r"what is", r"how does", r"explain", r"search for",
        r"find information", r"look up", r"\bresearch\b",
        r"tell me about", r"what's a", r"learn about",
        r"understand", r"explore",
    ],
    "health-check": [
        r"\bhealth\b", r"\bstatus\b", r"\bdeps\b", r"\boutdated\b",
        r"ci status", r"test coverage", r"are we green",
        r"project health", r"check.*up", r"how's.*doing",
    ],
    "testing": [
        r"\btest\b", r"\bpytest\b", r"\bcoverage\b", r"run tests",
        r"unit test", r"integration test", r"\bspec\b",
        r"test.*fail", r"write.*test",
    ],
    "planning": [
        r"\bplan\b", r"next steps", r"how to", r"should we",
        r"roadmap", r"milestones", r"getting started",
        r"setup", r"where to start",
    ],
    "review": [
        r"\breview\b", r"\bPR\b", r"pull request", r"check this",
        r"look at", r"review.*code", r"feedback",
    ],
    "ops": [
        r"\bdeploy\b", r"\bserver\b", r"\brunning\b", r"\bport\b",
        r"\bprocess\b", r"\bdocker\b", r"kubernetes", r"ci/cd",
        r"restart", r"kill", r"stop",
    ],
}

INTENT_SKILLS = {
    "debugging": ["auto-recover", "system-awareness", "context-memory"],
    "coding": ["auto-test", "context-memory", "project-health"],
    "architecture": ["architecture-diagram", "context-memory"],
    "research": ["context-memory", "quick-context"],
    "health-check": ["project-health", "ci-watcher"],
    "testing": ["auto-test", "project-health"],
    "planning": ["context-memory", "architecture-diagram"],
    "review": ["ci-watcher", "auto-test"],
    "ops": ["system-awareness", "project-health"],
}

def classify(text: str) -> dict:
    """Classify text into intent categories."""
    text_lower = text.lower()
    scores = {}
    
    for intent, patterns in INTENT_PATTERNS.items():
        score = 0
        matched = []
        for pattern in patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                score += 1
                matched.append(pattern)
        if score > 0:
            scores[intent] = {"score": score, "matched": matched}
    
    if not scores:
        return {"intent": "general", "confidence": "low", "skills": [], "signals": []}
    
    # Get top intent
    top = max(scores.items(), key=lambda x: x[1]["score"])
    intent = top[0]
    score = top[1]["score"]
    
    # Confidence based on number of matches
    if score >= 3:
        confidence = "high"
    elif score >= 2:
        confidence = "medium"
    else:
        confidence = "low"
    
    return {
        "intent": intent,
        "confidence": confidence,
        "skills": INTENT_SKILLS.get(intent, []),
        "signals": top[1]["matched"],
    }

def show_intent(text: str):
    result = classify(text)
    
    print(f"\n  Intent: {result['intent']}")
    print(f"  Confidence: {result['confidence']}")
    if result['signals']:
        print(f"  Signals: {', '.join(result['signals'][:5])}")
    if result['skills']:
        print(f"  Activates: {', '.join(result['skills'])}")
    print()

def list_intents():
    print(f"\n  Intent Categories")
    print(f"  {'='*55}")
    for intent, patterns in INTENT_PATTERNS.items():
        skills = INTENT_SKILLS.get(intent, [])
        print(f"\n  {intent}:")
        print(f"    Skills: {', '.join(skills) if skills else 'none'}")
        print(f"    Patterns: {len(patterns)} detection rules")
    print()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        list_intents()
    elif sys.argv[1] == "--show":
        print("  Detected: general (no specific signals)")
    elif sys.argv[1] == "--list":
        list_intents()
    elif sys.argv[1].startswith("-"):
        print("Usage: classify.py [--list|--show] [text]")
    else:
        text = " ".join(sys.argv[1:])
        show_intent(text)