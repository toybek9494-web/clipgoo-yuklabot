import os
import re
import uuid
import shutil
import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
import yt_dlp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN topilmadi! Railway Variables bo'limiga kiriting.")

# Railway Variables'dan Instagram/YouTube cookies ma'lumotini o'qish
COOKIES_PATH = "cookies.txt"
cookies_content = os.environ.get("COOKIES_CONTENT")
if cookies_content and cookies_content.strip():
    with open(COOKIES_PATH, "w", encoding="utf-8") as f:
        f.write(cookies_content.strip() + "\n")
    logging.info("cookies.txt muvaffaqiyatli yaratildi.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

BASE_DOWNLOAD_DIR = "downloads"
os.makedirs(BASE_DOWNLOAD_DIR, exist_ok=True)


def extract_clean_url(text: str) -> str | None:
    """Matn yoki forward xabar ichidan toza video havolasini ajratib olish"""
    match = re.search(r'https?://[^\s<>"\']+', text)
    if not match:
        return None

    url = match.group(0).rstrip(".,!?)")

    # Instagram havolalaridagi ortiqcha kuzatuv parametrlarini tozalash
    if "instagram.com" in url:
        url = url.split("?")[0]
        url = url.replace("/reels/", "/reel/")

    return url


def download_video_sync(url: str, temp_dir: str) -> str | None:
    """Videoni alohida vaqtinchalik papkaga 45MB limit bilan yuklab olish"""
    ydl_opts = {
        # 45MB dan oshmaydigan eng yaxshi MP4 sifatni avtomatik tanlash
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "format_sort": ["filesize~45M", "res:720", "ext:mp4:m4a"],
        "merge_output_format": "mp4",
        "outtmpl": os.path.join(temp_dir, "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "geo_bypass": True,
        "nocheckcertificate": True,
        "socket_timeout": 30,
        "retries": 3,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios", "web"]
            }
        },
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        },
    }

    if os.path.exists(COOKIES_PATH):
        ydl_opts["cookiefile"] = COOKIES_PATH

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.extract_info(url, download=True)

    # Yuklangan tayyor video faylni papkadan topish
    for filename in os.listdir(temp_dir):
        if filename.endswith((".mp4", ".mkv", ".webm", ".mov")):
            return os.path.join(temp_dir, filename)

    return None


@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    await message.answer(
        "👋 **Assalomu alaykum!**\n\n"
        "Menga quyidagi platformalardan video havolasini yuboring:\n"
        "• **Instagram** (Reels, Post)\n"
        "• **YouTube** (Shorts, Video)\n"
        "• **TikTok**\n"
        "• **Facebook**\n"
        "• **Pinterest**\n\n"
        "📎 Shunchaki linkni tashlang, men yuklab beraman.",
        parse_mode="Markdown"
    )


@dp.message(F.text | F.caption)
async def handle_video_request(message: types.Message):
    raw_text = message.text or message.caption or ""
    url = extract_clean_url(raw_text)

    if not url:
        return

    status_msg = await message.answer("⏳ Video yuklanmoqda, biroz kuting...")

    # Har bir so'rov uchun alohida noyob papka (xotirani 100% tozalash uchun)
    request_dir = os.path.join(BASE_DOWNLOAD_DIR, str(uuid.uuid4()))
    os.makedirs(request_dir, exist_ok=True)

    try:
        file_path = await asyncio.to_thread(download_video_sync, url, request_dir)

        if not file_path or not os.path.exists(file_path):
            await status_msg.edit_text("❌ Videoni yuklab bo'lmadi. Havolani tekshirib qayta yuboring.")
            return

        # Telegram Bot API 50MB limitini tekshirish
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > 49.5:
            await status_msg.edit_text(
                f"❌ Video hajmi juda katta ({file_size_mb:.1f} MB). "
                "Telegram botlar 50 MB gacha video yubora oladi."
            )
            return

        await status_msg.edit_text("📤 Video yuborilmoqda...")
        video_file = FSInputFile(file_path)
        await message.reply_video(
            video=video_file,
            caption="✅ Video muvaffaqiyatli yuklandi!",
            supports_streaming=True
        )
        await status_msg.delete()

    except yt_dlp.utils.DownloadError as e:
        logging.error(f"Yuklash xatosi ({url}): {e}")
        await status_msg.edit_text(
            "❌ Videoni yuklab bo'lmadi.\n"
            "Sabablari: profil yopiq (private), havola noto'g'ri yoki "
            "Instagram/YouTube cookies muddati tugagan."
        )
    except Exception as e:
        logging.error(f"Kutilmagan xato ({url}): {e}")
        await status_msg.edit_text("❌ Serverda kutilmagan xatolik yuz berdi. Birozdan so'ng qayta urinib ko'ring.")
    finally:
        # SERVER XOTIRASINI TO'LIQ TOZALASH (video va barcha vaqtinchalik fayllar o'chadi)
        shutil.rmtree(request_dir, ignore_errors=True)
        logging.info(f"🗑 Vaqtinchalik papka o'chirildi: {request_dir}")


async def main():
    logging.info("Bot ishga tushmoqda...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
