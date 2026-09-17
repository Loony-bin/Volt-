import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Dictionary to store contacts: 
# { "prefix": { "name": "...", "avatar": "...", "nick": "...", "color": discord.Color } }
contacts = {}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content
    matched_prefix = None
    
    # Sort prefixes by length descending so longer prefixes match first if overlapping
    sorted_prefixes = sorted(contacts.keys(), key=len, reverse=True)
    
    for prefix in sorted_prefixes:
        if content.startswith(prefix):
            matched_prefix = prefix
            break

    if matched_prefix:
        data = contacts[matched_prefix]
        actual_text = content[len(matched_prefix):].strip()

        # Delete the user's original message
        try:
            await message.delete()
        except discord.HTTPException:
            pass

        # Find or create a webhook in the channel
        channel = message.channel
        webhooks = await channel.webhooks()
        webhook = discord.utils.get(webhooks, name="VoltProxy")
        
        if not webhook:
            webhook = await channel.create_webhook(name="VoltProxy")

        # Create an embed acting as the chat bubble
        embed = discord.Embed(
            description=actual_text, 
            color=data.get("color", discord.Color.blurple())
        )
        
        display_name = data["nick"] if data["nick"] else data["name"]
        avatar_url = data["avatar"] if data["avatar"] else message.author.display_avatar.url

        # Send via webhook
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
        "`!register <name> <prefix>text` - Register a new character (Attach an image for the avatar!)\n"
        "`!remove <prefix>` - Remove a character\n"
        "`!list` - View your contact list\n"
        "`!avatar <prefix> <url>` - Set character avatar URL\n"
        "`!nick <prefix> <nickname>` - Set character display nickname\n"
        "`!hex <prefix> <#HEXCODE>` - Change the embed side color (e.g. !hex c! #ffb6c1)"
    )
    await ctx.send(help_text)

@bot.command()
async def register(ctx, name: str, proxy_format: str):
    # Expecting format like c!text
    if not proxy_format.endswith("text"):
        await ctx.reply("Invalid format! Please end your registration with `text`, for example: `!register Cairo c!text`")
        return
    
    # Extract the prefix part (e.g., "c!" from "c!text")
    prefix = proxy_format[:-4]

    if prefix in contacts:
        await ctx.reply(f"A contact with prefix `{prefix}` already exists!")
        return
    
    # Check if the user attached an image to the registration message for the avatar
    avatar_url = None
    if ctx.message.attachments:
        avatar_url = ctx.message.attachments[0].url

    contacts[prefix] = {
        "name": name,
        "avatar": avatar_url,
        "nick": None,
        "color": discord.Color.blurple()
    }
    
    # Build the registration confirmation embed matching your layout
    embed = discord.Embed(title="Contact info", color=discord.Color.blurple())
    embed.add_field(name="Name", value=name, inline=False)
    embed.add_field(name="Prefix", value=f"`{prefix}`", inline=False)
    embed.add_field(name="Action", value=f"Say hi with {name} by typing: `{prefix}Hello!`", inline=False)
    
    if avatar_url:
        embed.set_thumbnail(url=avatar_url)
        
    await ctx.reply("Character Registered Successfully!", embed=embed)

@bot.command()
async def remove(ctx, prefix: str):
    if prefix in contacts:
        removed_name = contacts[prefix]["name"]
        del contacts[prefix]
        await ctx.reply(f"Contact **{removed_name}** (`{prefix}`) has been removed.")
    else:
        await ctx.reply(f"No contact found with prefix `{prefix}`.")

@bot.command(name="list")
async def list_contacts(ctx):
    if not contacts:
        await ctx.reply("You don't have any contacts registered yet.")
        return
    
    msg = "**Your Full Contact List:**\n"
    for prefix, data in contacts.items():
        msg += f"- **{data['name']}** | Prefix: `{prefix}text`\n"
    await ctx.reply(msg)

@bot.command()
async def avatar(ctx, prefix: str, url: str):
    if prefix in contacts:
        contacts[prefix]["avatar"] = url
        await ctx.reply(f"Avatar for `{prefix}` updated successfully!")
    else:
        await ctx.reply(f"No contact found with prefix `{prefix}`.")

@bot.command()
async def nick(ctx, prefix: str, *, nickname: str):
    if prefix in contacts:
        contacts[prefix]["nick"] = nickname
        await ctx.reply(f"Nickname for `{prefix}` set to **{nickname}**.")
    else:
        await ctx.reply(f"No contact found with prefix `{prefix}`.")

@bot.command()
async def hex(ctx, prefix: str, color_code: str):
    if prefix not in contacts:
        await ctx.reply(f"No contact found with prefix `{prefix}`.")
        return
    
    try:
        cleaned_hex = color_code.lstrip("#")
        color_int = int(cleaned_hex, 16)
        contacts[prefix]["color"] = discord.Color(color_int)
        await ctx.reply(f"Embed border color for `{prefix}` updated to `#{cleaned_hex}`!")
    except ValueError:
        await ctx.reply("Invalid hex code format! Please use something like `!hex c! #FF5733`.")

bot.run("YOUR_REAL_TOKEN_HERE")
