"""
VaultGuard - Password Rotation Engine
Handles scheduled/automatic password rotation logic.
"""

import threading
import time
from datetime import datetime
from typing import Callable, Optional, List, Dict, Any
from generator import generate_password
from analyzer import analyze
import vault as db


class RotationEngine:
    """Background engine that checks for passwords due for rotation."""

    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._master_password: Optional[str] = None
        self._on_rotation_needed: Optional[Callable] = None
        self._check_interval = 3600  # Check every hour

    def start(self, master_password: str, on_rotation_needed: Callable):
        """Start the background rotation checker."""
        self._master_password = master_password
        self._on_rotation_needed = on_rotation_needed
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _run(self):
        while self._running:
            self._check_rotations()
            for _ in range(self._check_interval):
                if not self._running:
                    break
                time.sleep(1)

    def _check_rotations(self):
        try:
            overdue = db.get_entries_due_for_rotation()
            if overdue and self._on_rotation_needed:
                self._on_rotation_needed(overdue)
        except Exception:
            pass

    def auto_rotate(self, master_password: str, entry_ids: List[int],
                    length: int = 20) -> List[Dict[str, Any]]:
        """Auto-rotate specified entries with new strong passwords."""
        results = []
        for entry_id in entry_ids:
            new_pw = generate_password(
                length=length,
                use_upper=True,
                use_lower=True,
                use_digits=True,
                use_special=True
            )
            analysis = analyze(new_pw)
            success = db.rotate_password(
                master_password=master_password,
                entry_id=entry_id,
                new_password=new_pw,
                new_strength=analysis.score,
                reason="Auto-rotation (schedule)"
            )
            results.append({
                "entry_id": entry_id,
                "success": success,
                "new_password": new_pw,
                "new_strength": analysis.score,
                "rotated_at": datetime.now().isoformat()
            })
        return results


def get_rotation_status(entries: List[Dict]) -> List[Dict]:
    """Annotate entries with rotation status."""
    from datetime import datetime

    status_list = []
    for entry in entries:
        try:
            last_rotated = datetime.fromisoformat(entry.get("last_rotated", entry["created_at"]))
            days_ago = (datetime.now() - last_rotated).days
            interval = entry.get("rotation_interval_days", 90)
            days_remaining = interval - days_ago

            if days_remaining < 0:
                status = "overdue"
                status_label = f"Overdue by {abs(days_remaining)} days"
            elif days_remaining <= 7:
                status = "warning"
                status_label = f"Due in {days_remaining} days"
            else:
                status = "ok"
                status_label = f"{days_remaining} days remaining"
        except Exception:
            status = "unknown"
            status_label = "Unknown"
            days_ago = 0

        status_list.append({
            **entry,
            "rotation_status": status,
            "rotation_status_label": status_label,
            "days_since_rotation": days_ago
        })
    return status_list


# Singleton engine
engine = RotationEngine()
