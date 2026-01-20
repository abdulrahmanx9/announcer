# 📢 D7M Announcer Bot

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Discord.py](https://img.shields.io/badge/discord.py-2.0+-5865F2.svg)](https://discordpy.readthedocs.io/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A professional, premium-grade **Discord Announcement Bot** designed for owners who demand quality. Control everything via Direct Messages, use intelligent channel search, and send sleek, styled embeds without ever typing a command in your server.

**[View Demo / Report Issues](https://github.com/abdulrahmanx9/announcer/issues)**

---

## ✨ Why D7M Announcer?

Most bots require complex commands like `/announce channel:#general title:hello...`.
**D7M Announcer** changes the game:

*   **🕵️ Stealthy Workflow**: You DM the bot. It posts in the server. No one sees you typing commands.
*   **🧠 Fuzzy Search**: Forgot if it's `#announcements` or `#server-news`? Just type `channel: news` and the bot figures it out.
*   **🎨 Dynamic Styling**: Set colors, ping roles by name, and attach polls on the fly using simple keys.
*   **⚡ Productivity**: Schedule posts for later, add interactive buttons, and preview everything before it goes live.

## 🚀 Key Features

*   **DM-to-Channel Architecture**: Keep your admin channels clean.
*   **Smart Mention System**: `mention: Gamers` finds the `@Gamers` role automatically.
*   **Rich Media Support**: Images attached to your DM are auto-formatted and sent as high-quality attachments.
*   **Interactive Elements**: Easily add **Link Buttons** and **Polls** (Reaction voting).
*   **Safety First**: `preview: true` lets you see exactly what will be sent (and where) before you pull the trigger.
*   **Reply-to-Edit**: Made a typo in a live announcement? Just **reply** to the bot's message with the fix. 🛠️

---

## � Usage Guide

Everything is controlled via **keys** in your message. Keys are stripped out, leaving only your beautiful content.

### 1. The Simple Announcement
**You send this (in DM):**
```yaml
channel: distinct
color: blue
mention: everyone

Server restart in 10 minutes! Please save your work.
```

**The Bot posts this:**
> **@everyone**
> [Blue Vertical Bar]
> **Server restart in 10 minutes! Please save your work.**
> *Footer: D7M Announcement • Today at 12:00 PM*

---

### 2. The "Power User" Announcement
**You send this:**
```yaml
channel: updates
color: 0xF1C40F
mention: VIP, Moderators
schedule: 1h
button: View Changelog | https://your-site.com
poll: true
preview: true

# � Version 2.0 Released!

We have updated the server with new maps and weapons.
Check out the link below for full details.
```

*The bot will reply to you with a **Preview**, verify the channel `#updates`, and confirm it will auto-post in **1 hour**.*

---

## 🔧 Configuration Keys based Cheat Sheet

| Key | Description | Example |
| :--- | :--- | :--- |
| `channel: name` | **Required**. Target channel name (fuzzy matched). | `channel: news` |
| `color: value` | Embed color (Name or Hex). | `color: red` / `color: 0xFF0000` |
| `mention: roles` | Ping roles by name (comma separated). | `mention: Admins, Mods` |
| `everyone: true` | Pings `@everyone` (spoiler formatted). | `everyone: true` |
| `button: L\|U` | Adds a clickable link button. | `button: Vote | https://...` |
| `poll: true` | Adds ✅ ❌ reactions for voting. | `poll: true` |
| `schedule: time` | Delays posting by X time. | `schedule: 30m` / `1h` |
| `preview: true` | Sends a preview to you (does not post). | `preview: true` |

---

## 🛠️ Installation & Setup

### Prerequisites
*   Python 3.10+
*   A Discord Bot Token ([Get one here](https://discord.com/developers/applications))
*   Privileged Intents enabled (Message Content, Guilds, Members)

### Steps

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/abdulrahmanx9/announcer.git
    cd announcer
    ```

2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment**
    Create a `.env` file in the root directory:
    ```ini
    DISCORD_TOKEN=your_bot_token_here
    OWNER_ID=your_discord_user_id
    ```

4.  **Run the Bot**
    ```bash
    python announcerbot.py
    ```

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!
Feel free to check the [issues page](https://github.com/abdulrahmanx9/announcer/issues).

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

*Made with ❤️ by [Abdulrahman](https://github.com/abdulrahmanx9)*
