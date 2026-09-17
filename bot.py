import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Dictionary to store contacts by NAME: 
# { "cairo": { "prefix": "c!", "name": "Cairo", "avatar": "...", "nick": "...", "embed_color": None, "ansi_code": None, "auto_target_id": None } }
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
                # Check if message is in the target channel, thread, or category
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

        if matched_data.get("embed_color"):
            embed = discord.Embed(description=actual_text, color=matched_data["embed_color"])
            await webhook.send(
                embed=embed,
                username=display_name,
                avatar_url=avatar_url
            )
        else:
            final_content = actual_text
            if matched_data.get("ansi_code"):
                code = matched_data["ansi_code"]
                final_content = f"```ansi\n\u001b[{code}m{actual_text}\u001b[0m\n```"

            await webhook.send(
                content=final_content,
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
        "`hex! <Name> #HEXCODE` - Set embed side-bar color\n"
        "`text! <Name> #HEXCODE` - Set text color using a Hex code\n"
        "`!auto <Name> <#channel / thread_link / category>` - Auto-proxy a character\n"
        "`!unauto <Name>` - Remove auto-proxying for a character\n"
    )
    await ctx.reply(help_text)

@bot.command()
async def register(ctx, name: str, proxy_format: str):
    if not proxy_format.endswith("text"):
        await ctx.reply("Invalid format! End with `text`, like: `!register Cairo c!text`")
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
        "ansi_code": None,
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

@bot.command(name="hex")
async def hex_color(ctx, name: str, hex_code: str):
    name_key = name.lower()
    if name_key not in contacts:
        await ctx.reply(f"No contact found with the name **{name}**.")
        return
    
    try:
        clean_hex = hex_code.lstrip("#")
        color_int = int(clean_hex, 16)
        contacts[name_key]["embed_color"] = discord.Color(color_int)
        contacts[name_key]["ansi_code"] = None
        await ctx.reply(f"Embed side-bar color for **{contacts[name_key]['name']}** updated to `{hex_code}`!")
    except ValueError:
        await ctx.reply("Invalid HEX code! Please use a valid format like `#5E707A`.")

@bot.command(name="text")
async def text_color(ctx, name: str, input_val: str):
    name_key = name.lower()
    if name_key not in contacts:
        await ctx.reply(f"No contact found with the name **{name}**.")
        return
    
    if input_val.lower() == "reset":
        contacts[name_key]["ansi_code"] = None
        await ctx.reply(f"Text color for **{contacts[name_key]['name']}** has been reset.")
        return

    if input_val.startswith("#") or len(input_val) == 6:
        try:
            clean_hex = input_val.lstrip("#")
            r = int(clean_hex[0:2], 16)
            g = int(clean_hex[2:4], 16)
            b = int(clean_hex[4:6], 16)
            
            if r > 150 and g < 100 and b < 100: code = "0;31"
            elif g > 150 and r < 100: code = "0;32"
            elif r > 150 and g > 150 and b < 100: code = "0;33"
            elif b > 150 and r < 100: code = "0;34"
            elif r > 150 and b > 150: code = "0;35"
            elif g > 150 and b > 150: code = "0;36"
            elif r > 200 and g > 200 and b > 200: code = "0;37"
            else: code = "0;30"
            
            contacts[name_key]["ansi_code"] = code
            contacts[name_key]["embed_color"] = None
            await ctx.reply(f"Text color for **{contacts[name_key]['name']}** mapped from `{input_val}` successfully!")
            return
        except ValueError:
            pass

    await ctx.reply("Invalid format! Use a Hex code like `#7D8D95` or type `reset`.")

@bot.command()
async def auto(ctx, name: str, target: str = None):
    name_key = name.lower()
    if name_key not in contacts:
        await ctx.reply(f"No contact found with the name **{name}**.")
        return
    
    target_id = None
    
    # Check if a channel mention was provided (e.g. #chat)
    if ctx.message.channel_mentions:
        target_id = ctx.message.channel_mentions[0].id
    elif target:
        # Check if they pasted a thread link or ID
        if "discord.com/channels/" in target:
            try:
                parts = target.split("/")
                target_id = int(parts[-1])
            except ValueError:
                pass
        elif target.isdigit():
            target_id = int(target)
            
    if not target_id:
        # Default to current channel if none specified
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

bot.run("YOUR_REAL_TOKEN_HERE")
