import os
import json
import requests
import time
import itertools
import discord
from discord.ext import commands

CONFIG_FILE = "config.json"

class Colors:
    PURPLE = "\033[95m"
    DARKBLUE = "\033[94m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"

def print_banner():
    line = Colors.PURPLE + Colors.BOLD + "=" * 31 + Colors.ENDC
    title = Colors.PURPLE + Colors.BOLD + "   SectorX- Discord Cloner   " + Colors.ENDC
    print(f"{line}\n{title}\n{line}\n")
print("How to use: Discord user token to read the server channels, discord bot to create the channels and other stuff." \
"discord bot need to have admin on the server you want to clone to <3")
ticker = itertools.cycle(['◐', '◓', '◑', '◒'])
def log(message, color=Colors.DARKBLUE, end="\n"):
    ts = time.strftime("%H:%M:%S")
    spin = next(ticker)
    print(f"{Colors.PURPLE}[{ts}]{Colors.ENDC} {spin} {color}{message}{Colors.ENDC}", end=end)

def init_config():
    if not os.path.exists(CONFIG_FILE):
        log("Config not found, creating config.json...", Colors.DARKBLUE)
        user_token = input(f"{Colors.PURPLE}[?]{Colors.ENDC} Enter your User Token: ").strip()
        bot_token = input(f"{Colors.PURPLE}[?]{Colors.ENDC} Enter your Bot Token: ").strip()
        with open(CONFIG_FILE, 'w') as f:
            json.dump({"user_token": user_token, "bot_token": bot_token}, f, indent=4)
        log("Config saved.", Colors.DARKBLUE)
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def fetch_server_data(user_token, guild_id):
    headers = {"Authorization": user_token, "Content-Type": "application/json"}
    log("Fetching server info...", Colors.DARKBLUE)
    base = "https://discord.com/api/v10"
    resp = requests.get(f"{base}/guilds/{guild_id}", headers=headers)
    resp_roles = requests.get(f"{base}/guilds/{guild_id}/roles", headers=headers)
    resp_channels = requests.get(f"{base}/guilds/{guild_id}/channels", headers=headers)
    resp_stickers = requests.get(f"{base}/guilds/{guild_id}/stickers", headers=headers)

    if resp.status_code != 200:
        log(f"Error fetching guild info: {resp.status_code}", Colors.DARKBLUE)
        return None
    if resp_roles.status_code != 200 or resp_channels.status_code != 200:
        log(f"Error fetching roles/channels: {resp_roles.status_code}/{resp_channels.status_code}", Colors.DARKBLUE)
        return None
    if resp_stickers.status_code != 200:
        log(f"Error fetching stickers: {resp_stickers.status_code}", Colors.DARKBLUE)

    guild_data = resp.json()
    roles = resp_roles.json()
    channels = resp_channels.json()
    stickers = resp_stickers.json() if resp_stickers.status_code == 200 else []

    icon_bytes = None
    if guild_data.get('icon'):
        icon_url = f"https://cdn.discordapp.com/icons/{guild_id}/{guild_data['icon']}.png"
        icon_bytes = requests.get(icon_url).content
        log("Server icon downloaded.", Colors.DARKBLUE)

    log("Server data retrieved.", Colors.DARKBLUE)
    return {
        'info': guild_data,
        'roles': roles,
        'channels': channels,
        'stickers': stickers,
        'icon_bytes': icon_bytes
    }

def run_clone(options, data):
    discord.utils.setup_logging(level=100)
    bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())

    @bot.event
    async def on_ready():
        log("Logged in.", Colors.DARKBLUE)
        guild = bot.get_guild(int(options['target_guild']))
        if not guild:
            log("Cannot access target server.", Colors.DARKBLUE)
            return await bot.close()
        log(f"Cloning to: {guild.name}", Colors.DARKBLUE)

        if options['del_channels']:
            for ch in guild.channels:
                try: await ch.delete()
                except: pass
            log("Existing channels deleted.", Colors.DARKBLUE)
        if options['del_roles']:
            for r in guild.roles:
                if r.name != '@everyone':
                    try: await r.delete()
                    except: pass
            log("Existing roles deleted.", Colors.DARKBLUE)
        if options['del_stickers']:
            for s in guild.stickers:
                try: await s.delete()
                except: pass
            log("Existing stickers deleted.", Colors.DARKBLUE)

        if options['clone_name']:
            await guild.edit(name=data['info']['name'])
            log(f"Server name set to: {data['info']['name']}", Colors.DARKBLUE)

        if options['clone_icon'] and data['icon_bytes']:
            try:
                await guild.edit(icon=data['icon_bytes'])
                log("Server icon cloned.", Colors.DARKBLUE)
            except: log("Failed to set server icon.", Colors.DARKBLUE)

        role_map = {}
        if options['clone_roles']:
            for r in reversed(data['roles']):
                if r['name'] != '@everyone':
                    try:
                        role_obj = await guild.create_role(
                            name=r['name'],
                            permissions=discord.Permissions(int(r['permissions'])),
                            color=discord.Colour(int(r['color'])),
                            hoist=r['hoist'],
                            mentionable=r['mentionable']
                        )
                        role_map[r['id']] = role_obj
                        log(f"Role created: {r['name']}", Colors.DARKBLUE)
                    except: pass

        if options['clone_stickers']:
            for s in data['stickers']:
                try:
                    img = requests.get(f"https://cdn.discordapp.com/stickers/{s['id']}.png").content
                    await guild.create_sticker(
                        name=s['name'],
                        description=s.get('description',''),
                        tags=s.get('tags',''),
                        file=discord.File(fp=img, filename='sticker.png')
                    )
                    log(f"Sticker created: {s['name']}", Colors.DARKBLUE)
                except: pass

        if options['clone_channels']:
            cat_map = {}
            for ch in data['channels']:
                if ch['type'] == 4:
                    cat = await guild.create_category(ch['name'])
                    cat_map[ch['id']] = cat
                    log(f"Category: {ch['name']}", Colors.DARKBLUE)
            for ch in data['channels']:
                parent = cat_map.get(ch.get('parent_id'))
                overwrites = {}
                for o in ch.get('permission_overwrites', []):
                    target = role_map.get(o['id'])
                    if target:
                        allow = discord.Permissions(int(o['allow']))
                        deny = discord.Permissions(int(o['deny']))
                        overwrites[target] = discord.PermissionOverwrite.from_pair(allow, deny)
                try:
                    if ch['type'] == 0:
                        await guild.create_text_channel(ch['name'], category=parent, overwrites=overwrites)
                    elif ch['type'] == 2:
                        await guild.create_voice_channel(ch['name'], category=parent, overwrites=overwrites)
                    log(f"Channel: {ch['name']}", Colors.DARKBLUE)
                except: pass

        log("Clone complete!", Colors.DARKBLUE)
        await bot.close()

    bot.run(options['bot_token'])

if __name__ == '__main__':
    print_banner()
    config = init_config()
    opts = {}
    opts['source_guild'] = input(f"{Colors.PURPLE}[?]{Colors.ENDC} Source Guild ID: ")
    opts['target_guild'] = input(f"{Colors.PURPLE}[?]{Colors.ENDC} Target Guild ID: ")

    opts['clone_name'] = input(f"{Colors.PURPLE}[?]{Colors.ENDC} Clone server name? (y/N): ").lower() == 'y'
    opts['del_channels'] = input(f"{Colors.PURPLE}[?]{Colors.ENDC} Delete existing channels? (y/N): ").lower() == 'y'
    opts['del_roles'] = input(f"{Colors.PURPLE}[?]{Colors.ENDC} Delete existing roles? (y/N): ").lower() == 'y'
    opts['del_stickers'] = input(f"{Colors.PURPLE}[?]{Colors.ENDC} Delete existing stickers? (y/N): ").lower() == 'y'
    opts['clone_icon'] = input(f"{Colors.PURPLE}[?]{Colors.ENDC} Clone server icon? (y/N): ").lower() == 'y'
    opts['clone_roles'] = input(f"{Colors.PURPLE}[?]{Colors.ENDC} Clone roles? (y/N): ").lower() == 'y'
    opts['clone_stickers'] = input(f"{Colors.PURPLE}[?]{Colors.ENDC} Clone stickers? (y/N): ").lower() == 'y'
    opts['clone_channels'] = input(f"{Colors.PURPLE}[?]{Colors.ENDC} Clone channels? (y/N): ").lower() == 'y'
    opts['bot_token'] = config['bot_token']

    data = fetch_server_data(config['user_token'], opts['source_guild'])
    if data:
        run_clone(opts, data)
    else:
        log("Aborted due to errors.", Colors.DARKBLUE)
