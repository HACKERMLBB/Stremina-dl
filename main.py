import os
import subprocess
import asyncio
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

# උඹේම Channel / ID විතරක් මෙතන දාන්න
ALLOWED = {
    "twitch": "https://twitch.tv/{id}",
    "youtube": "https://youtube.com/{id}/live",
    "tiktok": "https://tiktok.com/{id}/live",
    "soop": "https://play.sooplive.com/{id}",
}

def get_stream_url(platform, uid):
    url = ALLOWED[platform].format(id=uid)
    # 1. Streamlink වලින් බලනවා
    try:
        r = subprocess.run(
            ["streamlink", url, "720p,best", "--stream-url"],
            capture_output=True, text=True, timeout=30
        )
        if r.stdout.strip().startswith("http"):
            return r.stdout.strip()
    except Exception as e:
        print(f"streamlink fail: {e}")

    # 2. Streamlink නැත්තම් yt-dlp වලින්
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

async def record_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage:\n/record twitch:shroud\n/record youtube:@channel\n/record tiktok:@user\n/record soop:seoeun3104"
        )
        return

    raw = context.args[0]
    if ":" not in raw:
        await update.message.reply_text("Format: /record platform:id")
        return

    platform, uid = raw.split(":", 1)
    platform = platform.lower()
    if platform not in ALLOWED:
        await update.message.reply_text("twitch / youtube / tiktok / soop විතරයි")
        return

    await update.message.reply_text(f"🔍 Checking {platform}:{uid} ...")
    stream_url = get_stream_url(platform, uid)

    if not stream_url:
        await update.message.reply_text("❌ Live නෑ / Stream URL හම්බුනේ නෑ")
        return

    filename = f"{platform}_{uid}_{int(time.time())}.mp4"
    await update.message.reply_text(f"🔴 Recording Started\n📂 {filename}\n🎞️ 720p")

    # Render එකේ තාවකාලිකව Record වෙනවා
    # 10 Min = 600 sec, ඊට පස්සේ නවතිනවා
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", stream_url, "-c", "copy", "-t", "600", filename],
            timeout=650
        )
    except Exception as e:
        print(f"ffmpeg error: {e}")

    if os.path.exists(filename):
        size_mb = os.path.getsize(filename) / 1024 / 1024
        # Bot API Limit එක 50MB, ඒකට වඩා ලොකු නම් Telegram එකට යවන්න බෑ
        if size_mb < 48:
            await update.message.reply_text(f"✅ Done - {size_mb:.1f} MB, Uploading...")
            with open(filename, "rb") as f:
                await update.message.reply_document(CHANNEL_ID, document=f, caption=f"🎬 {platform}:{uid}\n📦 {size_mb:.1f} MB")
        else:
            await update.message.reply_text(f"⚠️ File එක {size_mb:.1f} MB - 50MB ට වඩා වැඩියි, Telegram Bot එකෙන් යවන්න බෑ. Render එකෙන් Download කරගන්න.")
        try:
            os.remove(filename)
        except:
            pass
    else:
        await update.message.reply_text("❌ Record Fail")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎬 Live Recorder\n\n/record twitch:username\n/record youtube:@channel\n/record tiktok:@user\n/record soop:id\n\n⚠️ උඹේම / Permission තියෙන Live විතරක් Record කරන්න.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("record", record_command))
    print("Bot Running on Render...")
    app.run_polling()

if __name__ == "__main__":
    main()
