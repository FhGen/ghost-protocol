# Ghost Protocol — macOS Privacy, Anti-Forensics & Secure Tor Routing Suite

Ghost Protocol is a high-security, local privacy dashboard, system hardening utility, and anti-forensics console tailored specifically for macOS. It provides a suite of advanced operations to audit, scrub, and protect your digital footprint.

---

## 🛠️ System Architecture

Ghost Protocol is structured into four distinct operational domains: **User Interface & Graphics Engine**, **Hardened Anonymous Routing (Tor Engine)**, **Local Privacy & Clean-Up Routines**, and **Anti-Forensics & Shredder Subsystems**.

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
                  │    Local Tor Daemon  │ (Autodetects or binds to port 9050)
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
*   **Colored Audit Trail**: Logs are piped to a custom `tk.Text` element configured with tagging parameters to dynamically color output strings depending on success, warning, or error signals. Starts in a read-only (`DISABLED`) state to protect audit integrity.

---

## 2. Hardened Anonymous Routing (Tor Engine)
This subsystem handles the initialization, configuration template generation, SOCKS5 validation, and management of the local Tor process, along with binding macOS proxy configurations.

*   **Smart SOCKS5 Port Binding**: Before spawning a local daemon, Ghost Protocol checks if port `9050` is active. If occupied, it initiates a SOCKS5 handshake. If verified as an active Tor proxy, it seamlessly reuses the connection, preventing double-binding conflicts.
*   **Exit Node Resolver**: Connects to the Tor Metrics API (`Onionoo`) asynchronously to fetch the top 50 active exit relays sorted by consensus weight. Details are parsed into country codes and mapped to their exact 40-character fingerprints.
*   **`torrc` Generation**: Translates UI toggle configurations into strict configuration directives:
    *   `Exclude 5-Eyes`: Resolves US, UK, CA, AU, NZ country codes (`{us},{gb},{ca},{au},{nz}`) and maps them to `ExcludeNodes` and `ExcludeExitNodes`.
    *   `Safe SOCKS`: Disables unsafe DNS resolutions by writing `SafeSocks 1` and `TestSocks 1`.
    *   `Daemon Hardening`: Generates configuration blocks enabling `SafeLogging 1`, `DisableDebuggerAttachment 1` (blocking `ptrace` attachments), and blocks internal address proxy requests (`ClientRejectInternalAddresses`).
*   **Control Port IP Switching (NEWNYM)**: When requesting a **🔄 NEW IP**, the suite communicates with the Tor Control Port (`9051`) using a random session-generated authentication password or reading Mac Homebrew cookie files (`control_auth_cookie`), sending a `SIGNAL NEWNYM` request. It displays a real-time countdown as the circuit rebuilds.

---

## 3. Local Privacy & Anti-Forensics Clean-Up
Automates sanitization runs to clean local application footprints and scrub metadata records from storage blocks.

*   **DNS & RAM Purger**: Issues `dscacheutil -flushcache` and signals `mDNSResponder` to drop resolved hostname tables. A subsystem call triggers macOS `purge` to clear volatile inactive memory buffers.
*   **Terminal History Cleaner**: Wipes command files across primary shells (Bash, Zsh, Sh, Python, and SQLite command buffers) by truncating target files on disk.
*   **Multi-Tiered Browser Force-Quit**: If active browsers (Safari, Google Chrome, Firefox, Brave Browser) are running during cleanup, the engine prompts the user and escalates closure:
    1. Sends graceful AppleScript `quit` events to preserve application state.
    2. Escalates to `pkill -9 -x` (exact case-sensitive matching).
    3. Triggers `killall -9`.
    4. Automatically kills underlying WebKit/Chrome helper sub-daemons.
*   **TCC Permission Escalation**: When cleaning sandbox directories (such as Safari's protected `History.db`), standard permission blocks (`EPERM`) are handled by escalating the deletion run to admin `rm` via AppleScript. If system-level Full Disk Access is still missing, detailed setup guidance is logged in the console.

---

## 4. Anti-Forensics & Shredder Subsystems

*   **Secured File Overwriter**: Securely overwrites file buffers (1-pass Fast, 3-pass DoD Standard, 7-pass Gutmann, or 35-pass Maximum), renames them to random strings, and deletes them to prevent forensic recovery. The listbox is updated in sync to prevent file desync errors.
*   **Non-Blocking Directory Walk**: Scanning directories with large quantities of files runs entirely on a background thread. Found paths are queued and loaded in batches of 200 items into the Tkinter listbox using `after()` callbacks, preventing GUI freezes.
*   **EXIF & Metadata Stripper**:
    *   **JPEGs**: Parses image segments chunk-by-chunk and removes application metadata blocks (`APP0` through `APP15` segments containing EXIF data, GPS coordinates, and camera profiles).
    *   **PNGs**: Implements a custom PNG chunk layout parser. It reads the PNG 8-byte signature (`\x89PNG\r\n\x1a\n`) and filters out auxiliary metadata chunks (like `tEXt`, `zTXt`, `iTXt`, `eXIf`, `iCCP`) while preserving standard visual render chunks (`IHDR`, `PLTE`, `IDAT`, `IEND`, `tRNS`, `gAMA`, `cHRM`, `sRGB`).

---

## 🚀 Getting Started

### Requirements
- **Platform**: macOS (built to interface with native tools like `networksetup`, `mdutil`, `wdutil`, and `/usr/sbin/purge`).
- **Core Dependencies**: Python 3.10+, Tkinter.
- **Tor Integration**: Requires Tor binary (`brew install tor`).

### Execution
Run the unified script directly via your terminal:
```bash
python3 ghost_protocol.py
```
*Tip: Ensure you grant **Full Disk Access** to Terminal (or your packaged App) in System Settings to allow complete cleaning of browser cache data.*
