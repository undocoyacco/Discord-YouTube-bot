import os
import asyncio
from datetime import datetime
import discord
from discord.ext import commands, tasks
from googleapiclient.discovery import build

# 環境変数（Render側で設定する値）を読み込み
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID")
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0"))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

is_live = False
stream_start_time = None

youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


@tasks.loop(minutes=2)
async def check_youtube_live():
    global is_live, stream_start_time

    try:
        request = youtube.search().list(
            part="snippet",
            channelId=YOUTUBE_CHANNEL_ID,
            eventType="live",
            type="video",
        )
        response = request.execute()
        items = response.get("items", [])

        if items:
            if not is_live:
                is_live = True
                stream_start_time = datetime.now()
                video_title = items[0]["snippet"]["title"]

                channel = bot.get_channel(DISCORD_CHANNEL_ID)
                if channel:
                    await channel.send(
                        f"🎥 **配信検知！記録を開始しました**\n"
                        f"タイトル: {video_title}\n"
                        f"開始時刻: {stream_start_time.strftime('%H:%M:%S')}"
                    )
        else:
            if is_live:
                is_live = False
                stream_start_time = None
                channel = bot.get_channel(DISCORD_CHANNEL_ID)
                if channel:
                    await channel.send("🔴 **配信が終了しました。**")

    except Exception as e:
        print(f"Error checking YouTube: {e}")


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    check_youtube_live.start()


@bot.event
async def on_message(message):
    global is_live, stream_start_time

    if message.author.bot:
        return

    if message.content.startswith("今"):
        if not is_live or stream_start_time is None:
            await message.channel.send(
                "⚠️ 現在、配信中として検知されているライブがありません。"
            )
            return

        now = datetime.now()
        elapsed = now - stream_start_time
        hours, remainder = divmod(int(elapsed.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)

        timestamp_str = f"{hours:02}:{minutes:02}:{seconds:02}"
        memo = message.content[1:].strip()
        memo_text = f" ({memo})" if memo else ""

        await message.channel.send(
            f"✂️ **切り抜きタイム:** `{timestamp_str}`{memo_text}"
        )

    await bot.process_commands(message)


bot.run(DISCORD_TOKEN)
