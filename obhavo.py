import asyncio
import logging
import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from datetime import datetime
import pytz
import aioschedule

# ✅ OpenWeather API kaliti
OPENWEATHER_API_KEY = "ac2610f9e1afd26e59ee480be0df3a59"

# ✅ Telegram bot tokeni
BOT_TOKEN = "7587955088:AAEJlTfySp9vuPv817CaguKKFY-1gkhUBaQ"

uzbekistan_tz = pytz.timezone("Asia/Tashkent")

# 🔹 Obuna bo'lgan foydalanuvchilar va ularning joylashuvi
subscribed_users = {}  # {user_id: city}

# 🔹 Viloyatlar ro‘yxati
regions = [
    ["Toshkent", "Samarqand"],
    ["Buxoro", "Xiva"],
    ["Andijon", "Farg'ona"],
    ["Namangan", "Jizzax"],
    ["Sirdaryo", "Qashqadaryo"],
    ["Termiz", "Navoiy"]
]

# 🔹 Emoji bilan ob-havo tarjimalari
weather_translations = {
    "clear sky": "Ochiq osmon ☀️",
    "few clouds": "Ozroq bulutli 🌤",
    "scattered clouds": "Sochilgan bulutlar ⛅",
    "broken clouds": "Parcha-parcha bulutlar 🌥",
    "overcast clouds": "Qorong‘i bulutlar ☁️",
    "shower rain": "Yomg‘ir yog‘moqda 🌦",
    "rain": "Yomg‘ir 🌧",
    "thunderstorm": "Momaqaldiroq ⛈",
    "snow": "Qor ❄️",
    "mist": "Tuman 🌫",
    "light rain": "Yengil yomg'ir 🌦",
    "light intensity shower rain": "Yengil, kuchsiz yomg'irli jala 🌧"
}

# ✅ Bot va Dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# 🔹 Boshlang‘ich tanlov tugmalari
def start_menu():
    buttons = [
        [InlineKeyboardButton(text="🟢 Hozirgi ob-havo", callback_data="current")],
        [InlineKeyboardButton(text="📆 7 kunlik prognoz", callback_data="forecast")],
        [InlineKeyboardButton(text="📍 GPS asosida ob-havo", callback_data="gps")],
        [InlineKeyboardButton(text="🔔 Obuna", callback_data="subscribe")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# 🔹 Viloyatlar uchun inline tugmalar
def create_inline_keyboard(weather_type="current"):
    keyboard = [[InlineKeyboardButton(text=region, callback_data=f"{weather_type}_region_{region}") for region in row] for row in regions]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# 🔹 Ha/Yo‘q tugmalari
def confirmation_keyboard():
    buttons = [
        [InlineKeyboardButton(text="✅ Ha", callback_data="confirm_yes")],
        [InlineKeyboardButton(text="❌ Yo‘q", callback_data="confirm_no")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# 🔹 Hozirgi ob-havo ma'lumotlarini olish
def get_current_weather(city: str):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=en"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        city_name = data["name"]
        temp = data["main"]["temp"]
        feels_like = data["main"]["feels_like"]
        weather_desc = data["weather"][0]["description"]
        humidity = data["main"]["humidity"]
        wind_speed = data["wind"]["speed"]
        weather_desc_uz = weather_translations.get(weather_desc.lower(), weather_desc)

        return (f"🌤 <b>{city_name} ob-havosi (hozirgi):</b>\n"
                f"🌡 <b>Harorat:</b> {temp}°C\n"
                f"🤒 <b>His qilinishi:</b> {feels_like}°C\n"
                f"🌦 <b>Holati:</b> {weather_desc_uz}\n"
                f"💧 <b>Namlik:</b> {humidity}%\n"
                f"🌬 <b>Shamol tezligi:</b> {wind_speed} m/s")
    else:
        return "❌ Ob-havo ma'lumotlarini olishda xatolik yuz berdi!"

# 🔹 7 kunlik ob-havo prognozini olish
def get_weather_forecast(city: str, days=7):
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&cnt={days}&appid={OPENWEATHER_API_KEY}&units=metric&lang=en"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        city_name = data["city"]["name"]
        forecasts = data["list"]

        result = f"📍 <b>{city_name} ob-havo prognozi (7 kun):</b>\n\n"
        for day in forecasts:
            date = datetime.utcfromtimestamp(day["dt"]).strftime("%d-%m-%Y")
            temp = day["main"]["temp"]
            weather_desc = day["weather"][0]["description"]
            weather_desc_uz = weather_translations.get(weather_desc.lower(), weather_desc)

            result += f"📅 <b>{date}</b>\n"
            result += f"🌡 <b>Harorat:</b> {temp}°C\n"
            result += f"🌦 <b>Holati:</b> {weather_desc_uz}\n"
            result += "--------------------------\n"

        return result
    else:
        return "❌ Ob-havo ma'lumotlarini olishda xatolik yuz berdi!"

# 🔹 GPS orqali ob-havo olish
def get_weather_by_location(lat, lon):
    url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric&lang=en"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        city_name = data.get("name") or data["sys"].get("country", "Noma'lum joy")
        temp = data["main"]["temp"]
        weather_desc = data["weather"][0]["description"]
        weather_desc_uz = weather_translations.get(weather_desc.lower(), weather_desc)

        return city_name, (f"📍 <b>{city_name} ob-havosi:</b>\n"
                          f"🌡 <b>Harorat:</b> {temp}°C\n"
                          f"🌦 <b>Holati:</b> {weather_desc_uz}\n")
    else:
        return None, "❌ GPS orqali ob-havo ma'lumotlarini olishda xatolik yuz berdi!"

# 🔹 GPS orqali joylashuv va obuna
@dp.message(F.location)
async def location_weather(message: Message):
    lat = message.location.latitude
    lon = message.location.longitude
    city_name, weather_info = get_weather_by_location(lat, lon)
    await message.answer(weather_info, parse_mode="HTML")
    
    # Agar foydalanuvchi obuna uchun GPS yuborgan bo‘lsa
    if message.reply_to_message and "GPS yuborish uchun" in message.reply_to_message.text:
        if city_name:
            subscribed_users[message.from_user.id] = city_name
            await message.answer(f"✅ {city_name} uchun obuna bo‘ldingiz! Har kuni 06:00 da ob-havo ma'lumoti keladi.")
        else:
            await message.answer("❌ Joylashuvni aniqlashda xatolik yuz berdi, qayta urinib ko'ring.")

# 🔹 Har kuni 06:00 da obuna bo‘lganlarga ob-havo yuborish
async def send_daily_weather():
    for user_id, city in subscribed_users.items():
        weather_info = get_current_weather(city)
        try:
            await bot.send_message(user_id, weather_info, parse_mode="HTML")
        except:
            pass

# 🔹 Fon jarayon sifatida ishlaydigan scheduler
async def scheduler():
    aioschedule.every().day.at("06:00").do(send_daily_weather)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(60)

# 🔹 /start komandasi
@dp.message(Command("start"))
async def start_command(message: Message):
    await message.answer(
        f"👋 Assalomu alaykum, <b>{message.from_user.full_name}</b>!\n\n"
        "🔃 Quyidagi funksiyalardan birini tanlang:",
        reply_markup=start_menu(),
        parse_mode="HTML"
    )

# 🔹 Boshlang‘ich tanlovlar
@dp.callback_query(F.data.in_(["current", "forecast"]))
async def weather_type_callback(callback: types.CallbackQuery):
    weather_type = callback.data
    await callback.message.answer(f"📍 <b> 🇺🇿 Ob-havo ma'lumotini olish uchun viloyatni tanlang:</b> 👇🏻", 
                                  reply_markup=create_inline_keyboard(weather_type), parse_mode="HTML")
    await callback.answer()

# 🔹 Viloyatni tanlash (Hozirgi yoki 7 kunlik)
@dp.callback_query(F.data.startswith("current_region_") | F.data.startswith("forecast_region_"))
async def region_callback(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    weather_type, city = parts[0], parts[2]
    
    if weather_type == "current":
        weather_info = get_current_weather(city)
    else:  # forecast
        weather_info = get_weather_forecast(city)
    
    await callback.message.answer(weather_info, parse_mode="HTML")
    await callback.message.answer("Yana ob-havo ma'lumotini olishni xohlaysizmi?", reply_markup=confirmation_keyboard())
    await callback.answer()

# 🔹 Obuna tanlansa
@dp.callback_query(F.data == "subscribe")
async def subscribe_callback(callback: types.CallbackQuery):
    await callback.message.answer("<b>📍 Obuna uchun joylashuvingizni GPS orqali yuboring yoki viloyatni tanlang:</b>", 
                                  reply_markup=create_inline_keyboard("subscribe"), parse_mode="HTML")
    await callback.message.answer("<b>GPS yuborish uchun joylashuvingizni yuboring (Telegramda 'Location' tugmasini bosib yuboring).</b>", parse_mode="HTML")
    await callback.answer()

# 🔹 Viloyat orqali obuna
@dp.callback_query(F.data.startswith("subscribe_region_"))
async def subscribe_region_callback(callback: types.CallbackQuery):
    city = callback.data.split("_")[2]
    subscribed_users[callback.from_user.id] = city
    await callback.message.answer(f"✅<b> {city} viloayti uchun har kunlik ob-havo ma'lumotiga obuna bo'ldingiz! Har kuni 06:00 da ob-havo ma'lumoti keladi.Obunani bekor qilish uchun /obuna_bekor ni yuboring.</b>",parse_mode="HTML")
    await callback.answer()

# 🔹 GPS tanlansa
@dp.callback_query(F.data == "gps")
async def gps_callback(callback: types.CallbackQuery):
    await callback.message.answer("📍 Iltimos, joylashuvingizni yuboring (Telegramda 'Location' tugmasini bosing).")
    await callback.answer()

# 🔹 Obunani bekor qilish
@dp.message(Command("obuna_bekor"))
async def unsubscribe_weather(message: Message):
    if message.from_user.id in subscribed_users:
        del subscribed_users[message.from_user.id]
        await message.answer("🔕 Obuna bekor qilindi.")
    else:
        await message.answer("❌ Siz obuna bo'lmagansiz!")

# 🔹 Ha/Yo‘q tugmalari
@dp.callback_query(F.data == "confirm_yes")
async def confirm_yes(callback: types.CallbackQuery):
    await callback.message.answer("<b>Yana funksiyalardan birini tanlang:</b>", reply_markup=start_menu(), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "confirm_no")
async def confirm_no(callback: types.CallbackQuery):
    await callback.message.answer("<b>😊 Rahmat! Yana Ob-Havo ma'lumoti kerak bo'lsa, /start ni bosing.</b>", parse_mode="HTML")
    await callback.answer()

# 🔹 /help komandasi
@dp.message(Command("help"))
async def help_handler(message: Message):
    help_text = ("<b>Ob-havo ma'lumotini olish uchun /start ni bosing.\n"
                 "Agar botda xatolik yuz bersa, qayta /start buyrug‘ini yuboring!\n"
                 "Boshqa savollaringiz bo'lsa t.me/uzpenta ga yozing.</b>")
    await message.answer(help_text, parse_mode="HTML")

# 🔹 /vaqt komandasi
@dp.message(Command("vaqt"))
async def send_time(message: Message):
    now = datetime.now(uzbekistan_tz)
    formatted_time = now.strftime("<i><b>Hozirgi vaqt: %H:%M:%S\nHozirgi sana: %d-%m-%Y-yil</b></i>")
    await message.answer(formatted_time, parse_mode="HTML")

# 🔹 Har qanday noaniq xabarga javob
@dp.message()
async def unknown_message(message: Message):
    await message.answer(
        "<b>❌ Iltimos, tugmalardan foydalaning yoki /start ni bosing!</b>",
        parse_mode="HTML"
    )

# 🔹 Botni ishga tushirish
async def main():
    logging.basicConfig(level=logging.INFO)
    print("✅ Bot ishga tushdi! 🟢")

    asyncio.create_task(scheduler())  # 🔹 Fon jarayon ishga tushadi

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
