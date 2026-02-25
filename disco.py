import discord
from discord.ext import commands
import asyncio
from gtts import gTTS
import os
import aiohttp
import io
from datetime import datetime, time as dt_time
from zoneinfo import ZoneInfo
import random

intents = discord.Intents.default()
intents.voice_states = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

GUILD_QUEUES = {}
GUILD_PLAYER_TASKS = {}

LOBBY_SIZES = {
    "5v5": 10,
    "flex": 5,
    "aram": 5,
    "streetbrawl": 4,
    "deadlock": 6,
}

GUILD_LOBBIES = {}
GUILD_ACTIVE_MODE = {}

USER_ANNOUNCEMENTS = {
    289662721325268994:"Salutations my good sir Aryan, what a glorious day to be in your presence. May your steaks be ever so juicy and your lobster be ever so buttery.",
    1369250468152217664:"Glennon fattie go study! No more TFT! Glennon fattie go study! No more TFT!",
    431738148217815040:"Shut Up! A Schizophrenic is speaking. Listen and learn.",
    454277839508733963:"DEADLOCK!DEADLOCK!DEADLOCK!DEADLOCK!DEADLOCK!",
    245470334512398337:"DEADLOCK!DEADLOCK!DEADLOCK!DEADLOCK!DEADLOCK!",
    306704268642091009:"One Business Please",
    272336035189489669:"Today in the mental asylum watch, lets see if Gideon is reformed after the reformation of Gideon.",
    291461481659236352:"Chuds! Assemble!",
    444500680716320810:"Aryan Beware!!!"
}

JOIN_IMAGE_CHANNEL_NAME = "general-assembly-hall"
JOIN_IMAGE_URL = "https://raw.githubusercontent.com/TejMahtaney/discordo/main/adnan.webp"
ARYAN_JOIN_IMAGE_URL = "https://raw.githubusercontent.com/TejMahtaney/discordo/main/aryangym.jpeg"

SUBWAY_CHANNEL_NAME = "gree"
SUBWAY_TZ = ZoneInfo("Asia/Singapore")
SUBWAY_ENTRY_OPEN_TIME = dt_time(15, 0)
SUBWAY_VOTE_OPEN_TIME = dt_time(19, 0)
SUBWAY_CLOSE_TIME = dt_time(22, 0)
SUBWAY_MENU_FILE = "subway_menu.txt"

SUBWAY_MENU_ITEMS = {
    # Breads
    "italian",
    "hearty multigrain",
    "italian herbs & cheese",
    "jalapeno cheddar",
    "artisan flatbread",
    "honey oat",
    "parmesan oregano",
    "monterey cheddar",
    "artisan italian",
    "toasted rustic rye",
    "brioche-style bun",
    "ghost pepper bread",
    "gluten-free",
    # Wraps
    "spinach wrap",
    "tomato basil wrap",
    "habanero wrap",
    "wheat wrap",
    "lavash wrap",
    # Proteins/Meats
    "oven-roasted turkey",
    "black forest ham",
    "roast beef",
    "genoa salami",
    "pepperoni",
    "capicola",
    "cold cut combo",
    "grilled chicken",
    "rotisserie-style chicken",
    "teriyaki chicken",
    "buffalo chicken",
    "chipotle chicken",
    "steak",
    "meatballs",
    "tuna",
    "bacon",
    "veggie patty",
    "seafood sensation",
    # Cheeses
    "american",
    "provolone",
    "cheddar",
    "pepper jack",
    "mozzarella",
    "swiss",
    "monterey jack",
    "parmesan",
    # Vegetables
    "lettuce",
    "spinach",
    "tomatoes",
    "cucumbers",
    "green peppers",
    "red onions",
    "pickles",
    "black olives",
    "jalapenos",
    "banana peppers",
    "avocado",
    "guacamole",
    # Sauces & Dressings
    "mayonnaise",
    "ranch dressing",
    "chipotle southwest",
    "baja chipotle",
    "creamy sriracha",
    "roasted garlic aioli",
    "caesar",
    "peppercorn ranch",
    "oil & vinegar",
    "red wine vinegar",
    "mvp parmesan vinaigrette",
    "subway vinaigrette",
    "yellow mustard",
    "honey mustard",
    "dijon mustard",
    "sweet onion",
    "buffalo sauce",
    "bbq sauce",
    "sriracha",
    "marinara sauce",
    "basil pesto",
    # Seasonings/Extras
    "salt",
    "pepper",
    "oregano",
    "sub spice",
}


def _normalize_menu_item(text):
    return " ".join(text.lower().strip().split())

SUBWAY_STATE = {}
SUBWAY_SCHEDULER_TASK = None


def _sgt_now():
    return datetime.now(tz=SUBWAY_TZ)


def _get_subway_state(guild_id):
    return SUBWAY_STATE.setdefault(
        guild_id,
        {
            "entries_open": False,
            "votes_open": False,
            "entries": {},
            "votes": {},
            "last_open_date": None,
            "last_vote_open_date": None,
            "last_close_date": None,
        },
    )


def _get_subway_channel(guild):
    return discord.utils.get(guild.text_channels, name=SUBWAY_CHANNEL_NAME)


def _get_announcement_message(member_id):
    if member_id == 306421962316578816:
        roll = random.randint(1, 20)
        if roll == 1:
            return f"Rolling for a gank saving throw............ its a {roll}. Its naked adventure round 2."
        if roll == 20:
            return f"Rolling for a gank saving throw............ its a nat {roll}. Unfortunately, you are still cooked."
        else:
            return f"Rolling for a gank saving throw............ its a {roll}. you are cooked."
    return USER_ANNOUNCEMENTS.get(member_id)


async def _send_subway_message(ctx, content=None, **kwargs):
    channel = _get_subway_channel(ctx.guild) if ctx.guild else None
    if channel:
        await channel.send(content, **kwargs)
    else:
        await ctx.send(content, **kwargs)


async def _announce_subway_open(guild):
    state = _get_subway_state(guild.id)
    state["entries_open"] = True
    state["votes_open"] = False
    state["entries"] = {}
    state["votes"] = {}
    state["last_open_date"] = _sgt_now().date()

    text_channel = _get_subway_channel(guild)
    if text_channel:
        message = (
            "Subway Thursday is now open for entries!\n"
            "Rules: Thu only (SGT). One entry per user. One vote per user. No self-votes.\n"
            "How to enter: !sandwich <ingredients>. Use the attached menu.\n"
            "Voting opens at 7:00 PM SGT. Competition closes at 10:00 PM SGT."
        )
        if os.path.exists(SUBWAY_MENU_FILE):
            await text_channel.send(message, file=discord.File(SUBWAY_MENU_FILE))
        else:
            await text_channel.send(message)


async def _announce_subway_vote_open(guild):
    state = _get_subway_state(guild.id)
    state["votes_open"] = True
    state["last_vote_open_date"] = _sgt_now().date()

    text_channel = _get_subway_channel(guild)
    if text_channel:
        await text_channel.send(
            "Subway Thursday voting is now open! Vote with !vote @user. Closes at 10:00 PM SGT."
        )


async def _announce_subway_close(guild):
    state = _get_subway_state(guild.id)
    state["entries_open"] = False
    state["votes_open"] = False
    state["last_close_date"] = _sgt_now().date()

    text_channel = _get_subway_channel(guild)
    if not text_channel:
        return

    if not state["entries"]:
        await text_channel.send("Subway Thursday is closed. No entries this week.")
        return

    if not state["votes"]:
        await text_channel.send("Subway Thursday is closed. No votes were cast.")
        return

    tally = {}
    for entry_user_id in state["votes"].values():
        tally[entry_user_id] = tally.get(entry_user_id, 0) + 1

    max_votes = max(tally.values())
    winners = [user_id for user_id, count in tally.items() if count == max_votes]
    winner_mentions = " ".join(f"<@{user_id}>" for user_id in winners)

    await text_channel.send(
        f"Subway Thursday is closed! Winner{'s' if len(winners) > 1 else ''}: {winner_mentions} "
        f"with {max_votes} vote{'s' if max_votes != 1 else ''}."
    )


async def _subway_scheduler():
    await bot.wait_until_ready()
    while not bot.is_closed():
        now = _sgt_now()
        if now.weekday() == 3:
            for guild in bot.guilds:
                state = _get_subway_state(guild.id)
                if now.time() >= SUBWAY_CLOSE_TIME:
                    if state["last_close_date"] != now.date():
                        await _announce_subway_close(guild)
                elif now.time() >= SUBWAY_VOTE_OPEN_TIME:
                    if state["last_vote_open_date"] != now.date():
                        await _announce_subway_vote_open(guild)
                elif now.time() >= SUBWAY_ENTRY_OPEN_TIME:
                    if state["last_open_date"] != now.date():
                        await _announce_subway_open(guild)

        await asyncio.sleep(30)

async def _guild_player(guild_id, guild):
    queue = GUILD_QUEUES[guild_id]
    vc = None
    try:
        while True:
            member, voice_channel, message = await queue.get()
            audio_file = None
            try:
                try:
                    if not guild.voice_client:
                        vc = await voice_channel.connect(timeout=20)
                    else:
                        vc = guild.voice_client
                        if vc.channel != voice_channel:
                            await vc.move_to(voice_channel)
                except asyncio.TimeoutError:
                    print("Voice connect timeout")
                    continue

                audio_file = f"announcement_{member.id}_{int(asyncio.get_running_loop().time() * 1000)}.mp3"

                await asyncio.to_thread(lambda: gTTS(text=message, lang='en', slow=False).save(audio_file))

                await asyncio.sleep(0.5)

                if not vc or not vc.is_connected():
                    try:
                        vc = await voice_channel.connect(timeout=20)
                    except asyncio.TimeoutError:
                        print("Voice connect timeout")
                        continue

                vc.play(discord.FFmpegPCMAudio(audio_file))
                while vc.is_playing():
                    await asyncio.sleep(0.1)
            finally:
                queue.task_done()
                try:
                    if audio_file and os.path.exists(audio_file):
                        os.remove(audio_file)
                except Exception:
                    pass

            if queue.empty():
                break
    finally:
        if guild.voice_client:
            await guild.voice_client.disconnect()
        GUILD_PLAYER_TASKS.pop(guild_id, None)


@bot.event
async def on_ready():
    global SUBWAY_SCHEDULER_TASK
    if not SUBWAY_SCHEDULER_TASK or SUBWAY_SCHEDULER_TASK.done():
        SUBWAY_SCHEDULER_TASK = asyncio.create_task(_subway_scheduler())


@bot.event
async def on_voice_state_update(member, before, after):
    if member.id == 431738148217815040 and before.channel is None and after.channel is not None:
        text_channel = discord.utils.get(member.guild.text_channels, name=JOIN_IMAGE_CHANNEL_NAME)
        if text_channel:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(JOIN_IMAGE_URL) as response:
                        response.raise_for_status()
                        data = await response.read()
                image_fp = io.BytesIO(data)
                await text_channel.send(file=discord.File(image_fp, filename="adnan.webp"))
            except Exception as exc:
                print(f"Failed to send join image: {exc}")

    if member.id == 431738148217815040 and before.channel is None and after.channel is not None:
        text_channel = discord.utils.get(member.guild.text_channels, name=JOIN_IMAGE_CHANNEL_NAME)
        if text_channel:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(ARYAN_JOIN_IMAGE_URL) as response:
                        response.raise_for_status()
                        data = await response.read()
                image_fp = io.BytesIO(data)
                await text_channel.send(file=discord.File(image_fp, filename="aryanjpg.jpeg"))
            except Exception as exc:
                print(f"Failed to send join image: {exc}")

    if before.channel is None and after.channel is not None:
        guild_id = member.guild.id
        if guild_id not in GUILD_QUEUES:
            GUILD_QUEUES[guild_id] = asyncio.Queue()
        message = _get_announcement_message(member.id)
        if message:
            await GUILD_QUEUES[guild_id].put((member, after.channel, message))

            task = GUILD_PLAYER_TASKS.get(guild_id)
            if not task or task.done():
                GUILD_PLAYER_TASKS[guild_id] = asyncio.create_task(_guild_player(guild_id, member.guild))


def _get_lobby(guild_id, mode):
    guild_lobbies = GUILD_LOBBIES.setdefault(guild_id, {})
    return guild_lobbies.setdefault(mode, [])


def _get_role_mention(guild, role_name):
    role = discord.utils.get(guild.roles, name=role_name)
    return role.mention if role else None


async def _start_lobby(ctx, mode):
    guild_id = ctx.guild.id
    GUILD_ACTIVE_MODE[guild_id] = mode
    GUILD_LOBBIES.setdefault(guild_id, {})[mode] = []
    role_mention = None
    if mode == "5v5":
        role_mention = _get_role_mention(ctx.guild, "5v5")
    announce = f" {role_mention}" if role_mention else ""
    await ctx.send(f"{announce}Lobby started for {mode}. Use !join to enter.")


@bot.command(name="5v5")
async def lobby_5v5(ctx):
    await _start_lobby(ctx, "5v5")


@bot.command(name="flex")
async def lobby_flex(ctx):
    await _start_lobby(ctx, "flex")


@bot.command(name="aram")
async def lobby_aram(ctx):
    await _start_lobby(ctx, "aram")


@bot.command(name="streetbrawl")
async def lobby_streetbrawl(ctx):
    await _start_lobby(ctx, "streetbrawl")


@bot.command(name="deadlock")
async def lobby_deadlock(ctx):
    await _start_lobby(ctx, "deadlock")


@bot.command(name="join")
async def lobby_join(ctx):
    guild_id = ctx.guild.id
    mode = GUILD_ACTIVE_MODE.get(guild_id)
    if not mode:
        await ctx.send("No active lobby. Start one with !5v5, !flex, !aram, !streetbrawl, or !deadlock.")
        return

    lobby = _get_lobby(guild_id, mode)
    if ctx.author.id in lobby:
        await ctx.send(f"{ctx.author.mention} is already in the {mode} lobby.")
        return

    lobby.append(ctx.author.id)
    size = LOBBY_SIZES[mode]
    mentions = " ".join(f"<@{user_id}>" for user_id in lobby)
    role_mention = None
    if mode == "5v5":
        role_mention = _get_role_mention(ctx.guild, "5v5")
    ping_role = mode == "5v5" and role_mention and len(lobby) >= 9
    announce = f" {role_mention}" if ping_role else ""
    await ctx.send(f"{announce}{mode} lobby ({len(lobby)}/{size}): {mentions}")

    if len(lobby) >= size:
        full_announce = f" {role_mention}" if ping_role else ""
        await ctx.send(f"{full_announce}{mode} lobby is full! {mentions}")
        GUILD_LOBBIES[guild_id][mode] = []
        GUILD_ACTIVE_MODE[guild_id] = None


@bot.command(name="close")
async def lobby_close(ctx):
    guild_id = ctx.guild.id
    mode = GUILD_ACTIVE_MODE.get(guild_id)
    if not mode:
        await ctx.send("No active lobby to close.")
        return

    lobby = _get_lobby(guild_id, mode)
    if ctx.author.id not in lobby:
        await ctx.send("Only a user in the lobby can close it.")
        return

    GUILD_LOBBIES[guild_id][mode] = []
    GUILD_ACTIVE_MODE[guild_id] = None
    await ctx.send(f"Closed the {mode} lobby.")


@bot.command(name="help")
async def help_command(ctx):
    await ctx.send(
        "Available commands: !5v5, !flex, !aram, !streetbrawl, !deadlock, !join, !close, "
        "!subway, !sandwich, !vote, !help"
    )


@bot.command(name="subway")
async def subway_info(ctx):
    if not ctx.guild:
        return
    state = _get_subway_state(ctx.guild.id)
    entries_status = "open" if state["entries_open"] else "closed"
    votes_status = "open" if state["votes_open"] else "closed"
    entries_count = len(state["entries"])
    votes_count = len(state["votes"])
    await _send_subway_message(
        ctx,
        "Subway Thursday status (SGT): "
        f"Entries {entries_status} (3:00-7:00 PM). "
        f"Voting {votes_status} (7:00-10:00 PM). "
        f"Entries: {entries_count}. Votes: {votes_count}."
    )


@bot.command(name="sandwich")
async def subway_sandwich(ctx, *, entry: str):
    if not ctx.guild:
        return
    now = _sgt_now()
    state = _get_subway_state(ctx.guild.id)
    in_event_window = now.weekday() == 3 and state["entries_open"]

    entry = entry.strip()
    if not entry:
        await _send_subway_message(ctx, "Please include your sandwich details. Example: !sandwich turkey, jalapenos, chipotle")
        return

    parts = [part.strip() for part in entry.split(",") if part.strip()]
    if not parts:
        await _send_subway_message(ctx, "Please include at least one menu item, separated by commas.")
        return

    invalid = [item for item in parts if _normalize_menu_item(item) not in SUBWAY_MENU_ITEMS]
    if invalid:
        invalid_list = ", ".join(invalid[:6])
        suffix = "..." if len(invalid) > 6 else ""
        await _send_subway_message(
            "Some items are not on the menu: "
            f"{invalid_list}{suffix}. Please use the attached menu."
        )
        return

    if in_event_window:
        state["entries"][ctx.author.id] = entry
    receipt_lines = ["Subway Thursday Receipt", f"Customer: {ctx.author.display_name}", "Items:"]
    receipt_lines.extend(f"- {item}" for item in parts)
    receipt_lines.append("Total: 1 entry")
    receipt_text = "\n".join(receipt_lines)
    status_note = "" if in_event_window else " (not part of Subway Thursday)"
    await _send_subway_message(
        ctx,
        f"{ctx.author.mention} submitted a sandwich entry{status_note}.\n```\n{receipt_text}\n```",
    )


@bot.command(name="vote")
async def subway_vote(ctx, member: discord.Member):
    if not ctx.guild:
        return
    now = _sgt_now()
    if now.weekday() != 3:
        await _send_subway_message(ctx, "Subway Thursday voting is only open on Thursdays (SGT).")
        return
    state = _get_subway_state(ctx.guild.id)
    if not state["votes_open"]:
        await _send_subway_message(ctx, "Subway Thursday voting is closed. It opens at 7:00 PM SGT.")
        return

    if member.id == ctx.author.id:
        await _send_subway_message(ctx, "You cannot vote for your own sandwich.")
        return

    if member.id not in state["entries"]:
        await _send_subway_message(ctx, "That user does not have a sandwich entry.")
        return

    previous = state["votes"].get(ctx.author.id)
    state["votes"][ctx.author.id] = member.id
    if previous and previous != member.id:
        await _send_subway_message(ctx, f"{ctx.author.mention} updated their vote to {member.mention}.")
    else:
        await _send_subway_message(ctx, f"{ctx.author.mention} voted for {member.mention}.")


@bot.command(name="roll")
async def roll_command(ctx):
    if ctx.author.id == 175796967920762880 or ctx.author.id == 403898699413061643:
        result = random.randint(90,100)
    elif ctx.author.id == 371914348656066561 or ctx.author.id == 1369250468152217664:
        result = random.randint(1,10)
    else:
        result = random.randint(1, 100)
    if result == 67:
        await ctx.send(f"{ctx.author.mention} rolled **{result}**. @everyone")
    else:
        await ctx.send(f"{ctx.author.mention} rolled **{result}**.")


bot.run(os.getenv("DISCORD_TOKEN"))





