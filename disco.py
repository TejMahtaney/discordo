import discord
from discord.ext import commands
import asyncio
from gtts import gTTS
import os

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
    289662721325268994:"Salutations my good sir Aryan, what a glorious day to be in your presence. May your harvest be ever bountiful.",
    1369250468152217664:"Glennon fattie go study! No more TFT! Glennon fattie go study! No more TFT! Glennon fattie go study! No more TFT! Glennon fattie go study! No more TFT! Glennon fattie go study! No more TFT!",
    431738148217815040:"Shut Up! A Schizophrenic is speaking. Listen and learn.",
    306421962316578816:"Rolling for a gank saving throw............ its a 4. you are cooked.",
    403898699413061643:"ITS NOT MY BIRTHDAY!ITS NOT MY BIRTHDAY!ITS NOT MY BIRTHDAY!ITS NOT MY BIRTHDAY!ITS NOT MY BIRTHDAY!ITS NOT MY BIRTHDAY!ITS NOT MY BIRTHDAY!ITS NOT MY BIRTHDAY!ITS NOT MY BIRTHDAY!ITS NOT MY BIRTHDAY! Fucking shitty ass aryan bot clearly mogged by gree",
    454277839508733963:"DEADLOCK!DEADLOCK!DEADLOCK!DEADLOCK!DEADLOCK!DEADLOCK!DEADLOCK!DEADLOCK",
    245470334512398337:"DEADLOCK!DEADLOCK!DEADLOCK!DEADLOCK!DEADLOCK!DEADLOCK!DEADLOCK!DEADLOCK",
    306704268642091009:"One Business Please",
    272336035189489669:"Today in the mental asylum, lets see if Gideon is reformed after the reformation of Gideon.",
    291461481659236352:"Chuds! Assemble!"
}

JOIN_IMAGE_CHANNEL_NAME = "general-assembly-hall"
JOIN_IMAGE_PATH = r"C:\Users\tej12\OneDrive\Desktop\discord\adnan.webp"

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
async def on_voice_state_update(member, before, after):
    if member.id == 431738148217815040 and before.channel is None and after.channel is not None:
        text_channel = discord.utils.get(member.guild.text_channels, name=JOIN_IMAGE_CHANNEL_NAME)
        if text_channel and os.path.exists(JOIN_IMAGE_PATH):
            try:
                await text_channel.send(file=discord.File(JOIN_IMAGE_PATH))
            except Exception as exc:
                print(f"Failed to send join image: {exc}")

    if member.id in USER_ANNOUNCEMENTS and before.channel is None and after.channel is not None:
        guild_id = member.guild.id
        if guild_id not in GUILD_QUEUES:
            GUILD_QUEUES[guild_id] = asyncio.Queue()

        message = USER_ANNOUNCEMENTS[member.id]
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
    announce = f" {role_mention}" if role_mention else ""
    await ctx.send(f"{announce}{mode} lobby ({len(lobby)}/{size}): {mentions}")

    if len(lobby) >= size:
        await ctx.send(f"{mode} lobby is full! {mentions}")
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
        "Available commands: !5v5, !flex, !aram, !streetbrawl, !deadlock, !join, !close, !help"
    )

bot.run(os.getenv("DISCORD_TOKEN"))