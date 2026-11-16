import os
import subprocess
import asyncio
import time
import glob
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

ALLOWED = {
    "twitch": "https://twitch.tv/{id}",
    "youtube": "https://youtube.com/{id}/live",
    "tiktok": "https://tiktok.com/{id}/live",
    "soop": "https://play.sooplive.com/{id}",
}

def get_stream_url(platform, uid):
    url = ALLOWED[platform].format(id=uid)
    try:
        r = subprocess.run(
            ["streamlink", url, "720p,best", "--stream-url"],
            capture_output=True, text=True, timeout=30
        )
        if r.stdout.strip().startswith("http"):
            return r.stdout.strip()
    except Exception as e:
        print(f"streamlink fail: {e}")

    try:
        r = subprocess.run(
            ["yt-dlp", url, "-f", "best[height<=720]/best", "-g"],
            capture_output=True, text=True, timeout=30
        )
        if r.stdout.strip().startswith("http"):
            return r.stdout.strip().split("\n")[0]
    except Exception as e:
        print(f"yt-dlp fail: {e}")
    return None

def do_record_5min(stream_url, base_name):
    pattern = f"{base_name}_part%03d.mp4"
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", stream_url, "-c", "copy",
             "-f", "segment", "-segment_time", "300",
             "-reset_timestamps", "1", pattern],
            timeout=3600, capture_output=True
        )
    except Exception as e:
        print(f"ffmpeg error: {e}")
    return sorted(glob.glob(f"{base_name}_part*.mp4"))

async def record_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text(
            "Usage:\n/record twitch:shroud\n/record youtube:@channel\n/record tiktok:@user\n/record soop:seoeun3104"
        )
        return

    raw = context.args[0]
    if ":" not in raw:
        await update.message.reply_text("Format: /record platform:id")
        return

    platform, uid = raw.split(":", 1)
    platform = platform.lower().strip()
    uid = uid.strip()
    if platform not in ALLOWED:
        await update.message.reply_text("twitch / youtube / tiktok / soop විතරයි")
        return

    await update.message.reply_text(f"🔍 Checking {platform}:{uid} ...")
    stream_url = await asyncio.to_thread(get_stream_url, platform, uid)

    if not stream_url:
        await update.message.reply_text("❌ Live නෑ / Stream URL හම්බුනේ නෑ")
        return

    base_name = f"{platform}_{uid}_{int(time.time())}"
    await update.message.reply_text(
        f"🔴 Recording Started\n"
        f"🎬 {platform}:{uid}\n"
        f"🎞️ 720p\n"
        f"✂️ 5 Min Parts\n"
        f"📂 Channel එකට එකින් එක යනවා"
    )

    parts = await asyncio.to_thread(do_record_5min, stream_url, base_name)

    if not parts:
        await update.message.reply_text("❌ Record Fail")
        return

    for i, part in enumerate(parts, 1):
        if not os.path.exists(part):
            continue
        size_mb = os.path.getsize(part) / 1024 / 1024
        if size_mb < 1:
            try: os.remove(part)
            except: pass
            continue
        try:
            with open(part, "rb") as f:
                await context.bot.send_document(
                    chat_id=CHANNEL_ID,
                    document=f,
                    filename=os.path.basename(part),
                    caption=f"🎬 {platform}:{uid}\n📂 Part {i}\n📦 {size_mb:.1f} MB\n🎞️ 720p | ✂️ 5 Min"
                )
            await update.message.reply_text(f"✅ Part {i} ගියා - {size_mb:.1f} MB")
        except Exception as e:
            await update.message.reply_text(f"❌ Part {i} Fail: {e}")
        try: os.remove(part)
        except: pass

    await update.message.reply_text("✅ All 5-Min Parts Done!")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 Live Recorder - 5 Min Parts\n\n"
        "/record twitch:username\n"
        "/record youtube:@channel\n"
        "/record tiktok:@user\n"
        "/record soop:id\n\n"
        "⚠️ උඹේම / Permission තියෙන Live විතරක් Record කරන්න."
    )

def main():
    if not BOT_TOKEN or not CHANNEL_ID:
        print("❌ BOT_TOKEN / CHANNEL_ID Missing!")
        return
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("record", record_command))
    print("Bot Running on Render - 5 Min Mode...")
    app.run_polling()

if __name__ == "__main__":
    main()
