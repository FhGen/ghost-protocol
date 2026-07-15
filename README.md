# Ghost Protocol — Absolute macOS Privacy & Anti-Forensics Suite

Ghost Protocol is a high-security local privacy dashboard, system hardening utility, and anti-forensics console tailored specifically for macOS. It provides a suite of advanced operations to audit, scrub, and protect your digital footprint.

---

## 🛠️ System Architecture

Ghost Protocol is structured into three distinct operational domains: **User Interface & Graphics Engine**, **Hardened Anonymous Routing (Tor Engine)**, and **Local Privacy & Clean-Up Routines**.

```
                  ┌──────────────────────┐
                  │ Ghost Protocol GUI   │
                  └──────────┬───────────┘
                             │ (Refreshes exit nodes / Selects filters)
                             ▼
                  ┌──────────────────────┐
                  │ Onionoo metrics API  │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │  Dynamic torrc File  │
                  └──────────┬───────────┘
                             │
                             ▼
 ┌───────────────┐ ┌───────────────────┐ ┌───────────────┐
 │ Exclude 5-Eyes│ │ Safe SOCKS/Daemon │ │ Strict Routing│
 └───────┬───────┘ └─────────┬─────────┘ └───────┬───────┘
         │                   │                   │
         └─────────────┐     ▼     ┌─────────────┘
                       ▼           ▼
                  ┌──────────────────────┐
                  │    Local Tor Daemon  │
                  └──────────┬───────────┘
                             │ (Binds to SOCKS port 9050)
                             ▼
                  ┌──────────────────────┐
                  │ networksetup SOCKS   │
                  │ (System-wide Routing)│
                  └──────────────────────┘
```

---

## 1. User Interface & Graphics Engine
The visual theme is custom-built on top of Tkinter's basic Canvas renderer using customized styling properties to simulate a modern, hardware-accelerated dark visual aesthetic (e.g. rounded border tabs, card elevations, toggle switches, and glowing active states).

### Custom Canvas Widgets
*   **`GhostButton`**: Implements custom polygon drawing via `create_polygon`. It handles mouse hover transitions (`<Enter>`, `<Leave>`) dynamically, swapping the interior fill and outline color to generate a premium hover-glow state.
*   **`ToggleSwitch`**: A custom-drawn switch mimicking modern native toggle elements. Uses linear animation displacement (`dx = target - current / steps`) over a thread timer interval to slide the toggle knob smoothly between active and inactive states.
*   **`StatusDot`**: A lightweight canvas drawing widget displaying real-time operational feedback (green/red dot) matching the local Tor daemon states.
*   **`_left_scroll_handler`**: Overrides default mousewheel delta behavior to prevent global scrolling hijacks and support smooth trackpad/mouse scroll wheel interpolation on macOS.

### Layout & Navigation
*   **Tabbed Interface**: The right panel maps frames dynamically (`self._tab_frames`) when switching tabs, providing single-pane window navigation between Console, Tor Config, and Shredder.
*   **Colored Audit Trail**: Logs are piped to a custom `tk.Text` element configured with tagging parameters to dynamically color output strings depending on success, warning, or error signals.

---

## 2. Hardened Anonymous Routing (Tor Engine)
This subsystem handles the initialization, configuration template generation, and management of the local Tor process, along with binding macOS proxy configurations.

*   **Exit Node Resolver**: Connects to the Tor Metrics API (`Onionoo`) asynchronously to fetch the top 50 active exit relays sorted by consensus weight. Details are parsed into country codes and mapped to their exact 40-character fingerprints.
*   **`torrc` Generation**: Translates UI toggle configurations into strict configuration directives:
    *   `Exclude 5-Eyes`: Resolves US, UK, CA, AU, NZ country codes (`{us},{gb},{ca},{au},{nz}`) and maps them to `ExcludeNodes` and `ExcludeExitNodes`.
    *   `Safe SOCKS`: Disables unsafe DNS resolutions by writing `SafeSocks 1` and `TestSocks 1`.
    *   `Daemon Hardening`: Generates configuration blocks enabling `SafeLogging 1`, `DisableDebuggerAttachment 1` (blocking `ptrace` attachments), and blocks internal address proxy requests (`ClientRejectInternalAddresses`).
*   **macOS Network Integration**: Automates `networksetup` system calls to query active network adapters (`-listallnetworkservices`) and apply system-wide SOCKS proxy settings redirection to the local loopback interface (`127.0.0.1:9050`).

---

## 3. Local Privacy & Anti-Forensics Clean-Up
Automates sanitization runs to clean local application footprints and scrub metadata records from storage blocks.

*   **DNS & RAM Purger**: Issues `dscacheutil -flushcache` and signals `mDNSResponder` to drop resolved hostname tables. A subsystem call triggers macOS `purge` to clear volatile inactive memory buffers.
*   **Terminal History Cleaner**: Wipes command files across primary shells (Bash, Zsh, Sh, Python, and SQLite command buffers) by truncating target files on disk.
*   **Browser Nuker**: Performs structural detection of history, session caches, and SQL cookie stores for Safari, Google Chrome, Mozilla Firefox, and Brave Browser. If active instances are running, it blocks cleaning to prevent data corruption.
*   **Anti-Forensics Secure File Shredder**: Securely overwrites file buffers (1-pass Fast, 3-pass DoD Standard, 7-pass Gutmann, or 35-pass Maximum), renames them to random strings, and deletes them to prevent forensic recovery.
*   **EXIF Metadata Stripper**: Reads raw image byte structures to detect JPEG and PNG markers. For JPEGs, it parses markers segment-by-segment and strips application markers (`APP0` through `APP15` segments which contain EXIF data, GPS coordinates, and camera profiles) while preserving the basic image array segments.
*   **Emergency Panic**: Triggers instant memory scrubbing, clears the OS clipboard memory buffer, resets SOCKS firewall routing states, kills the local Tor sub-daemon, and closes the application instantly.

---

## 🚀 Getting Started

### Requirements
- **Platform**: macOS (built to interface with native tools like `networksetup`, `mdutil`, `wdutil`, and `/usr/sbin/purge`).
- **Core Dependencies**: Python 3.10+, Tkinter.
- **Tor Integration**: Requires Tor binary (`brew install tor`).

### Dynamic Privilege Elevation
The application utilizes AppleScript system elevation dialogs (`osascript -e "do shell script with administrator privileges"`) to authenticate specific administrative tasks. This allows you to run the GUI program normally as a standard user, prompting Touch ID or your password only when necessary (e.g. for `/etc/hosts` changes).
