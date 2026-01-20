# D7M Announcer Bot

A specialized Discord bot that converts owner messages into premium-styled embeds in specific channels. It supports advanced formatting, dynamic coloring, and interaction via **Direct Messages**.

## ✨ Features

- **DM-to-Channel Workflow**: Control everything from the bot's DMs. No need to clutter server channels with commands.
- **Fuzzy Channel Search**: Just type `channel: updates` and the bot finds `#📢updates` automatically.
- **Dynamic Configuration**: Control the embed directly from your message text:
    - **Mentions**: `mention: Gamers, Updates` (pings roles by name).
    - **Colors**: `color: red`, `0x5865F2`, etc.
    - **Buttons**: `button: Visit Site | https://example.com`.
- **Preview Mode**: `preview: true` shows you exactly what the embed looks like and **confirms the target channel** before sending.
- **Scheduling**: `schedule: 2h` to automatically post the announcement later.
- **Polls**: `poll: true` adds reaction votes.
- **Reply to Edit**: Notice a typo? Simply **Reply** to the bot's embed (in the server) with the corrected text to edit it instantly.

## 🚀 Setup

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Environment Configuration**:
    Create a `.env` file:
    ```ini
    DISCORD_TOKEN=your_bot_token_here
    OWNER_ID=your_discord_user_id
    ```

3.  **Run**:
    ```bash
    python announcerbot.py
    ```

## 📝 Usage Guide

Send a **Direct Message** to the bot with your announcement content and configuration keys. Keys are removed from the final message.

### Basic Example
```text
channel: general
color: blue
mention: everyone
Hello team, meeting in 5 minutes!
```

### Advanced Example
```text
channel: announcements
color: 0xF1C40F
mention: Gamers
preview: true
button: Event Page | https://google.com
poll: true
schedule: 30m

# 🏆 Big Tournament!

We are hosting a massive event tonight.
Click the button below to register!
```

### Available Keys
| Key | Description | Example |
| :--- | :--- | :--- |
| `channel: name` | Target channel (fuzzy match) | `channel: updates` |
| `color: value` | Embed color | `color: red` or `color: 0xFF5500` |
| `mention: roles`| Ping roles by name | `mention: Admins, Mods` |
| `everyone: true`| Legacy everyone ping | `everyone: true` |
| `button: L\|U` | Add Link Button | `button: Vote | https://...` |
| `poll: true` | Add ✅ ❌ reactions | `poll: true` |
| `schedule: time`| Delay posting | `schedule: 1h 30m` |
| `preview: true` | Monitor only (no send) | `preview: true` |
