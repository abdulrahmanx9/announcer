import discord
from discord.ui import View, Button
import os
import logging
import asyncio
import re
import difflib
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("EmbedBot")

# Load environment variables
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
try:
    OWNER_ID = int(os.getenv("OWNER_ID", 0))
except ValueError:
    logger.error("OWNER_ID must be an integer.")
    OWNER_ID = 0


class LinkButtonView(View):
    def __init__(self, buttons_config):
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

    async def on_ready(self):
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        # Send usage guide to owner
        user = await self.fetch_user(OWNER_ID)
        if user:
            await self._send_usage_guide(user)

    async def _send_usage_guide(self, user):
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
                "`schedule: 10m` - Delayed posting (m/h/d)\n"
                "`button: Label | URL` - Add link buttons"
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

    def _parse_time(self, time_str):
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

    def _find_channel(self, channel_name):
        """Fuzzy search for a channel across all guilds."""
        all_channels = []
        for guild in self.guilds:
            for channel in guild.text_channels:
                all_channels.append(channel)

        # Create a map of name -> channel
        channel_map = {c.name.lower(): c for c in all_channels}

        # Fuzzy match
        matches = difflib.get_close_matches(
            channel_name.lower(), channel_map.keys(), n=1, cutoff=0.4
        )
        if matches:
            return channel_map[matches[0]]
        return None

    def _parse_content(self, content):
        """
        Parses content for keys and separates description.
        Returns:
            config (dict): Parsed configuration
            clean_content (str): The message content
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
            "schedule": 0,
            "buttons": [],  # List of (Label, URL) tuples
            "mentions": [],  # List of role names
        }

        color_map = {
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

        for line in content_lines:
            clean_line = line.strip()
            lower_line = clean_line.lower()

            # Key Parsing
            if lower_line.startswith("channel:"):
                # Handle keys regardless of capitalization
                try:
                    config["channel"] = clean_line.split(":", 1)[1].strip()
                except:
                    pass
                continue

            if lower_line.startswith("mention:"):
                try:
                    role_names = clean_line.split(":", 1)[1].strip().split(",")
                    for r in role_names:
                        if r.strip():
                            config["mentions"].append(r.strip())
                except:
                    pass
                continue

            if lower_line.startswith("everyone:"):
                try:
                    config["everyone"] = lower_line.split(":", 1)[1].strip() == "true"
                except:
                    pass
                continue

            if lower_line.startswith("preview:"):
                try:
                    config["preview"] = lower_line.split(":", 1)[1].strip() == "true"
                except:
                    pass
                continue

            if lower_line.startswith("poll:"):
                try:
                    config["poll"] = lower_line.split(":", 1)[1].strip() == "true"
                except:
                    pass
                continue

            if lower_line.startswith("schedule:"):
                try:
                    config["schedule"] = self._parse_time(
                        lower_line.split(":", 1)[1].strip()
                    )
                except:
                    pass
                continue

            if lower_line.startswith("color:"):
                try:
                    val = lower_line.split(":", 1)[1].strip()
                    if val in color_map:
                        config["color"] = color_map[val]
                    elif val.startswith("0x"):
                        config["color"] = int(val, 16)
                except:
                    pass
                continue

            if lower_line.startswith("button:"):
                # format: button: Label | URL
                try:
                    parts = clean_line.split(":", 1)[1].strip().split("|")
                    if len(parts) >= 2:
                        config["buttons"].append((parts[0].strip(), parts[1].strip()))
                except Exception:
                    pass
                continue

            # Legacy mentions
            if "@everyone" in line or "@here" in line:
                outside_lines.append(line)
            else:
                embed_lines.append(line)

        if config["everyone"]:
            outside_lines.append("||@everyone||")

        return config, "\n".join(outside_lines), "\n".join(embed_lines)

    async def on_message(self, message):
        if message.author.id == self.user.id or message.author.id != OWNER_ID:
            return

        # 1. Handle DM Messages (New Workflow support)
        if isinstance(message.channel, discord.DMChannel):
            await self._handle_dm_announcement(message)
            return

        # 2. Handle Reply-to-Edit in Server Channels (Legacy support logic could go here)
        # But for DM-based workflow, reply-to-edit works better in DM if finding cached message
        # We will keep server-channel checking just in case user is using it there.
        if message.reference:
            await self._handle_reply_edit(message)

    async def _handle_dm_announcement(self, message):
        config, outside_content, embed_description = self._parse_content(
            message.content
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

        # Prepare View (Buttons)
        view = None
        if config["buttons"]:
            view = LinkButtonView(config["buttons"])

        # Prepare Files
        files = []
        if message.attachments:
            for att in message.attachments:
                files.append(await att.to_file())

        # Target Channel Resolution (Run early for preview)
        target_channel = None
        target_channel_info = "Not specified"

        if config["channel"]:
            target_channel = self._find_channel(config["channel"])
            if target_channel:
                target_channel_info = target_channel.mention
            else:
                target_channel_info = f"❌ (Could not find `{config['channel']}`)"
        else:
            target_channel_info = "❌ (No channel specified)"

        # MODE: Preview
        if config["preview"]:
            preview_mentions = outside_content
            if config["mentions"]:
                preview_mentions += (
                    "\n(Mentions: " + ", ".join(config["mentions"]) + ")"
                )

            # Show target channel info in preview
            preview_header = f"👀 **Preview** for {target_channel_info}:"
            await message.channel.send(preview_header, embed=embed, view=view)

            if preview_mentions.strip():
                await message.channel.send(preview_mentions)
            if files:
                await message.channel.send(
                    "*(Attachments included in preview)*", files=files
                )
            return

        # Validation: Stop if no valid channel found (unless previewing, which just returns above)
        if not target_channel:
            if config["channel"]:
                await message.channel.send(
                    f"❌ Could not find any channel matching `{config['channel']}`."
                )
            else:
                await message.channel.send(
                    "❌ Please specify a channel using `channel: name`."
                )
            return

        # Role Mention Resolution
        final_outside_content = outside_content
        if config["mentions"]:
            guild = target_channel.guild
            role_mentions = []

            # Create a map of lower_role_name -> Role object
            role_map = {r.name.lower(): r for r in guild.roles}

            for role_name in config["mentions"]:
                # Exact match first (case-insensitive)
                found_role = role_map.get(role_name.lower())

                # If not found, fuzzy match?
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
                # Add to content
                if final_outside_content:
                    final_outside_content += "\n" + " ".join(role_mentions)
                else:
                    final_outside_content = " ".join(role_mentions)

        # MODE: Schedule
        if config["schedule"] > 0:
            wait_time = config["schedule"]
            finish_time = datetime.now() + timedelta(seconds=wait_time)
            await message.channel.send(
                f"⏳ Scheduled for {target_channel.mention} in {wait_time}s ({finish_time.strftime('%H:%M:%S')})"
            )

            # Wait loop
            await asyncio.sleep(wait_time)

        # SEND
        try:
            sent_msg = await target_channel.send(
                content=final_outside_content, embed=embed, view=view, files=files
            )

            if config["poll"]:
                await sent_msg.add_reaction("✅")
                await sent_msg.add_reaction("❌")

            await message.channel.send(f"✅ Sent to {target_channel.mention}!")
        except Exception as e:
            await message.channel.send(f"❌ Error sending: {e}")
            logger.error(f"Error sending announcement: {e}")

    async def _handle_reply_edit(self, message):
        """Legacy in-server edit support."""
        try:
            original_message = await message.channel.fetch_message(
                message.reference.message_id
            )
            if original_message.author.id == self.user.id:
                # We reuse parse_content but filter out channel/schedule keys which are irrelevant for edits
                config, outside_content, embed_description = self._parse_content(
                    message.content
                )

                if original_message.embeds:
                    embed = original_message.embeds[0]
                    embed.description = embed_description if embed_description else None
                    embed.color = discord.Color(config["color"])

                    view = None
                    if config["buttons"]:
                        view = LinkButtonView(config["buttons"])

                    await original_message.edit(
                        content=outside_content, embed=embed, view=view
                    )
                    await message.delete()
        except:
            pass


if __name__ == "__main__":
    if TOKEN:
        client = EmbedBot()
        client.run(TOKEN)
