# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

"""
Scheduler

Schedule reminders and alerts.
"""

import json
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

STATE_FILE = Path("~/.pi/reminders.json").expanduser()


def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"active": [], "completed": []}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def show_notification(title: str, message: str) -> None:
    """Show system notification."""
    try:
        # Windows toast notification
        subprocess.run([
            "powershell", "-Command",
            f"[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null; "
            f"$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02); "
            f"$textNodes = $template.GetElementsByTagName('text'); "
            f"$textNodes.Item(0).AppendChild($template.CreateTextNode('{title}')) | Out-Null; "
            f"$textNodes.Item(1).AppendChild($template.CreateTextNode('{message}')) | Out-Null; "
            f"$toast = [Windows.UI.Notifications.ToastNotification]::new($template); "
            f"[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('pi').Show($toast)"
        ], capture_output=True)
    except Exception:
        print(f"📢 Reminder: {title} - {message}")


def parse_duration(duration: str) -> Optional[timedelta]:
    """Parse duration like '30m', '2h', '1d'."""
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    try:
        value = int(duration[:-1])
        unit = duration[-1].lower()
        if unit in units:
            return timedelta(seconds=value * units[unit])
    except (ValueError, IndexError):
        pass
    return None


def parse_datetime(dt_str: str) -> Optional[datetime]:
    """Parse datetime string."""
    formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d",
        "%H:%M"
    ]
    for fmt in formats:
        try:
            return datetime.fromisoformat(dt_str)
        except ValueError:
            try:
                return datetime.strptime(dt_str, fmt)
            except ValueError:
                pass
    return None


def add_reminder(message: str, scheduled: datetime, repeat: Optional[str] = None) -> dict:
    """Add a new reminder."""
    state = load_state()

    reminder = {
        "id": f"rem-{len(state['active']) + 1:03d}",
        "message": message,
        "scheduled": scheduled.isoformat(),
        "repeat": repeat
    }

    state["active"].append(reminder)
    save_state(state)

    return reminder


def list_reminders() -> dict:
    """List active reminders."""
    state = load_state()
    return {"active": state["active"], "count": len(state["active"])}


def cancel_reminder(rem_id: str) -> dict:
    """Cancel a reminder."""
    state = load_state()
    original = len(state["active"])

    state["active"] = [r for r in state["active"] if r["id"] != rem_id]
    removed = original > len(state["active"])

    if removed:
        save_state(state)

    return {"cancelled": removed, "id": rem_id}


def snooze_reminder(rem_id: str, by: timedelta) -> dict:
    """Snooze a reminder."""
    state = load_state()

    for reminder in state["active"]:
        if reminder["id"] == rem_id:
            current = datetime.fromisoformat(reminder["scheduled"])
            reminder["scheduled"] = (current + by).isoformat()
            save_state(state)
            return {"snoozed": True, "id": rem_id, "new_time": reminder["scheduled"]}

    return {"snoozed": False, "error": "Reminder not found"}


def check_reminders() -> list[dict]:
    """Check for due reminders and return them."""
    state = load_state()
    due = []
    now = datetime.now()

    for reminder in state["active"]:
        scheduled = datetime.fromisoformat(reminder["scheduled"])
        if scheduled <= now:
            due.append(reminder)

    return due


def process_reminders() -> None:
    """Process due reminders and show notifications."""
    due = check_reminders()

    if due:
        for reminder in due:
            show_notification("Reminder", reminder["message"])
            print(f"🔔 {reminder['message']}")

            # Move to completed or repeat
            state = load_state()
            state["active"].remove(reminder)

            if reminder.get("repeat"):
                # Re-add with repeat duration
                new_scheduled = datetime.now() + parse_duration(reminder["repeat"])
                reminder["scheduled"] = new_scheduled.isoformat()
                state["active"].append(reminder)
            else:
                state["completed"].append(reminder)

            save_state(state)


def run_scheduler(interval: int = 30) -> None:
    """Run scheduler loop."""
    print(f"Scheduler running (check every {interval}s). Press Ctrl+C to stop.")

    while True:
        process_reminders()
        time.sleep(interval)


def main():
    if len(sys.argv) < 2:
        print("Usage: schedule.py <command> [args]")
        print("Commands:")
        print("  remind <message> --in <duration>    Set reminder (e.g., '30m', '2h')")
        print("  remind <message> --at <time>      Set reminder at specific time")
        print("  list                                  List active reminders")
        print("  cancel <id>                           Cancel reminder")
        print("  snooze <id> --by <duration>           Snooze reminder")
        print("  run                                   Start scheduler loop")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "remind":
        if len(sys.argv) < 3:
            print("Error: specify reminder message")
            sys.exit(1)

        message = sys.argv[2]
        scheduled = None

        if "--in" in sys.argv:
            idx = sys.argv.index("--in")
            duration = sys.argv[idx + 1]
            delta = parse_duration(duration)
            if delta:
                scheduled = datetime.now() + delta
            else:
                print(f"Error: invalid duration '{duration}'")
                sys.exit(1)

        elif "--at" in sys.argv:
            idx = sys.argv.index("--at")
            time_str = sys.argv[idx + 1]
            parsed = parse_datetime(time_str)
            if parsed:
                scheduled = parsed
            else:
                print(f"Error: could not parse time '{time_str}'")
                sys.exit(1)

        else:
            print("Error: specify --in or --at")
            sys.exit(1)

        reminder = add_reminder(message, scheduled)
        print(f"✅ Reminder set: {reminder['id']} at {reminder['scheduled']}")

    elif cmd == "list":
        result = list_reminders()
        if result["count"] == 0:
            print("No active reminders.")
        else:
            print(f"Active reminders ({result['count']}):")
            for r in result["active"]:
                print(f"  {r['id']}: {r['message']} @ {r['scheduled']}")

    elif cmd == "cancel":
        if len(sys.argv) < 3:
            print("Error: specify reminder ID")
            sys.exit(1)

        rem_id = sys.argv[2]
        result = cancel_reminder(rem_id)
        if result["cancelled"]:
            print(f"✅ Cancelled: {rem_id}")
        else:
            print(f"Error: reminder {rem_id} not found")

    elif cmd == "snooze":
        if len(sys.argv) < 3:
            print("Error: specify reminder ID")
            sys.exit(1)

        rem_id = sys.argv[2]
        by = timedelta(minutes=15)  # Default

        if "--by" in sys.argv:
            idx = sys.argv.index("--by")
            duration = sys.argv[idx + 1]
            parsed = parse_duration(duration)
            if parsed:
                by = parsed
            else:
                print(f"Error: invalid duration '{duration}'")
                sys.exit(1)

        result = snooze_reminder(rem_id, by)
        if result["snoozed"]:
            print(f"✅ Snoozed: {rem_id} until {result['new_time']}")
        else:
            print(f"Error: {result.get('error', 'unknown error')}")

    elif cmd == "run":
        interval = 30
        if "--interval" in sys.argv:
            idx = sys.argv.index("--interval")
            interval = int(sys.argv[idx + 1])

        try:
            run_scheduler(interval)
        except KeyboardInterrupt:
            print("\nScheduler stopped.")

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
