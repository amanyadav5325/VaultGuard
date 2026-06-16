"""
VaultGuard - Password Strength Analyzer
Analyzes password strength and provides detailed feedback.
"""

import re
import math
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class AnalysisResult:
    score: int          # 0-100
    strength: str       # Weak / Fair / Strong / Very Strong
    entropy: float      # Bits of entropy
    issues: List[str]
    suggestions: List[str]
    color: str          # Hex color for UI
    crack_time: str     # Estimated crack time


COMMON_PASSWORDS = {
    "password", "123456", "password1", "qwerty", "abc123",
    "letmein", "monkey", "1234567890", "dragon", "master",
    "123456789", "welcome", "login", "admin", "passw0rd",
    "iloveyou", "sunshine", "princess", "football", "shadow",
    "superman", "michael", "charlie", "donald", "password123"
}


def calculate_entropy(password: str) -> float:
    """Calculate Shannon entropy of the password."""
    charset_size = 0
    if re.search(r'[a-z]', password):
        charset_size += 26
    if re.search(r'[A-Z]', password):
        charset_size += 26
    if re.search(r'\d', password):
        charset_size += 10
    if re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?`~]', password):
        charset_size += 32
    if charset_size == 0:
        return 0.0
    return len(password) * math.log2(charset_size)


def estimate_crack_time(entropy: float) -> str:
    """Estimate time to crack based on entropy (assuming 10B guesses/sec)."""
    guesses_per_sec = 1e10
    seconds = (2 ** entropy) / guesses_per_sec

    if seconds < 1:
        return "Instantly"
    elif seconds < 60:
        return f"{int(seconds)} seconds"
    elif seconds < 3600:
        return f"{int(seconds/60)} minutes"
    elif seconds < 86400:
        return f"{int(seconds/3600)} hours"
    elif seconds < 2592000:
        return f"{int(seconds/86400)} days"
    elif seconds < 31536000:
        return f"{int(seconds/2592000)} months"
    elif seconds < 3.154e9:
        return f"{int(seconds/31536000)} years"
    elif seconds < 3.154e12:
        return f"{int(seconds/3.154e9)} thousand years"
    else:
        return "Millions of years"


def analyze(password: str) -> AnalysisResult:
    """Full password strength analysis."""
    issues = []
    suggestions = []
    score = 0

    # --- Length check ---
    length = len(password)
    if length == 0:
        return AnalysisResult(0, "None", 0.0, ["Password is empty"], [], "#555555", "N/A")

    if length < 8:
        issues.append("Too short (minimum 8 characters)")
        suggestions.append("Use at least 8 characters; 14+ is recommended")
        score += 5
    elif length < 12:
        score += 15
        suggestions.append("Consider using 14+ characters for stronger security")
    elif length < 16:
        score += 25
    else:
        score += 35

    # --- Complexity checks ---
    has_lower = bool(re.search(r'[a-z]', password))
    has_upper = bool(re.search(r'[A-Z]', password))
    has_digit = bool(re.search(r'\d', password))
    has_special = bool(re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?`~]', password))

    if not has_lower:
        issues.append("No lowercase letters")
        suggestions.append("Add lowercase letters (a-z)")
    else:
        score += 10

    if not has_upper:
        issues.append("No uppercase letters")
        suggestions.append("Add uppercase letters (A-Z)")
    else:
        score += 10

    if not has_digit:
        issues.append("No numbers")
        suggestions.append("Add numbers (0-9)")
    else:
        score += 10

    if not has_special:
        issues.append("No special characters")
        suggestions.append("Add special characters (!@#$%^&*...)")
    else:
        score += 15

    # --- Common password check ---
    if password.lower() in COMMON_PASSWORDS:
        issues.append("This is a commonly used password")
        suggestions.append("Avoid common passwords — use a random passphrase instead")
        score = max(0, score - 30)

    # --- Pattern checks ---
    if re.search(r'(.)\1{2,}', password):
        issues.append("Contains repeated characters (e.g., aaa, 111)")
        suggestions.append("Avoid repeating the same character multiple times")
        score = max(0, score - 10)

    if re.search(r'(012|123|234|345|456|567|678|789|890|abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)', password.lower()):
        issues.append("Contains sequential characters (e.g., abc, 123)")
        suggestions.append("Avoid sequential patterns like 'abc' or '123'")
        score = max(0, score - 10)

    if re.search(r'(qwerty|asdf|zxcv|qazwsx|qweasd)', password.lower()):
        issues.append("Contains keyboard pattern (e.g., qwerty)")
        suggestions.append("Avoid keyboard walk patterns")
        score = max(0, score - 10)

    # Clamp score
    score = min(100, max(0, score))

    # Determine strength label and color
    if score < 25:
        strength, color = "Weak", "#E74C3C"
    elif score < 50:
        strength, color = "Fair", "#E67E22"
    elif score < 75:
        strength, color = "Strong", "#2ECC71"
    else:
        strength, color = "Very Strong", "#1ABC9C"

    entropy = calculate_entropy(password)
    crack_time = estimate_crack_time(entropy)

    return AnalysisResult(
        score=score,
        strength=strength,
        entropy=round(entropy, 1),
        issues=issues,
        suggestions=suggestions,
        color=color,
        crack_time=crack_time
    )
