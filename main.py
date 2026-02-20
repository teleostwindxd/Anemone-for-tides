import discord
from discord.ext import commands
import os
import time
from datetime import timedelta
from collections import defaultdict
from keep_alive import keep_alive # Imports the fake web server

# --- Bot Setup ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents, activity=discord.Game(name="Watching the server | !help"))

# Tracking for anti-spam and warnings
user_messages = defaultdict(list)
user_warnings = defaultdict(int)

# Banned word list
BANNED_WORDS = ["badword1", "badword2", "spamlink.com"]

# Allowed Role IDs for sending GIFs
ALLOWED_GIF_ROLES = [
    1371466080404373507,
    1371466080387862661,
    1371468894853795871,
    1371466080404373506,
    1371466080366760064,
    1376303683599335434
]

# The GIF to send when someone gets caught
BROKE_GIF_LINK = "https://tenor.com/view/you%27re-broke-broke-brokie-andrew-tate-tate-gif-13383070538022521939"


@bot.event
async def on_ready():
    print(f'✅ Logged in as {bot.user.name} ({bot.user.id})')
    print('------')


# --- Smart Auto-Moderation ---
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content_lower = message.content.lower()

    # 1. Banned Word Filter
    if any(word in content_lower for word in BANNED_WORDS):
        await message.delete()
        warning_msg = await message.channel.send(f"⚠️ {message.author.mention}, please watch your language!")
        await warning_msg.delete(delay=5)
        return # Stop processing

    # 2. Advanced Anti-Spam (Auto-Mutes after 5 messages in 5 seconds)
    author_id = message.author.id
    current_time = time.time()
    user_messages[author_id].append(current_time)
    
    # Filter out messages older than 5 seconds
    user_messages[author_id] = [t for t in user_messages[author_id] if current_time - t < 5]
    
    if len(user_messages[author_id]) > 5:
        await message.delete()
        try:
            duration = timedelta(minutes=5)
            await message.author.timeout(duration, reason="Automated Spam Prevention")
            embed = discord.Embed(title="Anti-Spam Triggered", description=f"{message.author.mention} has been auto-muted for 5 minutes for spamming.", color=discord.Color.red())
            await message.channel.send(embed=embed)
        except discord.Forbidden:
            pass 
        return

    # 3. GIF Block Filter
    # First, verify the author is an actual Member in a Server (not DMing the bot)
    if isinstance(message.author, discord.Member):
        # Check if the user has any of the allowed roles
        has_allowed_role = any(role.id in ALLOWED_GIF_ROLES for role in message.author.roles)
        
        if not has_allowed_role:
            is_gif = False
            
            # Look for common GIF domains and extensions in the text
            if "tenor.com/view" in content_lower or "giphy.com/gifs" in content_lower or ".gif" in content_lower:
                is_gif = True
                
            # If no link was found, check if they uploaded a GIF file directly
            if not is_gif:
                for attachment in message.attachments:
                    if attachment.filename.lower().endswith(".gif") or (attachment.content_type and "gif" in attachment.content_type):
                        is_gif = True
                        break
            
            # If a GIF is detected, delete it and ping them
            if is_gif:
                try:
                    await message.delete()
                    await message.channel.send(f"{message.author.mention} {BROKE_GIF_LINK}")
                except discord.Forbidden:
                    pass # Fails safely if bot lacks permission
                return # Stop processing so commands aren't run

    # Process normal commands
    await bot.process_commands(message)


# --- Enhanced Moderation Commands (Using Embeds) ---

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason provided"):
    await member.kick(reason=reason)
    embed = discord.Embed(title="Member Kicked 👢", color=discord.Color.orange())
    embed.add_field(name="User", value=member.mention, inline=False)
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=False)
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason provided"):
    await member.ban(reason=reason)
    embed = discord.Embed(title="Member Banned 🔨", color=discord.Color.red())
    embed.add_field(name="User", value=member.mention, inline=False)
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=False)
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, minutes: int, *, reason="No reason provided"):
    duration = timedelta(minutes=minutes)
    await member.timeout(duration, reason=reason)
    embed = discord.Embed(title="Member Muted 🔇", color=discord.Color.gold())
    embed.add_field(name="User", value=member.mention, inline=False)
    embed.add_field(name="Duration", value=f"{minutes} minutes", inline=False)
    embed.add_field(name="Reason", value=reason, inline=False)
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f'🧹 Successfully deleted {len(deleted)-1} messages.')
    await msg.delete(delay=3)

@bot.command()
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    embed = discord.Embed(title="Channel Locked 🔒", description="Regular members can no longer send messages here.", color=discord.Color.red())
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    embed = discord.Embed(title="Channel Unlocked 🔓", description="Regular members can now send messages here.", color=discord.Color.green())
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(kick_members=True)
async def warn(ctx, member: discord.Member, *, reason="No reason provided"):
    user_warnings[member.id] += 1
    warnings_count = user_warnings[member.id]
    
    try:
        await member.send(f"⚠️ You have been warned in **{ctx.guild.name}**. Reason: {reason}. You now have {warnings_count} warning(s).")
    except discord.Forbidden:
        pass
        
    embed = discord.Embed(title="Warning Issued ⚠️", color=discord.Color.yellow())
    embed.add_field(name="User", value=member.mention, inline=False)
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.add_field(name="Total Warnings", value=warnings_count, inline=False)
    await ctx.send(embed=embed)

# --- Error Handling ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You do not have permission to use this command!")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ You are missing a required argument. Try checking the command usage.")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Could not find that member in the server.")

# --- Start Bot ---
if __name__ == "__main__":
    keep_alive() # Starts the fake Flask web server for Render
    TOKEN = os.getenv("DISCORD_TOKEN")
    if TOKEN is None:
        print("Error: DISCORD_TOKEN environment variable not set.")
    else:
        bot.run(TOKEN)
