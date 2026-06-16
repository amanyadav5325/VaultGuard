
https://github.com/user-attachments/assets/facff79d-7bf1-4214-a010-13b94163696a

# 🔐 VaultGuard — Password Manager

**VaultGuard** is a fully local, encrypted password manager with a beautiful dark-themed GUI built in Python + Tkinter.

---

## Features

| Phase | Feature | Status |
|-------|---------|--------|
| 1 | Password Strength Analyzer | ✅ |
| 2 | Strong Password Generator | ✅ |
| 3 | Encrypted Password Vault (SQLite3 + AES-256) | ✅ |
| 4 | Daily Automatic Password Rotation | ✅ |
| 5 | Beautiful Tkinter GUI | ✅ |

---

## Project Structure

```
VaultGuard/
├── main.py            # Main Tkinter GUI (run this)
├── analyzer.py        # Password strength analysis engine
├── generator.py       # Secure password/passphrase generator
├── encryptor.py       # AES-256 Fernet encryption with PBKDF2 key derivation
├── vault.py           # SQLite3 encrypted password vault
├── rotate.py          # Scheduled rotation engine
├── pyperclip_fallback.py
├── requirements.txt
├── README.md
└── data/
    ├── vault.db       # Encrypted SQLite database (auto-created)
    └── vault.salt     # Cryptographic salt (auto-created)
```

---

## Installation

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the app
python main.py
```

### Requirements
- Python 3.8+
- `cryptography` (AES-256 encryption)
- `schedule` (rotation scheduling)
- Tkinter (included with Python on Windows/macOS; `sudo apt install python3-tk` on Linux)

---

## Security Architecture

- **Encryption**: AES-256 via Fernet (from the `cryptography` library)
- **Key Derivation**: PBKDF2-HMAC-SHA256 with 480,000 iterations (OWASP recommended)
- **Salt**: 32-byte random salt stored separately from the database
- **Master Password**: Hashed with PBKDF2 for verification; never stored in plaintext
- **Storage**: All passwords encrypted before writing to SQLite3
- **Local Only**: No network connections; all data stays on your machine

---

## How to Use

### First Launch
1. Run `python main.py`
2. Create a strong master password (this encrypts everything)
3. You're in!

### Adding Passwords
- Click **+ Add Password** in the top bar
- Fill in the title, username, and password
- Use the **⚡** button to auto-generate a strong password
- Set a rotation interval (default: 90 days)

### Password Generator
- Switch to the **⚡ Generator** tab
- Choose type: Random, Passphrase, Memorable, or PIN
- Adjust length and options
- Click **Generate** then **Save to Vault**

### Password Analyzer
- Switch to the **🔍 Analyzer** tab
- Type or paste any password
- See real-time strength, entropy, crack time, and suggestions

### Password Rotation
- Switch to the **🔄 Rotation** tab
- See which passwords are overdue
- Rotate individually or use **Auto-Rotate Overdue**
- Background engine runs every hour and alerts you

---

## Password Strength Scoring

| Score | Label | Color |
|-------|-------|-------|
| 0–24 | Weak | 🔴 Red |
| 25–49 | Fair | 🟠 Orange |
| 50–74 | Strong | 🟢 Green |
| 75–100 | Very Strong | 💎 Teal |

---

## License
MIT License — for educational/personal use.
