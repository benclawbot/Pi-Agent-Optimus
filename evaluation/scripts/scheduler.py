#!/usr/bin/env python3
"""
Scheduler - Manages the nightly evaluation schedule and cron setup.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Optional


class EvaluationScheduler:
    """Manages the evaluation schedule."""
    
    CRON_COMMENT = "# Pi Agent Optimus Evaluation"
    CRON_ENTRY = "0 3 * * * cd {eval_dir} && python3 scripts/orchestrator.py --schedule >> {log_file} 2>&1"
    
    def __init__(self):
        self.script_dir = Path(__file__).parent.parent
        self.eval_dir = self.script_dir.absolute()
        self.log_file = self.eval_dir / "evaluation.log"
    
    def setup(self):
        """Set up cron job for nightly evaluation."""
        
        print("🔧 Setting up Pi Agent Optimus evaluation schedule...")
        
        # Check if cron is available
        if not self._is_cron_available():
            print("❌ Cron is not available on this system.")
            print("   You can still run evaluations manually with:")
            print(f"   python3 {self.eval_dir}/scripts/orchestrator.py run --full")
            return False
        
        # Get existing crontab
        existing_cron = self._get_crontab()
        
        # Remove any existing evaluation entries
        new_cron = self._remove_evaluation_entries(existing_cron)
        
        # Add new entry
        entry = self._build_cron_entry()
        
        if entry:
            new_cron += "\n" + entry
        
        # Install new crontab
        self._install_crontab(new_cron)
        
        print(f"✅ Nightly evaluation scheduled for 3:00 AM")
        print(f"   Log file: {self.log_file}")
        print(f"\n   To run manually:")
        print(f"   python3 {self.eval_dir}/scripts/orchestrator.py run --full")
        
        return True
    
    def remove(self):
        """Remove the scheduled evaluation."""
        
        existing_cron = self._get_crontab()
        new_cron = self._remove_evaluation_entries(existing_cron)
        
        if existing_cron != new_cron:
            self._install_crontab(new_cron)
            print("✅ Scheduled evaluation removed.")
        else:
            print("No scheduled evaluation found.")
    
    def status(self) -> Dict[str, any]:
        """Check current schedule status."""
        
        existing_cron = self._get_crontab()
        
        entry = self._find_evaluation_entry(existing_cron)
        
        if entry:
            return {
                "scheduled": True,
                "entry": entry,
                "log_file": str(self.log_file)
            }
        else:
            return {
                "scheduled": False,
                "entry": None
            }
    
    def _is_cron_available(self) -> bool:
        """Check if cron daemon is available."""
        
        # Check if crontab command exists
        if os.system("which crontab > /dev/null 2>&1") != 0:
            return False
        
        # Check if cron is running (optional)
        # We don't fail if cron isn't running, just warn
        
        return True
    
    def _get_crontab(self) -> str:
        """Get current crontab content."""
        
        import subprocess
        
        try:
            result = subprocess.run(
                ["crontab", "-l"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return result.stdout
            else:
                return ""
        except Exception:
            return ""
    
    def _install_crontab(self, content: str):
        """Install a new crontab."""
        
        import subprocess
        
        try:
            result = subprocess.run(
                ["crontab", "-"],
                input=content,
                text=True,
                capture_output=True
            )
            
            if result.returncode != 0:
                print(f"⚠️  Warning: Could not install crontab: {result.stderr}")
        except Exception as e:
            print(f"⚠️  Warning: Could not install crontab: {e}")
    
    def _remove_evaluation_entries(self, cron: str) -> str:
        """Remove evaluation entries from crontab."""
        
        lines = []
        
        in_evaluation_block = False
        
        for line in cron.split("\n"):
            if self.CRON_COMMENT in line:
                in_evaluation_block = True
                continue
            elif in_evaluation_block and line.strip() == "":
                in_evaluation_block = False
                continue
            elif in_evaluation_block:
                continue
            
            if line.strip():
                lines.append(line)
        
        return "\n".join(lines) + "\n"
    
    def _build_cron_entry(self) -> str:
        """Build the cron entry string."""
        
        entry = self.CRON_ENTRY.format(
            eval_dir=self.eval_dir,
            log_file=self.log_file
        )
        
        return f"{self.CRON_COMMENT}\n{entry}"
    
    def _find_evaluation_entry(self, cron: str) -> Optional[str]:
        """Find the evaluation entry in crontab."""
        
        lines = cron.split("\n")
        
        in_block = False
        entry_lines = []
        
        for line in lines:
            if self.CRON_COMMENT in line:
                in_block = True
                continue
            elif in_block and line.strip():
                entry_lines.append(line)
            elif in_block and not line.strip():
                break
        
        return "\n".join(entry_lines) if entry_lines else None


def main():
    """Command-line interface."""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Manage evaluation schedule")
    parser.add_argument("action", choices=["setup", "remove", "status"],
                       help="Action to perform")
    
    args = parser.parse_args()
    
    scheduler = EvaluationScheduler()
    
    if args.action == "setup":
        scheduler.setup()
    elif args.action == "remove":
        scheduler.remove()
    elif args.action == "status":
        status = scheduler.status()
        if status["scheduled"]:
            print("✅ Evaluation is scheduled")
            print(f"   Entry: {status['entry']}")
            print(f"   Log: {status['log_file']}")
        else:
            print("❌ No evaluation scheduled")
            print(f"   Run 'scheduler.py setup' to schedule nightly evaluation")


if __name__ == "__main__":
    main()