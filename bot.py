import os
import asyncio
import random
import logging
from collections import defaultdict, deque

from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls import PyTgCalls, idle
from pytgcalls.types import MediaStream, AudioQuality, VideoQuality

# =========================
# LOGGING
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# =========================
# ENVIRONMENT VARIABLES
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
LOGGER_CHAT_ID = os.getenv("LOGGER_CHAT_ID")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing")

if not API_ID:
    raise RuntimeError("API_ID is missing")

if not API_HASH:
    raise RuntimeError("API_HASH is missing")

API_ID = int(API_ID)

# =========================
# TELEGRAM CLIENT
# =========================

app = Client(
    "lofi_panda_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

call_py = PyTgCalls(app)

# =========================
# MUSIC DATA
# =========================

queues = defaultdict(deque)
current = {}
loop_mode = defaultdict(lambda: "off")

# loop_mode:
# off
# song
# queue

# =========================
# LOGGER
# =========================

async def send_logger(text: str):

    if not LOGGER_CHAT_ID:
        return

    try:
        await app.send_message(
            int(LOGGER_CHAT_ID),
            text
        )
    except Exception as e:
        logging.error(
            "Logger error: %s",
            e
        )

# =========================
# USER NAME
# =========================

def get_user_name(message: Message):

    if not message.from_user:
        return "Unknown"

    if message.from_user.username:
        return "@" + message.from_user.username

    return message.from_user.first_name or "Unknown"

# =========================
# START
# =========================

@app.on_message(filters.command("start"))
async def start_handler(_, message: Message):

    await message.reply_text(
        "🎵 **LOFI PANDA MUSIC BOT**\n\n"

        "🎵 `/play URL` - Audio\n"
        "🎬 `/vplay URL` - Video\n"
        "📋 `/queue` - Queue\n"
        "⏭️ `/skip` - Skip\n"
        "⏸️ `/pause` - Pause\n"
        "▶️ `/resume` - Resume\n"
        "🛑 `/stop` - Stop\n"
        "🔀 `/shuffle` - Shuffle\n"
        "🔁 `/loop` - Loop\n"
        "🔊 `/volume 50` - Volume\n"
        "🚪 `/leave` - Leave VC\n\n"

        "⚠️ Bot ko group ke voice chat me admin permission dena zaroori hai."
    )

# =========================
# PLAY AUDIO
# =========================

@app.on_message(filters.command("play"))
async def play_handler(_, message: Message):

    if len(message.command) < 2:

        await message.reply_text(
            "❌ Use:\n`/play AUDIO_URL`"
        )

        return

    url = message.command[1]

    user = get_user_name(message)

    item = {
        "url": url,
        "type": "audio",
        "user": user,
        "title": "Audio"
    }

    chat_id = message.chat.id

    queues[chat_id].append(item)

    position = len(queues[chat_id])

    await message.reply_text(
        "🎵 **Added to Queue**\n\n"
        f"🔗 `{url}`\n"
        f"📋 Position: `{position}`"
    )

    if chat_id not in current:

        await play_next(chat_id)

# =========================
# PLAY VIDEO
# =========================

@app.on_message(filters.command("vplay"))
async def vplay_handler(_, message: Message):

    if len(message.command) < 2:

        await message.reply_text(
            "❌ Use:\n`/vplay VIDEO_URL`"
        )

        return

    url = message.command[1]

    user = get_user_name(message)

    item = {
        "url": url,
        "type": "video",
        "user": user,
        "title": "Video"
    }

    chat_id = message.chat.id

    queues[chat_id].append(item)

    position = len(queues[chat_id])

    await message.reply_text(
        "🎬 **Video Added to Queue**\n\n"
        f"🔗 `{url}`\n"
        f"📋 Position: `{position}`"
    )

    if chat_id not in current:

        await play_next(chat_id)

# =========================
# PLAY NEXT
# =========================

async def play_next(chat_id):

    if not queues[chat_id]:

        current.pop(chat_id, None)

        await send_logger(
            "🏁 **PLAYLIST ENDED**\n"
            f"💬 Chat ID: `{chat_id}`"
        )

        return

    item = queues[chat_id].popleft()

    current[chat_id] = item

    try:

        if item["type"] == "video":

            stream = MediaStream(
                item["url"],
                AudioQuality.HIGH,
                VideoQuality.HD_720p
            )

        else:

            stream = MediaStream(
                item["url"],
                AudioQuality.HIGH
            )

        await call_py.play(
            chat_id,
            stream
        )

        await send_logger(
            "▶️ **NOW PLAYING**\n"
            f"🎵 `{item['title']}`\n"
            f"👤 Requester: `{item['user']}`\n"
            f"💬 Chat ID: `{chat_id}`"
        )

    except Exception as e:

        logging.exception(
            "Playback error"
        )

        await send_logger(
            "❌ **PLAYBACK ERROR**\n"
            f"💬 Chat ID: `{chat_id}`\n"
            f"Error: `{e}`"
        )

        current.pop(chat_id, None)

        await play_next(chat_id)

# =========================
# QUEUE
# =========================

@app.on_message(filters.command("queue"))
async def queue_handler(_, message: Message):

    chat_id = message.chat.id

    text = "📋 **QUEUE**\n\n"

    if chat_id in current:

        text += (
            "▶️ **Playing:** "
            f"`{current[chat_id]['title']}`\n\n"
        )

    if not queues[chat_id]:

        text += "Queue empty."

    else:

        for number, item in enumerate(
            queues[chat_id],
            start=1
        ):

            icon = (
                "🎬"
                if item["type"] == "video"
                else "🎵"
            )

            text += (
                f"{number}. "
                f"{icon} `{item['title']}`\n"
            )

    await message.reply_text(text)

# =========================
# SKIP
# =========================

@app.on_message(filters.command("skip"))
async def skip_handler(_, message: Message):

    chat_id = message.chat.id

    if chat_id not in current:

        await message.reply_text(
            "❌ Nothing is playing."
        )

        return

    old = current.get(chat_id)

    try:

        await call_py.leave_call(
            chat_id
        )

    except Exception:
        pass

    current.pop(chat_id, None)

    await send_logger(
        "⏭️ **SKIPPED**\n"
        f"🎵 `{old['title'] if old else 'Unknown'}`\n"
        f"👤 `{old['user'] if old else 'Unknown'}`"
    )

    await message.reply_text(
        "⏭️ Skipped."
    )

    await play_next(chat_id)

# =========================
# PAUSE
# =========================

@app.on_message(filters.command("pause"))
async def pause_handler(_, message: Message):

    try:

        await call_py.pause(
            message.chat.id
        )

        await message.reply_text(
            "⏸️ Paused."
        )

    except Exception as e:

        await message.reply_text(
            f"❌ Pause error:\n`{e}`"
        )

# =========================
# RESUME
# =========================

@app.on_message(filters.command("resume"))
async def resume_handler(_, message: Message):

    try:

        await call_py.resume(
            message.chat.id
        )

        await message.reply_text(
            "▶️ Resumed."
        )

    except Exception as e:

        await message.reply_text(
            f"❌ Resume error:\n`{e}`"
        )

# =========================
# STOP
# =========================

@app.on_message(filters.command("stop"))
async def stop_handler(_, message: Message):

    chat_id = message.chat.id

    queues[chat_id].clear()

    old = current.pop(
        chat_id,
        None
    )

    try:

        await call_py.leave_call(
            chat_id
        )

    except Exception:
        pass

    await send_logger(
        "🛑 **PLAYBACK STOPPED**\n"
        f"🎵 `{old['title'] if old else 'Nothing'}`\n"
        f"💬 Chat ID: `{chat_id}`"
    )

    await message.reply_text(
        "🛑 Stopped.\n"
        "📋 Queue cleared."
    )

# =========================
# SHUFFLE
# =========================

@app.on_message(filters.command("shuffle"))
async def shuffle_handler(_, message: Message):

    chat_id = message.chat.id

    if len(queues[chat_id]) < 2:

        await message.reply_text(
            "❌ Queue me shuffle ke liye "
            "kam se kam 2 songs chahiye."
        )

        return

    items = list(
        queues[chat_id]
    )

    random.shuffle(items)

    queues[chat_id].clear()

    queues[chat_id].extend(items)

    await message.reply_text(
        "🔀 **Queue shuffled!**"
    )

# =========================
# LOOP
# =========================

@app.on_message(filters.command("loop"))
async def loop_handler(_, message: Message):

    chat_id = message.chat.id

    if len(message.command) < 2:

        await message.reply_text(
            "🔁 Use:\n"
            "`/loop off`\n"
            "`/loop song`\n"
            "`/loop queue`"
        )

        return

    mode = message.command[1].lower()

    if mode not in (
        "off",
        "song",
        "queue"
    ):

        await message.reply_text(
            "❌ Mode: off / song / queue"
        )

        return

    loop_mode[chat_id] = mode

    await message.reply_text(
        f"🔁 Loop mode: **{mode}**"
    )

# =========================
# VOLUME
# =========================

@app.on_message(filters.command("volume"))
async def volume_handler(_, message: Message):

    if len(message.command) < 2:

        await message.reply_text(
            "🔊 Use:\n`/volume 50`"
        )

        return

    try:

        volume = int(
            message.command[1]
        )

        volume = max(
            0,
            min(200, volume)
        )

        await call_py.change_volume_call(
            message.chat.id,
            volume
        )

        await message.reply_text(
            f"🔊 Volume: `{volume}`"
        )

    except Exception as e:

        await message.reply_text(
            f"❌ Volume error:\n`{e}`"
        )

# =========================
# LEAVE
# =========================

@app.on_message(filters.command("leave"))
async def leave_handler(_, message: Message):

    chat_id = message.chat.id

    queues[chat_id].clear()

    current.pop(
        chat_id,
        None
    )

    try:

        await call_py.leave_call(
            chat_id
        )

    except Exception:
        pass

    await message.reply_text(
        "🚪 Left the voice chat."
    )

# =========================
# MAIN
# =========================

async def main():

    await app.start()

    call_py.start()

    logging.info(
        "🎵 LOFI PANDA MUSIC BOT STARTED"
    )

    await idle()


if __name__ == "__main__":

    asyncio.run(main())
