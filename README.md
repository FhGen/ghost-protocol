# Ghost Protocol - Absolute macOS Privacy & Anti-Forensics Suite

Ghost Protocol is a high-security local privacy dashboard, system hardening utility, and anti-forensics console tailored specifically for macOS. It provides a suite of advanced operations to audit, scrub, and protect your digital footprint.

## Features

### 🖥️ High-Contrast Operational Audit Console
- Implements a retro-futuristic CRT style log console displaying timestamped events.
- Tracks all execution flows with detailed success/fail indicators.

### 🛡️ System Hardening & Telemetry blocking
- **Apple Telemetry Sinkholing**: Writes rules to `/etc/hosts` to block diagnostic connections (`telemetry.apple.com`, `metrics.apple.com`, `diagnostics.apple.com`, etc.).
- **Spotlight Shielding**: Instantly turns off Spotlight disk indexing via metadata utilities (`mdutil`).
- **Log Diagnostic Terminations**: Terminates OS tracking log processes (`CrashReporter`).

### 🧼 Footprint Sanitization & Metadata Scrubbing
- **Secure File Shredder**: Securely overwrites file buffers (1-pass Fast, 3-pass DoD Standard, 7-pass Gutmann, or 35-pass Maximum), renames them to random strings, and deletes them to prevent forensic recovery.
- **EXIF Image Stripper**: Scrubs digital metadata segments and headers from JPEG/PNG images.
- **Saved App States / Recent Items Purge**: Cleans macOS Application Support cached states, Finder folder recents, and document logs.
- **System Logs & Cache Sanitizer**: Wipes log events and system temp directories.
- **Command History Purge**: Sanitizes `.zsh_history`, `.bash_history`, and sqlite command logs.

### 🌐 Secure Networking & Anonymous Routing
- **Enforced Tor Traffic Routing**: Configures local SOCKS5 proxy configuration on network services and boots the Tor daemon background process.
- **Tor Exit Presets**: Dynamic `torrc` builder that allows choosing exit node country locations (US, DE, CH, IS, or Custom entries) and toggling strict nodes (`StrictNodes 1`).
- **DNS Resolver Flush**: Purges local DNS caches and resets multicast responder daemons.
- **Wi-Fi radio disassociation**: Sever Wi-Fi radio connection to prevent beacon tracking.

### 🚨 Emergency Panic Handshake
- Pressing `ESC` or clicking **PANIC SHUTDOWN** instantly erases the clipboard buffer, stops the Tor process, resets system proxy profiles, and destroys the GUI thread.

---

## Technical Architecture & Requirements

- **Platform**: macOS (built specifically to interface with `networksetup`, `mdutil`, `wdutil`, and native macOS configurations).
- **Core Dependencies**: Python 3, Tkinter.
- **Tor Integration**: Requires Tor binary (`brew install tor`).

### Dynamic Privilege Elevation
The application utilizes AppleScript system elevation dialogs (`osascript -e "do shell script with administrator privileges"`) to authenticate specific administrative tasks. This allows you to run the GUI program normally as a standard user, prompting Touch ID or your password only when necessary.
