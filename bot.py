import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Dictionary to store contacts: { "prefix": { "name": "...", "brackets": "...", "avatar": "...", "nick": "...", "auto": False } }
contacts = {}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.command(name="customhelp")
async def help_command(ctx):
    help_text = (
        "**Volt | Help Menu**\n\n"
        "**Managing Contacts**\n"
        "`!register <name> <prefix>` - Register a new character/contact\n"
        "`!remove <prefix>` - Remove a contact\n"
        "`!list` - View your full contact list\n"
        "`!rename <prefix> <new_name>` - Change a contact's name\n"
        "`!brackets <prefix> <new_brackets>` - Manage a contact's text brackets\n"
        "`!avatar <prefix> <url>` - Manage a contact's avatar\n"
        "`!nick <prefix> <nickname>` - Manage a contact's display nickname\n"
        "`!auto <prefix>` - Toggle auto-proxy for a contact"
    )
    await ctx.send(help_text)

@bot.command()
async def register(ctx, name: str, prefix: str):
    if prefix in contacts:
        await ctx.send(f"A contact with prefix `{prefix}` already exists!")
        return
    
    contacts[prefix] = {
        "name": name,
        "brackets": "text",
        "avatar": None,
        "nick": None,
        "auto": False
    }
    await ctx.send(f"Character **{name}** registered successfully with prefix `{prefix}`!")

@bot.command()
async def remove(ctx, prefix: str):
    if prefix in contacts:
        removed_name = contacts[prefix]["name"]
        del contacts[prefix]
        await ctx.send(f"Contact **{removed_name}** (`{prefix}`) has been removed.")
    else:
        await ctx.send(f"No contact found with prefix `{prefix}`.")

@bot.command(name="list")
async def list_contacts(ctx):
    if not contacts:
        await ctx.send("You don't have any contacts registered yet.")
        return
    
    msg = "**Your Full Contact List:**\n"
    for prefix, data in contacts.items():
        msg += f"- **{data['name']}** | Prefix: `{prefix}` | Nick: {data['nick']} | Auto: {data['auto']}\n"
    await ctx.send(msg)

@bot.command()
async def rename(ctx, prefix: str, new_name: str):
    if prefix in contacts:
        old_name = contacts[prefix]["name"]
        contacts[prefix]["name"] = new_name
        await ctx.send(f"Renamed contact from **{old_name}** to **{new_name}**.")
    else:
        await ctx.send(f"No contact found with prefix `{prefix}`.")

@bot.command()
async def brackets(ctx, prefix: str, new_brackets: str):
    if prefix in contacts:
        contacts[prefix]["brackets"] = new_brackets
        await ctx.send(f"Brackets for `{prefix}` updated to `{new_brackets}`.")
    else:
        await ctx.send(f"No contact found with prefix `{prefix}`.")

@bot.command()
async def avatar(ctx, prefix: str, url: str):
    if prefix in contacts:
        contacts[prefix]["avatar"] = url
        await ctx.send(f"Avatar for `{prefix}` updated successfully!")
    else:
        await ctx.send(f"No contact found with prefix `{prefix}`.")

@bot.command()
async def nick(ctx, prefix: str, *, nickname: str):
    if prefix in contacts:
        contacts[prefix]["nick"] = nickname
        await ctx.send(f"Nickname for `{prefix}` set to **{nickname}**.")
    else:
        await ctx.send(f"No contact found with prefix `{prefix}`.")

@bot.command()
async def auto(ctx, prefix: str):
    if prefix in contacts:
        current_status = contacts[prefix]["auto"]
        contacts[prefix]["auto"] = not current_status
        status_text = "enabled" if contacts[prefix]["auto"] else "disabled"
        await ctx.send(f"Auto-proxy for `{prefix}` is now **{status_text}**.")
    else:
        await ctx.send(f"No contact found with prefix `{prefix}`.")

bot.run("MTU0OTA4Njk2MDk4NjA5OTc0Mw.G77Uu7.BFkutIEWW4DGQQEZljBsXGUNGdw6ZeH51Mx9s0")
