import discord
from discord.ui import View, Button
import os
import logging
import asyncio
import re
import difflib
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import sqlite3
import json
from typing import Optional, Tuple, List, Dict, Any
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("AnnouncerBot")

# Load environment variables
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
try:
    OWNER_ID = int(os.getenv("OWNER_ID", 0))
except ValueError:
    logger.error("OWNER_ID must be an integer.")
    OWNER_ID = 0

DB_NAME = "announcements.db"
CAIRO_TZ = ZoneInfo("Africa/Cairo")

COLOR_MAP = {
    "red": 0xFF0000,
    "blue": 0x3498DB,
    "green": 0x2ECC71,
    "yellow": 0xF1C40F,
    "orange": 0xE67E22,
    "purple": 0x9B59B6,
    "black": 0x000000,
    "white": 0xFFFFFF,
    "gold": 0xF1C40F,
    "pink": 0xE91E63,
    "cyan": 0x00BCD4,
    "default": 0x2B2D31,
}


class DBHandler:
    """Context manager for SQLite database operations."""

    def __init__(self, db_name: str):
        self.db_name = db_name
        self.conn: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            if exc_type is None:
                self.conn.commit()
            self.conn.close()


def init_db():
    with DBHandler(DB_NAME) as db:
        db.cursor.execute("""CREATE TABLE IF NOT EXISTS scheduled (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        content TEXT,
                        run_at TIMESTAMP,
                        channel_name TEXT,
                        author_id INTEGER,
                        attachment_paths TEXT
                    )""")


class LinkButtonView(View):
    def __init__(self, buttons_config: List[Tuple[str, str]]):
        super().__init__()
        for label, url in buttons_config:
            self.add_item(Button(label=label, url=url))


class EmbedBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        intents.guilds = True
        intents.members = True  # Helpful for finding channels/users
        super().__init__(intents=intents)
        init_db()

    async def setup_hook(self):
        self.bg_task = self.loop.create_task(self._check_schedule_loop())

    async def on_ready(self):
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        user = await self.fetch_user(OWNER_ID)
        if user:
            await self._send_usage_guide(user)

    async def _send_usage_guide(self, user: discord.User):
        embed = discord.Embed(title="📢 D7M Announcer Utils", color=0x3498DB)
        embed.description = "I am ready! Send me a DM to make an announcement."
        embed.add_field(
            name="🔑 Configuration Keys",
            value=(
                "`channel: name` - Fuzzy search for target channel\n"
                "`color: red/hex` - Set embed color\n"
                "`mention: role` - Ping roles by name (comma separated)\n"
                "`everyone: true` - Ping @everyone\n"
                "`preview: true` - See it before sending (shows target)\n"
                "`poll: true` - Add vote reactions\n"
                "`schedule: 10m` - Delayed posting (10m, 1h, or YYYY-MM-DD HH:MM:SS)\n"
                "`list` - Show scheduled messages\n"
                "`edit: ID` - Edit a scheduled message\n"
                "`cancel: ID` - Cancel a scheduled message\n"
                "`button: Label | URL` - Add link buttons\n"
                "`template` - Get a copy-paste template\n"
                "`help` - Show this guide"
            ),
            inline=False,
        )
        embed.add_field(
            name="📝 Example",
            value=(
                "channel: general\n"
                "color: blue\n"
                "mention: Gamers, Updates\n"
                "button: Website | https://google.com\n"
                "poll: true\n"
                "Big news coming soon!"
            ),
            inline=False,
        )
        try:
            await user.send(embed=embed)
        except Exception:
            logger.warning("Could not send DM to owner. Make sure DMs are open.")

    def _parse_time_offset(self, time_str: str) -> int:
        """Parses 10m, 1h, 1d into seconds."""
        match = re.match(r"(\d+)([mhd])", time_str.lower())
        if not match:
            return 0
        value = int(match.group(1))
        unit = match.group(2)
        if unit == "m":
            return value * 60
        if unit == "h":
            return value * 3600
        if unit == "d":
            return value * 86400
        return 0

    def _parse_schedule_time(self, time_str: str) -> Optional[datetime]:
        """
        Parses 10m, 1h, 1d into a future datetime object (Cairo Time).
        Also accepts full 'YYYY-MM-DD HH:MM:SS' strings.
        Also accepts 'HH:MM:SS', 'HH:MM', 'HH:MM AM/PM' (assumes today/tomorrow).
        """
        now = datetime.now(CAIRO_TZ)

        # 1. Try full datetime
        try:
            naive_dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            dt = naive_dt.replace(tzinfo=CAIRO_TZ)
            if dt > now:
                return dt
            return None  # Past time
        except ValueError:
            pass

        # 2. Try time only (HH:MM:SS, HH:MM, 12-hour AM/PM)
        for fmt in ("%H:%M:%S", "%H:%M", "%I:%M:%S %p", "%I:%M %p"):
            try:
                naive_time = datetime.strptime(time_str.upper(), fmt).time()
                dt = datetime.combine(now.date(), naive_time).replace(tzinfo=CAIRO_TZ)
                if dt <= now:
                    dt += timedelta(days=1)
                return dt
            except ValueError:
                pass

        # 3. Try relative time
        seconds = self._parse_time_offset(time_str)
        if seconds > 0:
            return now + timedelta(seconds=seconds)

        return None

    def _find_channel(self, channel_name: str) -> Optional[discord.TextChannel]:
        """Fuzzy search for a channel across all guilds."""
        all_channels = []
        for guild in self.guilds:
            for channel in guild.text_channels:
                all_channels.append(channel)

        channel_map = {c.name.lower(): c for c in all_channels}
        matches = difflib.get_close_matches(
            channel_name.lower(), channel_map.keys(), n=1, cutoff=0.4
        )
        if matches:
            return channel_map[matches[0]]
        return None

    def _parse_content(self, content: str) -> Tuple[Dict[str, Any], str, str]:
        """
        Parses content for keys and separates description.
        Returns:
            config (dict): Parsed configuration
            outside_content (str): Content to outside the embed
            embed_description (str): Content inside the embed
        """
        content_lines = content.split("\n")
        embed_lines = []
        outside_lines = []

        config = {
            "color": 0x2B2D31,
            "everyone": False,
            "preview": False,
            "poll": False,
            "channel": None,
            "schedule": None,
            "buttons": [],
            "mentions": [],
        }

        for line in content_lines:
            clean_line = line.strip()
            lower_line = clean_line.lower()

            # Helper to safely extract value
            def get_val(prefix):
                try:
                    return clean_line.split(":", 1)[1].strip()
                except IndexError:
                    return ""

            if lower_line.startswith("channel:"):
                config["channel"] = get_val("channel:")
                continue

            if lower_line.startswith("mention:"):
                val = get_val("mention:")
                role_names = [r.strip() for r in val.split(",") if r.strip()]
                config["mentions"].extend(role_names)
                continue

            if lower_line.startswith("everyone:"):
                config["everyone"] = lower_line.split(":", 1)[1].strip() == "true"
                continue

            if lower_line.startswith("preview:"):
                config["preview"] = lower_line.split(":", 1)[1].strip() == "true"
                continue

            if lower_line.startswith("poll:"):
                config["poll"] = lower_line.split(":", 1)[1].strip() == "true"
                continue

            if lower_line.startswith("schedule:"):
                config["schedule"] = self._parse_schedule_time(get_val("schedule:"))
                continue

            if lower_line.startswith("color:"):
                val = get_val("color:")
                if val.lower() in COLOR_MAP:
                    config["color"] = COLOR_MAP[val.lower()]
                elif val.startswith("0x"):
                    try:
                        config["color"] = int(val, 16)
                    except ValueError:
                        pass
                continue

            if lower_line.startswith("button:"):
                # format: button: Label | URL
                val = get_val("button:")
                parts = val.split("|")
                if len(parts) >= 2:
                    config["buttons"].append((parts[0].strip(), parts[1].strip()))
                continue

            # Legacy mentions
            if "@everyone" in line or "@here" in line:
                outside_lines.append(line)
            else:
                embed_lines.append(line)

        if config["everyone"]:
            outside_lines.append("||@everyone||")

        return config, "\n".join(outside_lines), "\n".join(embed_lines)

    async def on_message(self, message: discord.Message):
        if message.author.id == self.user.id or message.author.id != OWNER_ID:
            return

        if isinstance(message.channel, discord.DMChannel):
            await self._handle_dm_announcement(message)
            return

        if message.reference:
            await self._handle_reply_edit(message)

    async def _handle_command_list(self, message: discord.Message):
        with DBHandler(DB_NAME) as db:
            db.cursor.execute(
                "SELECT id, channel_name, run_at FROM scheduled ORDER BY run_at ASC"
            )
            rows = db.cursor.fetchall()

        if not rows:
            await message.channel.send("📭 No scheduled announcements.")
            return

        text = "**📅 Scheduled Announcements:**\n"
        for r in rows:
            text += f"`#{r[0]}` | Channel: `{r[1]}` | Time: `{r[2]}`\n"
        await message.channel.send(text)

    async def _handle_command_cancel(self, message: discord.Message, arg: str):
        try:
            row_id = int(arg)
            with DBHandler(DB_NAME) as db:
                db.cursor.execute("DELETE FROM scheduled WHERE id = ?", (row_id,))
                deleted = db.cursor.rowcount > 0

            if deleted:
                await message.channel.send(f"✅ Cancelled announcement `{row_id}`.")
            else:
                await message.channel.send(f"⚠️ Could not find announcement `{row_id}`.")
        except ValueError:
            await message.channel.send("❌ Invalid ID.")

    async def _handle_dm_announcement(self, message: discord.Message):
        content_lower = message.content.lower().strip()

        if content_lower == "help":
            await self._send_usage_guide(message.author)
            return

        if content_lower == "template":
            template = (
                "channel: general\n"
                "color: blue\n"
                "mention: RoleName\n"
                "button: Click Me | https://example.com\n"
                "poll: true\n"
                "schedule: 10m\n"
                "\n"
                "Your message content here..."
            )
            await message.channel.send(
                f"Here is a template you can copy:\n```\n{template}\n```"
            )
            return

        if content_lower == "list":
            await self._handle_command_list(message)
            return

        if content_lower.startswith("cancel:"):
            arg = content_lower.split(":", 1)[1].strip()
            await self._handle_command_cancel(message, arg)
            return

        # Check for EDIT mode
        edit_id = None
        msg_content_without_cmd = message.content
        if content_lower.startswith("edit:"):
            try:
                first_line, remaining = message.content.split("\n", 1)
                edit_id = int(first_line.split(":", 1)[1].strip())
                msg_content_without_cmd = remaining
            except (ValueError, IndexError):
                await message.channel.send(
                    "❌ Invalid Edit format. Use `edit: ID` followed by content."
                )
                return

        config, outside_content, embed_description = self._parse_content(
            msg_content_without_cmd
        )

        # Prepare Embed
        embed = discord.Embed(
            description=embed_description if embed_description else None,
            color=config["color"],
            timestamp=datetime.now(),
        )
        embed.set_author(
            name=message.author.display_name, icon_url=message.author.display_avatar.url
        )
        embed.set_footer(text="D7M Announcement")

        view = LinkButtonView(config["buttons"]) if config["buttons"] else None

        # Handle Attachments
        discord_files = []
        saved_file_paths = []
        has_attachments = len(message.attachments) > 0

        if has_attachments:
            if config["schedule"] or edit_id:
                os.makedirs("attachments", exist_ok=True)
                for att in message.attachments:
                    safe_name = f"{int(datetime.now().timestamp())}_{att.filename}"
                    path = os.path.join("attachments", safe_name)
                    await att.save(path)
                    saved_file_paths.append(path)
            else:
                for att in message.attachments:
                    discord_files.append(await att.to_file())

        # Resolve Channel
        target_channel = None
        target_channel_info = "Not specified"
        if config["channel"]:
            target_channel = self._find_channel(config["channel"])
            target_channel_info = (
                target_channel.mention
                if target_channel
                else f"❌ (Could not find `{config['channel']}`)"
            )
        else:
            target_channel_info = "❌ (No channel specified)"

        # PREVIEW MODE
        if config["preview"]:
            await self._send_preview(
                message,
                target_channel_info,
                outside_content,
                embed,
                view,
                config,
                discord_files,
                saved_file_paths,
            )
            return

        # Validate Channel (if not preview)
        if not target_channel:
            msg = (
                f"❌ Could not find any channel matching `{config['channel']}`."
                if config["channel"]
                else "❌ Please specify a channel using `channel: name`."
            )
            await message.channel.send(msg)
            return

        # Resolve Mentions
        final_outside_content = await self._resolve_mentions(
            outside_content, config["mentions"], target_channel, message
        )

        # EDIT MODE
        if edit_id:
            await self._process_edit(
                edit_id,
                msg_content_without_cmd,
                config,
                saved_file_paths,
                has_attachments,
                old_att_paths_strategy="replace",
            )
            await message.channel.send(f"✅ Updated announcement `{edit_id}`!")
            return

        # SCHEDULE MODE
        if config["schedule"]:
            await self._schedule_message(
                message, config, saved_file_paths, target_channel
            )
            return

        # IMMEDIATE SEND
        await self._send_immediate(
            message,
            target_channel,
            final_outside_content,
            embed,
            view,
            discord_files,
            config["poll"],
        )

    async def _send_preview(
        self,
        message,
        target_channel_info,
        outside_content,
        embed,
        view,
        config,
        discord_files,
        saved_file_paths,
    ):
        preview_mentions = outside_content
        if config["mentions"]:
            preview_mentions += "\n(Mentions: " + ", ".join(config["mentions"]) + ")"

        await message.channel.send(
            f"👀 **Preview** for {target_channel_info}:", embed=embed, view=view
        )
        if preview_mentions.strip():
            await message.channel.send(preview_mentions)

        # Files in preview
        preview_files = []
        if saved_file_paths:
            for p in saved_file_paths:
                preview_files.append(discord.File(p))
        elif discord_files:
            preview_files = discord_files  # Reuse objects

        if preview_files:
            await message.channel.send(
                "*(Attachments included in preview)*", files=preview_files
            )

    async def _resolve_mentions(
        self, outside_content, mentions, target_channel, message
    ):
        if not mentions:
            return outside_content

        guild = target_channel.guild
        role_mentions = []
        role_map = {r.name.lower(): r for r in guild.roles}

        for role_name in mentions:
            found_role = role_map.get(role_name.lower())
            if not found_role:
                matches = difflib.get_close_matches(
                    role_name.lower(), role_map.keys(), n=1, cutoff=0.5
                )
                if matches:
                    found_role = role_map[matches[0]]

            if found_role:
                role_mentions.append(found_role.mention)
            else:
                await message.channel.send(
                    f"⚠️ Could not find role `{role_name}` in server `{guild.name}`."
                )

        if role_mentions:
            return (
                (outside_content + "\n" + " ".join(role_mentions))
                if outside_content
                else " ".join(role_mentions)
            )
        return outside_content

    async def _process_edit(
        self,
        edit_id,
        content,
        config,
        saved_file_paths,
        has_new_attachments,
        old_att_paths_strategy="replace",
    ):
        with DBHandler(DB_NAME) as db:
            db.cursor.execute(
                "SELECT content, run_at, attachment_paths FROM scheduled WHERE id = ?",
                (edit_id,),
            )
            row = db.cursor.fetchone()
            if not row:
                return  # Should handle cleaner but calling method checks existence? No it doesn't fully.

            old_raw, old_run_at, old_att_paths = row

            # Run At
            new_run_at = config["schedule"] if config["schedule"] else old_run_at
            run_at_str = (
                new_run_at
                if isinstance(new_run_at, str)
                else new_run_at.strftime("%Y-%m-%d %H:%M:%S")
            )

            # Attachments
            final_att_paths_json = old_att_paths
            if has_new_attachments:
                final_att_paths_json = json.dumps(saved_file_paths)
                if old_att_paths:
                    try:
                        old_paths = json.loads(old_att_paths)
                        for p in old_paths:
                            if os.path.exists(p):
                                os.remove(p)
                    except Exception:
                        pass

            db.cursor.execute(
                """UPDATE scheduled 
                                 SET content = ?, channel_name = ?, run_at = ?, attachment_paths = ? 
                                 WHERE id = ?""",
                (content, config["channel"], run_at_str, final_att_paths_json, edit_id),
            )

    async def _schedule_message(
        self, message, config, saved_file_paths, target_channel
    ):
        wait_time = config["schedule"]
        run_at_str = wait_time.strftime("%Y-%m-%d %H:%M:%S")
        att_paths_json = json.dumps(saved_file_paths) if saved_file_paths else None

        with DBHandler(DB_NAME) as db:
            db.cursor.execute(
                "INSERT INTO scheduled (content, run_at, channel_name, author_id, attachment_paths) VALUES (?, ?, ?, ?, ?)",
                (
                    message.content,
                    run_at_str,
                    config["channel"],
                    message.author.id,
                    att_paths_json,
                ),
            )
            new_id = db.cursor.lastrowid

        await message.channel.send(
            f"⏳ Scheduled `#{new_id}` for {target_channel.mention} at `{run_at_str}`."
        )

    async def _send_immediate(
        self, message, target_channel, content, embed, view, files, poll
    ):
        try:
            sent_msg = await target_channel.send(
                content=content, embed=embed, view=view, files=files
            )
            if poll:
                await sent_msg.add_reaction("✅")
                await sent_msg.add_reaction("❌")
            await message.channel.send(f"✅ Sent to {target_channel.mention}!")
        except Exception as e:
            await message.channel.send(f"❌ Error sending: {e}")
            logger.error(f"Error sending announcement: {e}")

    async def _check_schedule_loop(self):
        await self.wait_until_ready()
        while not self.is_closed():
            try:
                now_cairo = datetime.now(CAIRO_TZ)
                now_str = now_cairo.strftime("%Y-%m-%d %H:%M:%S")

                rows = []
                with DBHandler(DB_NAME) as db:
                    db.cursor.execute(
                        "SELECT id, content, channel_name, attachment_paths FROM scheduled WHERE run_at <= ?",
                        (now_str,),
                    )
                    rows = db.cursor.fetchall()

                for row in rows:
                    await self._execute_scheduled_task(row)
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")

            await asyncio.sleep(10)

    async def _execute_scheduled_task(self, row):
        row_id, raw_content, channel_name, att_paths_json = row

        target_channel = self._find_channel(channel_name)
        if not target_channel:
            logger.warning(
                f"Scheduled message {row_id}: Channel {channel_name} not found."
            )
            with DBHandler(DB_NAME) as db:
                db.cursor.execute("DELETE FROM scheduled WHERE id = ?", (row_id,))
            return

        config, outside, embed_desc = self._parse_content(raw_content)

        embed = discord.Embed(
            description=embed_desc if embed_desc else None,
            color=config["color"],
            timestamp=datetime.now(),
        )
        user = self.get_user(OWNER_ID)
        if user:
            embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
        embed.set_footer(text="D7M Announcement")

        view = LinkButtonView(config["buttons"]) if config["buttons"] else None

        # Resolve mentions again
        final_content = outside
        if config["mentions"]:
            guild = target_channel.guild
            role_mentions = []
            role_map = {r.name.lower(): r for r in guild.roles}
            for r_name in config["mentions"]:
                matches = difflib.get_close_matches(
                    r_name.lower(), role_map.keys(), n=1, cutoff=0.5
                )
                if matches:
                    role_mentions.append(role_map[matches[0]].mention)
            if role_mentions:
                final_content = (
                    (final_content + "\n" + " ".join(role_mentions))
                    if final_content
                    else " ".join(role_mentions)
                )

        files = []
        if att_paths_json:
            try:
                paths = json.loads(att_paths_json)
                for path in paths:
                    if os.path.exists(path):
                        files.append(discord.File(path))
            except Exception as e:
                logger.error(f"Failed to load attachments for {row_id}: {e}")

        try:
            sent_msg = await target_channel.send(
                content=final_content, embed=embed, view=view, files=files
            )
            if config["poll"]:
                await sent_msg.add_reaction("✅")
                await sent_msg.add_reaction("❌")

            with DBHandler(DB_NAME) as db:
                db.cursor.execute("DELETE FROM scheduled WHERE id = ?", (row_id,))

            if user:
                await user.send(
                    f"✅ Executed scheduled message {row_id} in {target_channel.mention}."
                )

            # Cleanup files
            if att_paths_json:
                paths = json.loads(att_paths_json)
                for path in paths:
                    try:
                        os.remove(path)
                    except Exception:
                        pass

        except Exception as e:
            logger.error(f"Failed to execute scheduled message {row_id}: {e}")

    async def _handle_reply_edit(self, message):
        """Legacy in-server edit support."""
        try:
            original_message = await message.channel.fetch_message(
                message.reference.message_id
            )
            if original_message.author.id == self.user.id:
                config, outside_content, embed_description = self._parse_content(
                    message.content
                )
                if original_message.embeds:
                    embed = original_message.embeds[0]
                    embed.description = embed_description if embed_description else None
                    embed.color = discord.Color(config["color"])
                    view = (
                        LinkButtonView(config["buttons"]) if config["buttons"] else None
                    )
                    await original_message.edit(
                        content=outside_content, embed=embed, view=view
                    )
                    await message.delete()
        except Exception:
            pass


if __name__ == "__main__":
    if TOKEN:
        client = EmbedBot()
        client.run(TOKEN)
