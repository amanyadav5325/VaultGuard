"""
VaultGuard - Strong Password Generator
Generates cryptographically secure random passwords.
"""

import secrets
import string
from typing import Optional


WORD_LIST = [
    "apple", "brave", "cloud", "dance", "eagle", "flame", "grace", "honey",
    "ivory", "joker", "karma", "lunar", "mango", "ninja", "ocean", "piano",
    "queen", "river", "storm", "tiger", "ultra", "vigor", "waltz", "xenon",
    "yacht", "zebra", "amber", "blaze", "cedar", "dwarf", "elbow", "frost",
    "globe", "haste", "index", "jewel", "kneel", "lemon", "maple", "north",
    "orbit", "pixel", "quirk", "razor", "solar", "tower", "umbra", "vault",
    "witch", "xenon", "youth", "zonal", "crane", "drake", "ember", "fable",
    "grind", "haven", "irony", "jumbo", "kiosk", "lodge", "manor", "noble",
]

SYMBOLS = "!@#$%^&*()-_=+[]{}|;:,.<>?"


def generate_password(
    length: int = 16,
    use_upper: bool = True,
    use_lower: bool = True,
    use_digits: bool = True,
    use_special: bool = True,
    exclude_ambiguous: bool = False
) -> str:
    """Generate a cryptographically secure random password."""
    charset = ""

    if use_lower:
        charset += string.ascii_lowercase
    if use_upper:
        charset += string.ascii_uppercase
    if use_digits:
        charset += string.digits
    if use_special:
        charset += SYMBOLS

    if exclude_ambiguous:
        for ch in "Il1O0oB8":
            charset = charset.replace(ch, "")

    if not charset:
        charset = string.ascii_letters + string.digits

    # Ensure at least one character from each required set
    required = []
    if use_lower:
        lower_chars = string.ascii_lowercase
        if exclude_ambiguous:
            lower_chars = ''.join(c for c in lower_chars if c not in "Il1O0oB8")
        required.append(secrets.choice(lower_chars))
    if use_upper:
        upper_chars = string.ascii_uppercase
        if exclude_ambiguous:
            upper_chars = ''.join(c for c in upper_chars if c not in "Il1O0oB8")
        required.append(secrets.choice(upper_chars))
    if use_digits:
        digit_chars = string.digits
        if exclude_ambiguous:
            digit_chars = ''.join(c for c in digit_chars if c not in "Il1O0oB8")
        required.append(secrets.choice(digit_chars))
    if use_special:
        required.append(secrets.choice(SYMBOLS))

    # Fill remaining length
    remaining_length = max(length - len(required), 0)
    password_chars = required + [secrets.choice(charset) for _ in range(remaining_length)]

    # Shuffle securely
    secrets.SystemRandom().shuffle(password_chars)
    return ''.join(password_chars[:length])


def generate_passphrase(
    word_count: int = 4,
    separator: str = "-",
    capitalize: bool = True,
    add_number: bool = True,
    add_symbol: bool = True
) -> str:
    """Generate a memorable passphrase from random words."""
    words = [secrets.choice(WORD_LIST) for _ in range(word_count)]

    if capitalize:
        words = [w.capitalize() for w in words]

    phrase = separator.join(words)

    if add_number:
        phrase += separator + str(secrets.randbelow(9000) + 1000)

    if add_symbol:
        phrase += secrets.choice("!@#$%&*")

    return phrase


def generate_pin(length: int = 6) -> str:
    """Generate a numeric PIN."""
    return ''.join([str(secrets.randbelow(10)) for _ in range(length)])


def generate_memorable(length: int = 12) -> str:
    """Generate a pronounceable/memorable password."""
    vowels = "aeiou"
    consonants = "bcdfghjklmnpqrstvwxyz"
    password = []

    for i in range(length):
        if i % 2 == 0:
            password.append(secrets.choice(consonants))
        else:
            password.append(secrets.choice(vowels))

    # Add uppercase, digit, symbol
    if len(password) >= 3:
        password[0] = password[0].upper()
        password[-1] = str(secrets.randbelow(10))
        password[-2] = secrets.choice(SYMBOLS[:10])

    secrets.SystemRandom().shuffle(password)
    return ''.join(password[:length])
