import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import asyncio
import pytz
import sqlite3
from sqlite3 import Error

# Load environment variables from .env file
load_dotenv()

# Get the bot token from environment variables
TOKEN = os.getenv('BOT_TOKEN')

# At the start, after load_dotenv()
print(f"Token loaded from environment: {'Yes' if TOKEN else 'No'}")
print(f"Token length: {len(TOKEN) if TOKEN else 0}")

# Configure the bot with the necessary intents (permissions)
intents = discord.Intents.default()
intents.reactions = True
intents.guilds = True
intents.guild_messages = True
intents.message_content = False

print("Intents configured:")
print(f"- Reactions: {intents.reactions}")
print(f"- Guilds: {intents.guilds}")
print(f"- Guild Messages: {intents.guild_messages}")
print(f"- Message Content: {intents.message_content}")

# Initialize the bot with a command prefix and intents
bot = commands.Bot(command_prefix='!', intents=intents)

# Define the roles for Tank, Healer, and DPS using emoji symbols
role_emojis = {
    "Tank": "🛡️",
    "Healer": "💚",
    "DPS": "⚔️",
    "Clear Role":
    "❌"  # This emoji is used to allow users to clear their selected role
}


# Event handler for when the bot is ready and connected to Discord
@bot.event
async def on_ready():
  print(f'Bot is ready! Logged in as {bot.user}')
  try:
    synced = await bot.tree.sync()  # Synchronize the command tree with Discord
    print(f"Synced {len(synced)} commands.")
  except Exception as e:
    print(f"Error syncing commands: {e}")


# Global dictionary to store active groups
active_groups = {}


async def update_group_embed(message, embed, group_state):
  """
    Updates the embed message with current group composition and backup information.

    Args:
        message: The Discord message to update
        embed: The embed object to modify
        group_state: Current state of the group including members and backups
    """
  if not message or not embed or not group_state:
    print("Missing required parameters for update_group_embed")
    return

  try:
    embed.clear_fields()

    # Display main role assignments
    embed.add_field(name="", value="------------",
                    inline=False)  # zero-width space
    embed.add_field(name="🛡️ Tank",
                    value=group_state.members["Tank"].mention
                    if group_state.members["Tank"] else "None",
                    inline=False)
    embed.add_field(name="", value="------------",
                    inline=False)  # zero-width space
    embed.add_field(name="💚 Healer",
                    value=group_state.members["Healer"].mention
                    if group_state.members["Healer"] else "None",
                    inline=False)
    embed.add_field(name="", value="------------",
                    inline=False)  # zero-width space
    # Display DPS slots (filled or empty)
    dps_value = "\n".join(
        [dps_user.mention for dps_user in group_state.members["DPS"]] +
        ["None"] * (3 - len(group_state.members["DPS"])))
    embed.add_field(name="⚔️ DPS", value=dps_value, inline=False)

    # Display backup players for each role
    backup_text = ""
    for role, backups in group_state.backups.items():
      if backups:
        backup_text += f"\n**{role}**: " + ", ".join(backup.mention
                                                     for backup in backups)

    if backup_text:
      embed.add_field(name="📋 Backups",
                      value=backup_text.strip(),
                      inline=False)

    # Changed to use fetch_message and edit
    try:
      # Fetch a fresh message object before editing
      current_message = await message.channel.fetch_message(message.id)
      await current_message.edit(embed=embed)
    except discord.NotFound:
      print("Message not found - it may have been deleted")
    except discord.Forbidden:
      print("Bot doesn't have permission to edit the message")
    except Exception as e:
      print(f"Error updating message: {e}")

  except Exception as e:
    print(f"Error in update_group_embed: {e}")


@bot.tree.command(name="lfm",
                  description="Start looking for members for a Mythic+ run.")
@app_commands.describe(
    dungeon="Enter the dungeon name (max 30 characters)",
    key_level="Enter the key level (e.g., +10)",
    role="Select your role in the group, Tank, Healer or DPS",
    time="When to run (e.g., The time you want to run)")
async def lfm(interaction: discord.Interaction, dungeon: str, key_level: str,
              role: str, time: str):
  print(f"LFM command received from {interaction.user}")
  print("Starting LFM command...")

  # Validate dungeon name (allow any non-empty string up to 30 chars)
  if not dungeon or len(dungeon) > 30:
    await interaction.response.send_message(
        f"Dungeon name must be 1-30 characters.", ephemeral=True)
    return
  full_dungeon_name = dungeon.strip()

  # Validate time (allow any non-empty string up to 30 chars)
  if not time or len(time) > 30:
    await interaction.response.send_message(f"Time must be 1-30 characters.",
                                            ephemeral=True)
    return
  time_str = time.strip()
  time_time = None  # No longer used, but kept for compatibility with later code

  # Remove defer and send the embed directly
  group_state = GroupState(interaction, role, time_time)
  embed = discord.Embed(
      title=f"Dungeon: {full_dungeon_name}\nDifficulty: {key_level}\nTime: {time_str}",
      color=discord.Color.blue()
  )
  embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url)
  embed.set_thumbnail(url="https://example.com/path/to/your/image.png")

  # Send the embed as the initial response
  await interaction.response.send_message(embed=embed)
  group_message = await interaction.channel.fetch_message((await interaction.original_response()).id)
  active_groups[group_message.id] = {
      "state": group_state,
      "embed": embed,
      "message": group_message,
      "dungeon": full_dungeon_name,
      "key_level": key_level
  }

  # Update embed with initial group composition
  await update_group_embed(group_message, embed, group_state)

  # Add role selection reactions
  for emoji in role_emojis.values():
      await group_message.add_reaction(emoji)

  # No reminder task since time_time is not parsed

  print(f"Created group message with ID: {group_message.id}")
  print(f"Active groups after creation: {list(active_groups.keys())}")


@bot.event
async def on_reaction_add(reaction, user):
  print(
      f"Reaction detected - Emoji: {reaction.emoji}, User: {user}, Message ID: {reaction.message.id}"
  )
  if user == bot.user:
    print("Reaction was from bot, ignoring")
    return

  group_info = active_groups.get(reaction.message.id)
  if not group_info:
    print(f"No group found for message ID {reaction.message.id}")
    print(f"Active groups: {list(active_groups.keys())}")
    return

  print(f"Found group info for message {reaction.message.id}")
  group_state = group_info["state"]
  group_message = group_info["message"]
  embed = group_info["embed"]

  # Handle role clearing
  if str(reaction.emoji) == role_emojis["Clear Role"]:
    role, promoted_user = group_state.remove_user(user)
    if promoted_user:
      await group_message.channel.send(
          f"{promoted_user.mention} has been promoted from backup to {role}!",
          delete_after=10)
    # Remove all role reactions from the user
    for role_name, emoji in role_emojis.items():
      if emoji != role_emojis["Clear Role"]:
        await group_message.remove_reaction(emoji, user)
    await update_group_embed(group_message, embed, group_state)
    await group_message.remove_reaction(reaction.emoji, user)
    return

  # Prevent users from selecting multiple roles
  current_role = group_state.get_user_role(user)
  if current_role:
    await group_message.remove_reaction(reaction.emoji, user)
    await user.send(
        "You can only select one role. Please remove your current role first.")
    return

  # Handle role selection
  role_added = False
  if str(reaction.emoji) == role_emojis["Tank"]:
    role_added = group_state.add_member("Tank", user)
  elif str(reaction.emoji) == role_emojis["Healer"]:
    role_added = group_state.add_member("Healer", user)
  elif str(reaction.emoji) == role_emojis["DPS"]:
    role_added = group_state.add_member("DPS", user)

  # Notify user if added to backup
  if not role_added:
    await user.send("You've been added to the backup list for this role.")

  await update_group_embed(group_message, embed, group_state)

  # Add completion marker if group is full
  if group_state.is_complete():
    await group_message.add_reaction("✅")


@bot.event
async def on_reaction_remove(reaction, user):
  """
    Handles when users remove their role reactions.

    Args:
        reaction: The reaction emoji removed
        user: The user who removed the reaction
    """
  if user == bot.user:
    return

  group_info = active_groups.get(reaction.message.id)
  if not group_info:
    return

  group_state = group_info["state"]
  group_message = group_info["message"]
  embed = group_info["embed"]

  # Remove user from their role
  if str(reaction.emoji
         ) == role_emojis["Tank"] and group_state.members["Tank"] == user:
    group_state.members["Tank"] = None
  elif str(
      reaction.emoji
  ) == role_emojis["Healer"] and group_state.members["Healer"] == user:
    group_state.members["Healer"] = None
  elif str(reaction.emoji
           ) == role_emojis["DPS"] and user in group_state.members["DPS"]:
    group_state.members["DPS"].remove(user)

  await update_group_embed(group_message, embed, group_state)


@bot.event
async def on_message(message):
  print(f"Message received: {message.content[:20]}...")
  await bot.process_commands(message)


class GroupState:
  """
    Manages the state of a Mythic+ group including members, backups, and reminders.

    Attributes:
        members: Dictionary containing current group members by role
        backups: Dictionary containing backup players by role
        reminder_task: Optional asyncio task for timed groups
    """

  def __init__(self, interaction, initial_role, time_time=None):
    """
        Initializes a new group state.

        Args:
            interaction: Discord interaction that created the group
            initial_role: Starting role of the group creator
            time_time: Optional datetime for timed groups
        """
    self.members = {"Tank": None, "Healer": None, "DPS": []}
    self.backups = {"Tank": [], "Healer": [], "DPS": []}
    self.reminder_task = None
    self.time_time = time_time

    # Add the command user to their selected role
    user = interaction.user
    self.add_member(initial_role, user)

  def add_member(self, role, user):
    """
        Adds a user to a role, or to backup if role is full.

        Args:
            role: The role to add the user to
            user: The Discord user to add

        Returns:
            bool: True if added to main role, False if added to backup
        """
    if role == "Tank":
      if not self.members["Tank"]:
        self.members["Tank"] = user
        return True
      else:
        self.backups["Tank"].append(user)
        return False
    elif role == "Healer":
      if not self.members["Healer"]:
        self.members["Healer"] = user
        return True
      else:
        self.backups["Healer"].append(user)
        return False
    elif role == "DPS":
      if len(self.members["DPS"]) < 3:
        self.members["DPS"].append(user)
        return True
      else:
        self.backups["DPS"].append(user)
        return False
    return False

  def remove_user(self, user):
    """
        Removes a user from their role and promotes a backup if available.

        Args:
            user: The Discord user to remove

        Returns:
            tuple: (role_removed_from, promoted_user) or (None, None) if user not found
        """
    # Check main roles first
    if self.members["Tank"] == user:
      self.members["Tank"] = None
      if self.backups["Tank"]:
        promoted_user = self.backups["Tank"].pop(0)
        self.members["Tank"] = promoted_user
        return "Tank", promoted_user
      return "Tank", None

    if self.members["Healer"] == user:
      self.members["Healer"] = None
      if self.backups["Healer"]:
        promoted_user = self.backups["Healer"].pop(0)
        self.members["Healer"] = promoted_user
        return "Healer", promoted_user
      return "Healer", None

    if user in self.members["DPS"]:
      self.members["DPS"].remove(user)
      if self.backups["DPS"]:
        promoted_user = self.backups["DPS"].pop(0)
        self.members["DPS"].append(promoted_user)
        return "DPS", promoted_user
      return "DPS", None

    # Check backups
    for role in ["Tank", "Healer", "DPS"]:
      if user in self.backups[role]:
        self.backups[role].remove(user)
        return role, None

    return None, None

  def get_user_role(self, user):
    """
        Gets the current role of a user in the group.

        Args:
            user: The Discord user to check

        Returns:
            str: The user's role or None if not in group
        """
    if self.members["Tank"] == user:
      return "Tank"
    if self.members["Healer"] == user:
      return "Healer"
    if user in self.members["DPS"]:
      return "DPS"

    # Check backups
    for role, backups in self.backups.items():
      if user in backups:
        return f"Backup {role}"
    return None

  def is_complete(self):
    """
        Checks if the group has all required roles filled.

        Returns:
            bool: True if group is complete, False otherwise
        """
    return (self.members["Tank"] is not None
            and self.members["Healer"] is not None
            and len(self.members["DPS"]) == 3)

  async def send_reminder(self, channel):
    """
        Sends reminders to group members before timed start time.

        Args:
            channel: The Discord channel to send fallback messages to
        """
    if not self.reminder_task:
      return

    try:
      # Wait until 15 minutes before timed time
      await asyncio.sleep(
          max(0,
              (self.time_time - datetime.now(pytz.UTC)).total_seconds() - 900))

      # Send DMs to all members
      all_members = [
          self.members["Tank"], self.members["Healer"], *self.members["DPS"]
      ]

      for member in all_members:
        if member:
          try:
            await member.send(f"Reminder: Your M+ run starts in 15 minutes!")
          except discord.Forbidden:
            await channel.send(
                f"{member.mention} (Could not send DM: Your M+ run starts in 15 minutes!)",
                delete_after=60)
    except asyncio.CancelledError:
      pass
    except Exception as e:
      print(f"Error in reminder task: {e}")


def create_connection():
  try:
    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)
    conn = sqlite3.connect('data/mythicmate.db')
    return conn
  except Error as e:
    print(f"Error connecting to database: {e}")
    return None


async def record_completed_run(group_state, dungeon_name, key_level, guild_id,
                               guild_name):
  conn = create_connection()
  if conn is None:
    return

  try:
    c = conn.cursor()

    # Ensure server is registered
    c.execute(
        '''
            INSERT OR IGNORE INTO servers (server_id, server_name)
            VALUES (?, ?)
        ''', (str(guild_id), guild_name))

    # Insert run record
    c.execute(
        '''
            INSERT INTO runs (server_id, dungeon_name, key_level, completion_time)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (str(guild_id), dungeon_name, int(key_level.strip('+'))))
    run_id = c.lastrowid

    # Record participants
    if group_state.members["Tank"]:
      c.execute(
          '''
                INSERT INTO participants (run_id, server_id, user_id, role)
                VALUES (?, ?, ?, ?)
            ''',
          (run_id, str(guild_id), str(group_state.members["Tank"].id), "Tank"))

    if group_state.members["Healer"]:
      c.execute(
          '''
                INSERT INTO participants (run_id, server_id, user_id, role)
                VALUES (?, ?, ?, ?)
            ''', (run_id, str(guild_id), str(
              group_state.members["Healer"].id), "Healer"))

    for dps in group_state.members["DPS"]:
      if dps:
        c.execute(
            '''
                    INSERT INTO participants (run_id, server_id, user_id, role)
                    VALUES (?, ?, ?, ?)
                ''', (run_id, str(guild_id), str(dps.id), "DPS"))

    conn.commit()
  except Error as e:
    print(f"Error recording run: {e}")
  finally:
    conn.close()


# Run the bot with the token loaded from the environment variables
bot.run(TOKEN)
