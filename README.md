# Keystone Hub

**This is a copy of @Beel12213 Discord Bot, Tweaked for our community.

**Keystone Hub** is a robust Discord bot designed for World of Warcraft players who love running Mythic+ dungeons. This bot helps you quickly form balanced groups, manage roles, track statistics, and organise scheduled runs. Whether you're a tank, healer, or DPS, MythicMate ensures smooth group formation and provides valuable insights into your M+ journey.

## Features

### Group Formation
- Create groups with `/lfm` command
- Interactive role selection through reactions
- Automatic backup system for full roles
- Real-time group composition updates
- Automatic completion tracking

### Scheduling System
- Schedule runs for immediate start or future times
- Format: "YYYY-MM-DD HH:MM" or "now"
- Automatic DM reminders 15 minutes before start
- Fallback channel notifications if DMs are blocked

### Statistics & Leaderboards
- Personal statistics tracking with `/mystats`
- Server leaderboards with `/leaderboard`
- Multiple leaderboard categories:
  - Most Runs Completed
  - Highest Keys Completed
  - Role Distribution
- Timeframe filters: All Time, Monthly, Weekly

### Role Management
- Easy role selection through reactions
- Clear role option to change roles
- Automatic backup promotion when spots open
- Notification system for role changes

## Commands

### `/lfm`
Start looking for members for a Mythic+ run.
```
/lfm dungeon:<dungeon> key_level:<key level> role:<your role> schedule:<time>
```
- **dungeon**: Dungeon name or abbreviation (e.g., "mots" for Mists of Tirna Scithe)
- **key_level**: Difficulty level (e.g., "+15")
- **role**: Your role in the group (Tank/Healer/DPS)
- **schedule**: When to start ("now" or "YYYY-MM-DD HH:MM")

### `/mystats`
View your personal M+ statistics for the current server.
```
/mystats
```

### `/leaderboard`
View server leaderboards for different categories.
```
/leaderboard category:<category> timeframe:<timeframe>
```
- **category**: "runs" or "keys"
- **timeframe**: "all", "month", or "week"

## Getting Started (Self Hosting)

### Prerequisites
- Python 3.10+
- Discord.py library
- SQLite3
- Docker & Docker Compose (optional)

### Installation

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/Beel12213/MythicMate.git
   cd MythicMate
   ```

2. **Set Up Environment Variables:**
   ```bash
   cp .env.example .env
   nano .env
   ```
   Add your Discord bot token:
   ```
   BOT_TOKEN=your_discord_bot_token
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Bot:**
   ```bash
   python bot.py
   ```

### Docker Deployment (Optional)
1. **Build and Run:**
   ```bash
   docker-compose up -d
   ```

## Required Permissions
MythicMate requires these Discord permissions:
- Read Messages/View Channels
- Send Messages
- Embed Links
- Add Reactions
- Manage Messages
- Use External Emojis

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
