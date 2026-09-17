import os
import discord
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Dictionary to store contacts by NAME: 
# { "name_key": { "prefix": "...", "name": "...", "avatar": "...", "nick": "...", "embed_color": "...", "auto_target_id": None } }
contacts = {}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content
    matched_data = None
    
    # 1. Check if the message matches any registered prefix manually
    sorted_items = sorted(contacts.values(), key=lambda x: len(x["prefix"]), reverse=True)
    
    for data in sorted_items:
        if content.startswith(data["prefix"]):
            matched_data = data
            actual_text = content[len(data["prefix"]):].strip()
            break

    # 2. If no prefix matched, check if the character is auto-proxied to this channel/thread/category
    if not matched_data:
        for data in contacts.values():
            target_id = data.get("auto_target_id")
            if target_id:
                channel = message.channel
                is_match = (
                    channel.id == target_id or 
                    (hasattr(channel, "parent") and channel.parent and channel.parent.id == target_id) or
                    (hasattr(channel, "category") and channel.category and channel.category.id == target_id)
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

        channel = message.channel
        webhooks = await channel.webhooks()
        webhook = discord.utils.get(webhooks, name="VoltProxy")
        
        if not webhook:
            webhook = await channel.create_webhook(name="VoltProxy")

        display_name = matched_data["nick"] if matched_data["nick"] else matched_data["name"]
        avatar_url = matched_data["avatar"] if matched_data["avatar"] else message.author.display_avatar.url

        # Dischook-style Embed Look (Side bar color support)
        color = matched_data.get("embed_color") or discord.Color.default()
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
        "`!avatar <Name> <url>` - Set character avatar URL\n"
        "`!nick <Name> <nickname>` - Set character display nickname\n"
        "`!hex <Name> #HEXCODE` - Set embed side-bar color (Dischook style)\n"
        "`!auto <Name> <#channel / thread_link / category>` - Auto-proxy a character\n"
        "`!unauto <Name>` - Remove auto-proxying for a character\n"
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
        "embed_color": None,
        "auto_target_id": None
    }
    
    embed = discord.Embed(title="Contact info", color=discord.Color.blurple())
    embed.add_field(name="Name", value=name, inline=False)
    embed.add_field(name="Prefix", value=f"`{prefix}text`", inline=False)
    embed.add_field(name="Action", value=f"Say hi by typing: `{prefix}Hi`", inline=False)
    
    if avatar_url:
        embed.set_thumbnail(url=avatar_url)
        
    await ctx.reply("Character Registered Successfully!", embed=embed)

@bot.command()
async def remove(ctx, *, name: str):
    name_key = name.lower()
    if name_key in contacts:
        removed_name = contacts[name_key]["name"]
        del contacts[name_key]
        await ctx.reply(f"Contact **{removed_name}** has been removed.")
    else:
        await ctx.reply(f"No contact found with the name **{name}**.")

@bot.command(name="list")
async def list_contacts(ctx):
    if not contacts:
        await ctx.reply("You don't have any contacts registered yet.")
        return
    
    msg = "**Your Full Contact List:**\n"
    for data in contacts.values():
        auto_status = f" (Auto-proxied)" if data.get("auto_target_id") else ""
        msg += f"- **{data['name']}** | Prefix: `{data['prefix']}text`{auto_status}\n"
    await ctx.reply(msg)

@bot.command()
async def avatar(ctx, name: str, url: str):
    name_key = name.lower()
    if name_key in contacts:
        contacts[name_key]["avatar"] = url
        await ctx.reply(f"Avatar for **{contacts[name_key]['name']}** updated successfully!")
    else:
        await ctx.reply(f"No contact found with the name **{name}**.")

@bot.command()
async def nick(ctx, name: str, *, nickname: str):
    name_key = name.lower()
    if name_key in contacts:
        contacts[name_key]["nick"] = nickname
        await ctx.reply(f"Nickname for **{contacts[name_key]['name']}** set to **{nickname}**.")
    else:
        await ctx.reply(f"No contact found with the name **{name}**.")

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
        await ctx.reply(f"Embed side-bar color for **{contacts[name_key]['name']}** updated to `{hex_code}`!")
    except ValueError:
        await ctx.reply("Invalid HEX code! Please use a valid format like `#5E707A`.")

@bot.command()
async def auto(ctx, name: str, target: str = None):
    name_key = name.lower()
    if name_key not in contacts:
        await ctx.reply(f"No contact found with the name **{name}**.")
        return
    
    target_id = None
    if ctx.message.channel_mentions:
        target_id = ctx.message.channel_mentions[0].id
    elif target:
        if "discord.com/channels/" in target:
            try:
                parts = target.split("/")
                target_id = int(parts[-1])
            except ValueError:
                pass
        elif target.isdigit():
            target_id = int(target)
            
    if not target_id:
        target_id = ctx.channel.id

    contacts[name_key]["auto_target_id"] = target_id
    await ctx.reply(f"Character **{contacts[name_key]['name']}** is now auto-proxied to this target location!")

@bot.command()
async def unauto(ctx, *, name: str):
    name_key = name.lower()
    if name_key not in contacts:
        await ctx.reply(f"No contact found with the name **{name}**.")
        return
    
    contacts[name_key]["auto_target_id"] = None
    await ctx.reply(f"Auto-proxy has been removed for **{contacts[name_key]['name']}**.")

bot.run(TOKEN)
