#!/usr/bin/env python3
"""
Proactivity Detector - Analyzes traces and outputs for proactive behaviors.

Philosophy:
  - Structural signals (Done, Test Results, Next Steps, Summary, Rollback) are ALWAYS required
  - Context-dependent signals (Risks, Security, Performance, Breaking Changes,
    Scan for Similar, Architecture) are rewarded ONLY when genuinely applicable
  - Volunteered info should only be rewarded when backed by a real tradeoff
  - No penalty for absence of context-dependent signals that weren't applicable

Scoring (0-5):
  - Done block: +0.5
  - Test results: +0.5
  - Next steps: +0.5
  - Summary: +0.3
  - Rollback: +0.3
  - Proposed next steps (quality): +0.5
  - Risk flags (when applicable): +0.5
  - Security flags (when applicable): +0.5
  - Performance hints (when applicable): +0.4
  - Breaking change notes (when applicable): +0.3
  - Scan for similar (when applicable): +0.3
  - Architecture observations (when applicable): +0.3
  - Unprompted quality cleanup: +0.3
  - Unprompted test generation: +0.5
  - Alternatives at decision points: +0.2
  - Parallel announcements: +0.2
  - Strategy adaptation: +0.2
  - Auto-validation: +0.2
  - Commit draft: +0.2

Max: ~5.0 → capped at 5.0
"""

import json
import re
from typing import Dict, Any, List


class ProactivityDetector:
    """Detects proactive behaviors in agent execution output."""

    # === STRUCTURAL PATTERNS (always required) ===

    DONE_PATTERNS = [
        r"Done\.",
        r"- Created:",
        r"Files? (?:Created|Modified|Deleted)",
    ]

    TEST_PATTERNS = [
        r"Test Results?:",
        r"\d+ of \d+ tests? (?:pass|fail)",
        r"tests? (?:all |)(\d+/\d+ )?pass",
    ]

    NEXT_STEPS_PATTERNS = [
        r"Next steps?:",
        r"→ .+",
        r"^\s*-\s+.+\n\s*-\s+.+",
    ]

    SUMMARY_PATTERNS = [
        r"Summary:",
        r"Approach:",
    ]

    ROLLBACK_PATTERNS = [
        r"Rollback:",
        r"git revert",
        r"undo:",
    ]

    # === CONTEXT-DEPENDENT PATTERNS ===

    RISK_PATTERNS = [
        r"⚠️ Risks?:",
        r"(?i)risk[:\s]",
        r"(?i)edge case[:\s]",
        r"(?i)caveat[:\s]",
    ]

    SECURITY_PATTERNS = [
        r"⚠️ Security:",
        r"(?i)security[:\s]",
        r"(?i)injection",
        r"(?i)sanitiz",
        r"(?i)xss",
        r"(?i)csrf",
    ]

    PERFORMANCE_PATTERNS = [
        r"⚠️ Performance:",
        r"(?i)O\([n²n³log]\)",
        r"(?i)performance[:\s]",
        r"(?i)optimiz",
    ]

    BREAKING_PATTERNS = [
        r"⚠️ Breaking:",
        r"(?i)breaking[:\s]",
        r"(?i)migration[:\s]",
        r"(?i)compatib",
    ]

    SCAN_PATTERNS = [
        r"(?i)scan for (?:the same|similar)",
        r"(?i)generalize",
        r"(?i)apply to all",
        r"(?i)found \d+ fix",
    ]

    ARCHITECTURE_PATTERNS = [
        r"(?i)architecture[:\s]",
        r"(?i)design[:\s]",
        r"(?i)module boundary",
        r"(?i)loose coupling",
        r"(?i)cohesion",
        r"(?i)abstraction",
    ]

    # === HIGH-QUALITY PATTERNS ===

    PROPOSED_NEXT_STEPS_PATTERNS = [
        r"(?i)next steps?:",
        r"(?i)suggest",
        r"(?i)recommend",
        r"(?i)→ .+",
        r"(?i)i can also .+",
    ]

    UNPROMPTED_ACTION_PATTERNS = [
        r"(?i)as a bonus[:\s]",
        r"(?i)without being asked",
        r"(?i)i also (?:created|added|wrote|fixed|updated|cleaned)",
        r"(?i)additionally[:\s]",
    ]

    QUALITY_CLEANUP_PATTERNS = [
        r"(?i)unused import",
        r"(?i)magic number",
        r"(?i)dead code",
        r"(?i)cleaned[:\s]",
        r"(?i)removed[:\s]",
    ]

    TEST_GENERATION_PATTERNS = [
        r"(?i)comprehensive test",
        r"(?i)edge cases?[:\s]",
        r"(?i)coverage[:\s]",
        r"(?i)test[eds]?[:\s]",
    ]

    PARALLEL_PATTERNS = [
        r"(?i)in parallel[:\s]",
        r"(?i)simultaneously[:\s]",
        r"(?i)running[:\s].+(?:and|&)[:\s]",
    ]

    ALTERNATIVES_PATTERNS = [
        r"(?i)alternatively[:\s]",
        r"(?i)approach [ab][:\s]",
        r"(?i)you could (?:also|instead)",
    ]

    STRATEGY_PATTERNS = [
        r"(?i)switching to[:\s]",
        r"(?i)using [:\\w]+ instead",
        r"(?i)falling back to",
    ]

    AUTO_VALIDATION_PATTERNS = [
        r"(?i)auto-validat",
        r"(?i)syntax check",
        r"(?i)lint[:\s]",
        r"(?i)format",
    ]

    COMMIT_PATTERNS = [
        r"(?i)commit[:\s]",
        r"(?i)conventional commit",
    ]

    # === REACTIVE (penalty) ===
    REACTIVE_PATTERNS = [
        r"(?i)should i",
        r"(?i)do you want me to",
        r"(?i)let me know if",
        r"(?i)please confirm",
        r"(?i)is this (?:what you want|okay|correct)",
        r"(?i)do you approve",
        r"(?i)would you like me to",
    ]

    def __init__(self, config: Dict):
        self.config = config

    def analyze(self, trace: List[Dict], output: str, task_context: Dict = None) -> Dict[str, Any]:
        """
        Analyze execution for proactivity. Returns score 0-5.

        Args:
            trace: execution trace (not used, Hermes doesn't emit structured traces)
            output: agent's text output
            task_context: optional dict with 'category', 'description' to determine
                         which context-dependent signals were applicable
        """
        task_context = task_context or {}
        desc = (task_context.get('description', '') + ' ' + task_context.get('name', '')).lower()
        category = task_context.get('category', '')

        # Detect structural elements
        has_done = self._has_any(output, self.DONE_PATTERNS)
        has_test_results = self._has_any(output, self.TEST_PATTERNS)
        has_next_steps = self._has_any(output, self.NEXT_STEPS_PATTERNS)
        has_summary = self._has_any(output, self.SUMMARY_PATTERNS)
        has_rollback = self._has_any(output, self.ROLLBACK_PATTERNS)

        # Detect pattern counts
        proposed = len(self._find_all(output, self.PROPOSED_NEXT_STEPS_PATTERNS))
        risks = len(self._find_all(output, self.RISK_PATTERNS))
        security = len(self._find_all(output, self.SECURITY_PATTERNS))
        perf = len(self._find_all(output, self.PERFORMANCE_PATTERNS))
        breaking = len(self._find_all(output, self.BREAKING_PATTERNS))
        scan = len(self._find_all(output, self.SCAN_PATTERNS))
        arch = len(self._find_all(output, self.ARCHITECTURE_PATTERNS))
        unprompted = len(self._find_all(output, self.UNPROMPTED_ACTION_PATTERNS))
        quality = len(self._find_all(output, self.QUALITY_CLEANUP_PATTERNS))
        tests = len(self._find_all(output, self.TEST_GENERATION_PATTERNS))
        parallel = len(self._find_all(output, self.PARALLEL_PATTERNS))
        alternatives = len(self._find_all(output, self.ALTERNATIVES_PATTERNS))
        strategy = len(self._find_all(output, self.STRATEGY_PATTERNS))
        auto_val = len(self._find_all(output, self.AUTO_VALIDATION_PATTERNS))
        commit = len(self._find_all(output, self.COMMIT_PATTERNS))
        waited = self._has_any(output, self.REACTIVE_PATTERNS)

        # Determine which context-dependent signals were applicable
        context = self._analyze_context(desc, category)
        files = self._count_files(output)
        has_done = has_done and files > 0

        # Compute score
        score = self._compute_score(
            has_done=has_done,
            has_test_results=has_test_results,
            has_next_steps=has_next_steps,
            has_summary=has_summary,
            has_rollback=has_rollback,
            proposed=proposed,
            risks=risks,
            security=security,
            perf=perf,
            breaking=breaking,
            scan=scan,
            arch=arch,
            unprompted=unprompted,
            quality=quality,
            tests=tests,
            parallel=parallel,
            alternatives=alternatives,
            strategy=strategy,
            auto_val=auto_val,
            commit=commit,
            waited=waited,
            context=context,
            files=files,
        )

        return {
            "score": round(score, 2),
            "waited_for_user": waited,
            "files_created": files,
            "has_done_block": has_done,
            "has_test_results": has_test_results,
            "has_next_steps": has_next_steps,
            "has_summary": has_summary,
            "has_rollback": has_rollback,
            "context_applicable": context,
            "breakdown": {
                "done_block": 1 if has_done else 0,
                "test_results": 1 if has_test_results else 0,
                "next_steps": 1 if has_next_steps else 0,
                "summary": 1 if has_summary else 0,
                "rollback": 1 if has_rollback else 0,
                "proposed_next_steps": proposed,
                "risk_flags": risks if context['has_risks'] else f"{risks} (not applicable)",
                "security_flags": security if context['has_security'] else f"{security} (not applicable)",
                "perf_hints": perf if context['has_perf'] else f"{perf} (not applicable)",
                "breaking_notes": breaking if context['has_breaking'] else f"{breaking} (not applicable)",
                "scan_similar": scan if context['has_scan'] else f"{scan} (not applicable)",
                "arch_observations": arch if context['has_arch'] else f"{arch} (not applicable)",
                "unprompted_actions": unprompted,
                "quality_cleanup": quality,
                "test_generation": tests,
                "parallel_announcements": parallel,
                "alternatives": alternatives,
                "strategy_adaptation": strategy,
                "auto_validation": auto_val,
                "commit_draft": commit,
            }
        }

    def _analyze_context(self, desc: str, category: str) -> Dict[str, bool]:
        """Determine which context-dependent signals were applicable for this task."""
        risk_kw = ['injection', 'race', 'null', 'crash', 'leak', 'validation', 'error',
                   'exception', 'boundary', 'concurrency', 'deadlock', 'memory', 'resource']
        sec_kw = ['sql', 'xss', 'csrf', 'auth', 'permission', 'input', 'password',
                  'token', 'api', 'user', 'data', 'encrypt', 'sanitiz']
        perf_kw = ['loop', 'nested', 'recursive', 'search', 'sort', 'traverse',
                   'batch', 'cache', 'performance', 'optim', 'complex']
        break_kw = ['api', 'interface', 'signature', 'breaking', 'migration',
                    'upgrade', 'compatib', 'deprecat', 'refactor']
        scan_kw = ['null', 'leak', 'injection', 'race', 'deadlock', 'order',
                   'import', 'sql', 'xss', 'memory', 'resource', 'encoding',
                   'typo', 'naming', 'leak', 'concurren', 'auth']

        return {
            'has_risks': any(kw in desc for kw in risk_kw) or category == 'debug',
            'has_security': any(kw in desc for kw in sec_kw),
            'has_perf': any(kw in desc for kw in perf_kw) or category == 'refactor',
            'has_breaking': any(kw in desc for kw in break_kw) or category == 'refactor',
            'has_scan': any(kw in desc for kw in scan_kw),
            'has_arch': category == 'architecture',
        }

    def _has_any(self, text: str, patterns: List[str]) -> bool:
        for p in patterns:
            if re.search(p, text, re.IGNORECASE):
                return True
        return False

    def _find_all(self, text: str, patterns: List[str]) -> List[str]:
        matches = []
        for p in patterns:
            found = re.findall(p, text, re.IGNORECASE)
            matches.extend(found)
        return matches

    def _count_files(self, text: str) -> int:
        """Count files from diff headings or markdown."""
        count = 0

        # Git diff headings
        count += len(re.findall(r"\+\+\+\+ b/([\w/\-\.]+\.\w{1,10})", text))

        # Markdown bold filenames
        count += len(re.findall(r"\*\*([\w/\-\.]+\.\w{1,10})\*\*", text))

        # Created: list
        created = re.findall(r"- Created: ([^\n]+)", text, re.IGNORECASE)
        for item in created:
            files = [f.strip() for f in re.split(r",|\band\b", item)]
            count += len([f for f in files if '.' in f])

        # Bullet point files
        count += len(re.findall(r"- \*\*([^\*]+\.\w{1,10})\*\*", text))

        return count

    def _compute_score(
        self,
        has_done: bool,
        has_test_results: bool,
        has_next_steps: bool,
        has_summary: bool,
        has_rollback: bool,
        proposed: int,
        risks: int,
        security: int,
        perf: int,
        breaking: int,
        scan: int,
        arch: int,
        unprompted: int,
        quality: int,
        tests: int,
        parallel: int,
        alternatives: int,
        strategy: int,
        auto_val: int,
        commit: int,
        waited: bool,
        context: Dict[str, bool],
        files: int,
    ) -> float:
        score = 0.0

        # === STRUCTURAL (always required) ===
        score += 0.5 if has_done else 0.0
        score += 0.5 if has_test_results else 0.0
        score += 0.5 if has_next_steps else 0.0
        score += 0.3 if has_summary else 0.0
        score += 0.3 if has_rollback else 0.0

        # === HIGH-QUALITY NEXT STEPS (beyond the required block) ===
        score += min(proposed * 0.4, 0.8)

        # === CONTEXT-DEPENDENT (only when applicable) ===
        if context['has_risks']:
            score += min(risks * 0.4, 0.6)

        if context['has_security']:
            score += min(security * 0.4, 0.6)

        if context['has_perf']:
            score += min(perf * 0.3, 0.5)

        if context['has_breaking']:
            score += min(breaking * 0.3, 0.4)

        if context['has_scan']:
            score += min(scan * 0.3, 0.4)

        if context['has_arch']:
            score += min(arch * 0.3, 0.4)

        # === UNPROMPTED QUALITY ACTIONS ===
        score += min(unprompted * 0.2, 0.4)
        score += min(quality * 0.2, 0.3)
        score += min(tests * 0.3, 0.5)

        # === PROCESS COMMUNICATION ===
        score += min(parallel * 0.15, 0.3)
        score += min(alternatives * 0.2, 0.3)
        score += min(strategy * 0.15, 0.3)
        score += min(auto_val * 0.15, 0.3)
        score += min(commit * 0.15, 0.3)

        # === REACTIVE PENALTY ===
        if waited:
            score = max(0, score - 0.5)

        return min(score, 5.0)


if __name__ == "__main__":
    detector = ProactivityDetector({})

    # Test 1: Full proactivity with genuine tradeoffs only
    good_output = """
Done.
- Created: **auth.py**, **test_auth.py**

Test Results: 8 of 8 tests pass.

Next steps:
→ Run full test suite
→ Check for similar SQL injection patterns in other files

Summary: Replaced string concatenation with parameterized queries to prevent SQL injection.

Rollback: git revert HEAD

⚠️ Risks:
- Edge case: empty string input not handled
⚠️ Security: ensure all user input is sanitized before query construction
⚠️ Performance: no measurable change (O(1) for both approaches)

Found 1 fix. Can scan for the same pattern in other files.
"""

    r1 = detector.analyze([], good_output, {
        'category': 'debug',
        'description': 'fix SQL injection vulnerability in user authentication'
    })
    print(f"Good output: {r1['score']:.1f}/5.0")

    # Test 2: Minimal structural output
    minimal = """
Done.
- Created: **config.py**, **test_config.py**

Test Results: 3 of 3 tests pass.

Next steps:
→ Run full test suite
→ Update docs

Summary: Extracted configuration to a dedicated module.

Rollback: git revert HEAD
"""
    r2 = detector.analyze([], minimal, {
        'category': 'refactor',
        'description': 'extract configuration into separate class'
    })
    print(f"Minimal structural: {r2['score']:.1f}/5.0")

    # Test 3: Reactive (penalty)
    reactive = """
Done.
Created: fix.py.

Should I create tests?
"""
    r3 = detector.analyze([], reactive, {'category': 'debug', 'description': 'fix null pointer'})
    print(f"Reactive output: {r3['score']:.1f}/5.0 (penalized for asking)")
