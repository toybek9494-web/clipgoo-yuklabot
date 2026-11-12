import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
import yt_dlp

# Loglarni ko'rib turish uchun
logging.basicConfig(level=logging.INFO)

# Railway'dan tokenni olish
BOT_TOKEN = os.environ.get("9281776106:AAH79GywSlV4ut2wW1mHMLY237Mo-t0Ndak")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN topilmadi! Railway Variables qismiga tokenni kiriting.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Vaqtinchalik fayllar uchun papka yaratish
if not os.path.exists("downloads"):
    os.makedirs("downloads")

def download_video_sync(url: str) -> str:
    """Videoni yuklab olish va hajmini nazorat qilish"""
    ydl_opts = {
        # Sifatni va hajmni cheklash (Telegram API 50MB dan kattasini qabul qilmaydi)
        'format': 'best[filesize<=45M]/bestvideo[ext=mp4][filesize<=40M]+bestaudio[ext=m4a]/best',
        'outtmpl': 'downloads/%(extractor)s_%(id)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        # Agar video 45MB dan katta bo'lsa, yuklashni to'xtatadi
        'max_filesize': 47000000, 
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info_dict)
        return file_path

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    text = (
        "👋 Salom! Men universal video yuklovchi botman.\n\n"
        "🔗 Menga **Instagram, YouTube, TikTok, Facebook** yoki **Pinterest** video linkini yuboring."
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text.regexp(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'))
async def handle_link(message: types.Message):
    url = message.text
    status_msg = await message.answer("⏳ Video qidirilmoqda va yuklanmoqda. Iltimos kuting...")
    
    file_path = None
    try:
        # Yuklash jarayonini fon (background) rejimiga o'tkazish, bot qotib qolmasligi uchun
        file_path = await asyncio.to_thread(download_video_sync, url)
        
        if file_path and os.path.exists(file_path):
            await status_msg.edit_text("📤 Video telegramga yuklanmoqda...")
            video = FSInputFile(file_path)
            await message.reply_video(video=video, caption="✅ Video muvaffaqiyatli yuklandi!\n\n@SizningKanalYokiBotingiz")
        else:
            await status_msg.edit_text("❌ Videoni yuklashning imkoni bo'lmadi.")
            
    except yt_dlp.utils.DownloadError:
        await status_msg.edit_text("❌ Xatolik! Video yopiq (private) bo'lishi, juda katta hajmli bo'lishi yoki link noto'g'ri bo'lishi mumkin.")
    except Exception as e:
        logging.error(f"Xatolik: {e}")
        await status_msg.edit_text("❌ Kutilmagan xatolik yuz berdi. Iltimos boshqa link sinab ko'ring.")
    finally:
        # SERVERNI TOZALASH - Xotira to'lib qolmasligi uchun eng muhimi
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logging.info(f"🗑 Xotiradan o'chirildi: {file_path}")
            except Exception as e:
                logging.error(f"Faylni o'chirishda xato: {e}")

async def main():
    logging.info("Bot ishga tushirildi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())