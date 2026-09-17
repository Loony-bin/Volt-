import os
import json
import discord
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")
DATA_FILE = "contacts.json"

intents = discord.Intents.default()
intents.message_content = intents.guilds = intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- MEMORY FUNCTIONS ---
def load_contacts():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                cleaned_data = {}
                for name_key, info in data.items():
                    cleaned_targets = {}
                    for k, v in info.get("auto_targets", {}).items():
                        cleaned_targets[int(k)] = v
                    cleaned_nicks = {}
                    for k, v in info.get("channel_nicknames", {}).items():
                        cleaned_nicks[int(k)] = v
                    
                    info["auto_targets"] = cleaned_targets
                    info["channel_nicknames"] = cleaned_nicks
                    cleaned_data[name_key] = info
                return cleaned_data
        except Exception as e:
            print(f"Error loading contacts data: {e}")
    return {}

def save_contacts():
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(contacts, f, indent=4)
    except Exception as e:
        print(f"Error saving contacts data: {e}")

contacts = load_contacts()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content
    matched_data = None
    channel = message.channel
    channel_id = channel.id

    # 1. Check manual prefix triggers first
    sorted_items = sorted(contacts.values(), key=lambda x: len(x["prefix"]), reverse=True)
    for data in sorted_items:
        if content.startswith(data["prefix"]):
            matched_data = data
            actual_text = content[len(data["prefix"]):].strip()
            break

    # 2. Check auto-proxy triggers across multiple saved locations (checking both int and str types for safety)
    if not matched_data:
        for data in contacts.values():
            auto_targets = data.get("auto_targets", {})
            parent_id = channel.parent.id if (hasattr(channel, "parent") and channel.parent) else None
            cat_id = channel.category.id if (hasattr(channel, "category") and channel.category) else None
            
            is_match = (
                channel_id in auto_targets or str(channel_id) in auto_targets or
                (parent_id and (parent_id in auto_targets or str(parent_id) in auto_targets)) or
                (cat_id and (cat_id in auto_targets or str(cat_id) in auto_targets))
            )
            if is_match:
                matched_data = data
                actual_text = content.strip()
                break

    if matched_data:
        try:
            await message.delete()
        except discord.HTTPException:
            pass

        webhooks = await channel.webhooks()
        webhook = discord.utils.get(webhooks, name="VoltProxy")
        
        if not webhook:
            webhook = await channel.create_webhook(name="VoltProxy")

        channel_nicknames = matched_data.get("channel_nicknames", {})
        # Check both integer and string versions of the channel ID for the nickname
        display_name = (
            channel_nicknames.get(channel_id) or 
            channel_nicknames.get(str(channel_id)) or 
            matched_data.get("nick") or 
            matched_data["name"]
        )
        
        avatar_url = matched_data["avatar"] if matched_data["avatar"] else message.author.display_avatar.url
        color = matched_data.get("embed_color") or discord.Color.default()
        
        # Supports custom emojis, headings (#), subtext (-#), and blockquotes (>)
        embed = discord.Embed(description=actual_text, color=color)

        await webhook.send(
            embed=embed,
            username=display_name,
            avatar_url=avatar_url
        )
        return

    await bot.process_commands(message)

@bot.command(name="customhelp")
async def customhelp(ctx):
    help_text = (
        "**Volt | Help Menu**\n\n"
        "`!register <Name> <prefix>text` - Register a new character (Attach image for avatar!)\n"
        "`!remove <Name>` - Remove a character by name\n"
        "`!list` - View your contact list\n"
        "`!avatar <Name> [url]` - Set character avatar URL (or attach an image!)\n"
        "`!nick <Name> <nickname>` - Set character global nickname\n"
        "`!autonick <Name> <nickname> | <#channel>` - Set a clean channel-specific nickname\n"
        "`!hex <Name> #HEXCODE` - Set embed side-bar color (Dischook style)\n"
        "`!auto <Name> [<#channel>]` - Add an auto-proxy location (keeps all existing ones!)\n"
        "`!unauto <Name>` - Remove auto-proxying for this channel\n\n"
        "**Volt Bot Customization:**\n"
        "`!voltavatar [url]` - Change Volt's profile picture (or attach an image!)\n"
        "`!voltname <Name>` - Change Volt's global display name\n"
    )
    await ctx.reply(help_text)

@bot.command()
async def register(ctx, name: str, proxy_format: str):
    if not proxy_format.endswith("text"):
        await ctx.reply("Invalid format! End with `text`, like: `!register CharacterName prefixtext`")
        return
    
    prefix = proxy_format[:-4]
    name_key = name.lower()

    if name_key in contacts:
        await ctx.reply(f"A contact named **{name}** already exists!")
        return
    
    avatar_url = None
    if ctx.message.attachments:
        avatar_url = ctx.message.attachments[0].url

    contacts[name_key] = {
        "name": name,
        "prefix": prefix,
        "avatar": avatar_url,
        "nick": None,
        "channel_nicknames": {},
        "embed_color": None,
        "auto_targets": {}
    }
    save_contacts()
    
    embed = discord.Embed(title="Contact info", color=discord.Color.blurple())
    embed.add_field(name="Name", value=name, inline=False)
    embed.add_field(name="Prefix", value=f"`{prefix}text`", inline=False)
    embed.add_field(name="Action", value=f"Say hi by typing: `{prefix}Hi`", inline=False)
    
    if avatar_url:
        embed.set_thumbnail(url=avatar_url)
        
    await ctx.reply("Character Registered Successfully and Saved!", embed=embed)

@bot.command()
async def remove(ctx, *, name: str):
    name_key = name.lower()
    if name_key in contacts:
        removed_name = contacts[name_key]["name"]
        del contacts[name_key]
        save_contacts()
        await ctx.reply(f"Contact **{removed_name}** has been removed and saved.")
    else:
        await ctx.reply(f"No contact found with the name **{name}**.")

@bot.command(name="list")
async def list_contacts(ctx):
    if not contacts:
        await ctx.reply("You don't have any contacts registered yet.")
        return
    
    msg = "**Your Full Contact List:**\n"
    for data in contacts.values():
        auto_count = len(data.get("auto_targets", {}))
        auto_status = f" (Auto-proxied in {auto_count} locations)" if auto_count > 0 else ""
        msg += f"- **{data['name']}** | Prefix: `{data['prefix']}text`{auto_status}\n"
    await ctx.reply(msg)

@bot.command()
async def avatar(ctx, name: str, url: str = None):
    name_key = name.lower()
    if name_key not in contacts:
        await ctx.reply(f"No contact found with the name **{name}**.")
        return
    
    avatar_url = None
    if ctx.message.attachments:
        avatar_url = ctx.message.attachments[0].url
    elif url:
        avatar_url = url

    if not avatar_url:
        await ctx.reply("Please provide an image URL or attach an image with your command!")
        return

    contacts[name_key]["avatar"] = avatar_url
    save_contacts()
    await ctx.reply(f"Avatar for **{contacts[name_key]['name']}** updated and saved successfully!")

@bot.command()
async def nick(ctx, name: str, *, nickname: str):
    name_key = name.lower()
    if name_key not in contacts:
        await ctx.reply(f"No contact found with the name **{name}**.")
        return
    
    contacts[name_key]["nick"] = nickname
    save_contacts()
    await ctx.reply(f"Global nickname for **{contacts[name_key]['name']}** set to **{nickname}**.")

@bot.command(name="autonick")
async def autonick(ctx, name: str, *, args: str):
    name_key = name.lower()
    if name_key not in contacts:
        await ctx.reply(f"No contact found with the name **{name}**.")
        return
    
    # Parse out channel mention/link from the end of the argument string
    target_id = None
    nickname = args.strip()
    
    if ctx.message.channel_mentions:
        target_id = ctx.message.channel_mentions[0].id
        # Remove the channel mention text from the nickname string
        for mention in ctx.message.channel_mentions:
            nickname = nickname.replace(f"<#{mention.id}>", "").strip()
    else:
        # Check if text contains a channel link or ID at the end
        parts = args.rsplit(" ", 1)
        if len(parts) == 2:
            potential_target = parts[1].strip()
            if "discord.com/channels/" in potential_target:
                try:
                    target_id = int(potential_target.split("/")[-1])
                    nickname = parts[0].strip()
                except ValueError:
                    pass
            elif potential_target.isdigit():
                target_id = int(potential_target)
                nickname = parts[0].strip()
                
    if not target_id:
        target_id = ctx.channel.id

    contacts[name_key]["channel_nicknames"][target_id] = nickname
    save_contacts()
    await ctx.reply(f"Channel nickname for **{contacts[name_key]['name']}** set to **{nickname}** cleanly for that channel!")

@bot.command()
async def hex(ctx, name: str, hex_code: str):
    name_key = name.lower()
    if name_key not in contacts:
        await ctx.reply(f"No contact found with the name **{name}**.")
        return
    
    try:
        clean_hex = hex_code.lstrip("#")
        color_int = int(clean_hex, 16)
        contacts[name_key]["embed_color"] = discord.Color(color_int)
        save_contacts()
        await ctx.reply(f"Embed side-bar color for **{contacts[name_key]['name']}** updated to `{hex_code}`!")
    except ValueError:
        await ctx.reply("Invalid HEX code! Please use a valid format like `#5E707A`.")

@bot.command()
async def auto(ctx, name: str, *, target: str = None):
    name_key = name.lower()
    if name_key not in contacts:
        await ctx.reply(f"No contact found with the name **{name}**.")
        return
    
    target_id = None
    if ctx.message.channel_mentions:
        target_id = ctx.message.channel_mentions[0].id
    elif target:
        cleaned_target = target.strip()
        if cleaned_target.startswith("<#") and cleaned_target.endswith(">"):
            try:
                target_id = int(cleaned_target[2:-1])
            except ValueError:
                pass
        elif "discord.com/channels/" in cleaned_target:
            try:
                parts = cleaned_target.split("/")
                target_id = int(parts[-1])
            except ValueError:
                pass
        elif cleaned_target.isdigit():
            target_id = int(cleaned_target)
            
    if not target_id:
        target_id = ctx.channel.id

    contacts[name_key]["auto_targets"][target_id] = True
    save_contacts()
    await ctx.reply(f"Character **{contacts[name_key]['name']}** has been added to this auto-proxy location (all other locations remain active)!")

@bot.command()
async def unauto(ctx, *, name: str):
    name_key = name.lower()
    if name_key not in contacts:
        await ctx.reply(f"No contact found with the name **{name}**.")
        return
    
    channel_id = ctx.channel.id
    auto_targets = contacts[name_key].get("auto_targets", {})
    
    if channel_id in auto_targets:
        del auto_targets[channel_id]
        if channel_id in contacts[name_key].get("channel_nicknames", {}):
            del contacts[name_key]["channel_nicknames"][channel_id]
        save_contacts()
        await ctx.reply(f"Auto-proxy removed for **{contacts[name_key]['name']}** in this specific channel.")
    else:
        await ctx.reply(f"Character **{contacts[name_key]['name']}** is not auto-proxied in this channel.")

# --- VOLT BOT PROFILE CUSTOMIZATION ---
@bot.command(name="voltavatar")
async def voltavatar(ctx, url: str = None):
    avatar_bytes = None
    if ctx.message.attachments:
        avatar_bytes = await ctx.message.attachments[0].read()
    elif url:
        async with ctx.typing():
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        avatar_bytes = await resp.read()

    if not avatar_bytes:
        await ctx.reply("Please provide an image URL or attach an image to update Volt's avatar!")
        return

    try:
        await bot.user.edit(avatar=avatar_bytes)
        await ctx.reply("Volt's profile picture has been successfully updated!")
    except discord.HTTPException as e:
        await ctx.reply(f"Failed to change avatar (Discord allows changing a bot's avatar only a few times per hour): {e}")

@bot.command(name="voltname")
async def voltname(ctx, *, new_name: str):
    try:
        await bot.user.edit(username=new_name)
        await ctx.reply(f"Volt's global bot name has been changed to **{new_name}**!")
    except discord.HTTPException as e:
        await ctx.reply(f"Failed to change name (Discord limits bot username changes to twice per hour): {e}")

bot.run(TOKEN)
