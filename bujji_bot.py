from flask import Flask, request
import threading
import telebot
from telebot import types
import requests
import random
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import smtplib
from email.mime.text import MIMEText

# 👉 Flask app
app = Flask(__name__)

@app.route('/')
def home():
    return "Bujji Weather Bot is running! ☁️☀️🌧️"

# 🌐 Telegram Bot and API Keys
BOT_TOKEN = "7407002704:AAEak_ultW_1f-uAApwjlUwn-10L6J5dSoo"
API_KEY = "cfe48a7245126131a4ac309b754d03fa"
bot = telebot.TeleBot(BOT_TOKEN)

# 📍 Local area to city mappings
local_to_city = {
    "duvvada": "Visakhapatnam", "gajuwaka": "Visakhapatnam", "anakapalli": "Visakhapatnam",
    "mvp colony": "Visakhapatnam", "madhurawada": "Visakhapatnam", "rajahmundry": "Rajahmundry",
    "kakinada": "Kakinada", "vizianagaram": "Vizianagaram", "tirupati": "Tirupati",
    "guntur": "Guntur", "vijayawada": "Vijayawada", "tenali": "Guntur", "ongole": "Ongole",
    "nellore": "Nellore", "sriharikota": "Nellore", "srikakulam": "Srikakulam", "eluru": "Eluru",
    "machilipatnam": "Machilipatnam", "tadepalligudem": "Tadepalligudem", "narasaraopet": "Guntur",
    "kadapa": "Kadapa", "ananthapur": "Anantapur", "chittoor": "Chittoor",
    "madhapur": "Hyderabad", "gachibowli": "Hyderabad", "ameerpet": "Hyderabad",
    "kukatpally": "Hyderabad", "uppal": "Hyderabad", "secunderabad": "Hyderabad",
    "lb nagar": "Hyderabad", "bhel": "Hyderabad", "warangal": "Warangal",
    "karimnagar": "Karimnagar", "khammam": "Khammam", "nizamabad": "Nizamabad",
    "siddipet": "Siddipet", "nalgonda": "Nalgonda", "zaheerabad": "Zaheerabad",
    "mahabubnagar": "Mahbubnagar"
}

# 😂 Funny suggestions
funny_suggestions = [
    "Don't forget your umbrella ☔", "Sunscreen is your bestie today 😎",
    "Perfect weather for a nap 😴", "Maybe cancel those beach plans 🌊",
    "Time for chai and pakodi? ☕🍟", "Get cozy, it's chilly out! 🧣",
    "Feels like Bujji weather 💖"
]

# 📧 Send feedback via email
def send_email_feedback(user, message):
    sender_email = "vinaymalapareddy@gmail.com"
    app_password = "pgfnuqhukwdnxgtw"
    receiver_email = "vinaymalapareddy@gmail.com"
    subject = f"Bujji Bot Feedback from {user.first_name or user.username}"
    body = f"User @{user.username} ({user.id}) said:\n\n{message}"

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = receiver_email

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.send_message(msg)
        server.quit()
        print("✅ Feedback email sent.")
    except Exception as e:
        print(f"❌ Failed to send feedback email: {e}")

# 🌡️ Funny tip generator
def get_funny_tip(temp_c, condition):
    if temp_c > 35:
        return "🥵 It's boiling! Stay hydrated and wear sunscreen! ☀️"
    elif temp_c > 28:
        return "😎 Warm and sunny – perfect for shades and chilled drinks."
    elif temp_c > 20:
        return "😊 Nice weather! Go for a walk or chill outside."
    elif temp_c > 10:
        return "🧥 It's getting chilly. Wear a jacket, bujji!"
    else:
        return "🥶 Brrr! Bundle up like a snowman!"

# 🌍 Get weather by city
def get_weather(city):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
    response = requests.get(url)
    data = response.json()
    if response.status_code != 200 or data.get('cod') != 200:
        return None

    temp = data['main']['temp']
    condition = data['weather'][0]['description']
    humidity = data['main']['humidity']
    tip = get_funny_tip(temp, condition)

    return (
        f"📍 Weather in {city.title()}:\n"
        f"🌡️ Temp: {temp}°C\n"
        f"☁️ Condition: {condition}\n"
        f"💧 Humidity: {humidity}%\n"
        f"{tip}"
    )

# 📍 Weather by lat/lon
def get_weather_by_location(lat, lon):
    url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
    response = requests.get(url)
    data = response.json()
    if response.status_code != 200 or data.get('cod') != 200:
        return None

    city = data['name']
    temp = data['main']['temp']
    condition = data['weather'][0]['description']
    humidity = data['main']['humidity']
    tip = get_funny_tip(temp, condition)

    return (
        f"📍 Weather in {city}:\n"
        f"🌡️ Temp: {temp}°C\n"
        f"☁️ Condition: {condition}\n"
        f"💧 Humidity: {humidity}%\n"
        f"{tip}"
    )

# 🌫️ Get AQI
def get_aqi(city):
    geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={API_KEY}"
    geo_data = requests.get(geo_url).json()
    if not geo_data:
        return "Couldn't find location for AQI."

    lat = geo_data[0]['lat']
    lon = geo_data[0]['lon']
    aqi_url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={API_KEY}"
    aqi_data = requests.get(aqi_url).json()
    if not aqi_data or 'list' not in aqi_data:
        return "Couldn't fetch AQI data."

    aqi = aqi_data['list'][0]['main']['aqi']
    levels = {1: "😃 Good", 2: "🙂 Fair", 3: "😐 Moderate", 4: "😷 Poor", 5: "☠️ Very Poor"}
    return f"🌬️ AQI in {city.title()}: {aqi} - {levels.get(aqi, 'Unknown')} 💨"

# 📅 Forecast (next 24 hrs)
def get_forecast(city):
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={API_KEY}&units=metric"
    data = requests.get(url).json()
    if data.get('cod') != "200":
        return "Couldn't fetch forecast data."

    forecast_list = data['list'][:8]
    lines = [f"📅 Forecast for {city.title()} (next 24hrs):\n"]
    for item in forecast_list:
        time = item['dt_txt'].split(" ")[1][:5]
        temp = item['main']['temp']
        cond = item['weather'][0]['description']
        lines.append(f"🕒 {time} – 🌡️ {temp}°C – {cond}")
    return "\n".join(lines)

# 🤖 Handlers
@bot.message_handler(commands=['start'])
def start(message):
    name = message.from_user.first_name
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("📍 Send My Location", request_location=True))
    bot.send_message(message.chat.id, f"Hi {name}! 🌤️ Send a city name or share your location for weather updates.", reply_markup=markup)

@bot.message_handler(content_types=['text'])
def city_weather(message):
    user_input = message.text.lower().strip()
    actual_city = local_to_city.get(user_input, user_input)
    if actual_city != user_input:
        bot.send_message(message.chat.id, f"📍 '{user_input}' not found. Showing weather for: {actual_city.title()} 🌐")
    weather = get_weather(actual_city)
    if weather:
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("🔍 Get AQI", callback_data=f"aqi:{actual_city}"),
            InlineKeyboardButton("⏳ 24hrs Forecast", callback_data=f"forecast:{actual_city}")
        )
        bot.send_message(message.chat.id, weather, reply_markup=markup)
    else:
        bot.send_message(message.chat.id, f"Sorry Bujji! I couldn’t find '{user_input}' 😔\nTry sending your location 📍")

@bot.message_handler(content_types=['location'])
def location_weather(message):
    lat, lon = message.location.latitude, message.location.longitude
    weather = get_weather_by_location(lat, lon)
    if weather:
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("🔍 Get AQI", callback_data=f"aqi_loc:{lat},{lon}"),
            InlineKeyboardButton("⏳ 24hrs Forecast", callback_data=f"forecast_loc:{lat},{lon}")
        )
        bot.send_message(message.chat.id, weather, reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "Sorry Bujji! I couldn’t fetch weather info from your location.")

@bot.message_handler(commands=['feedback'])
def feedback_handler(message):
    bot.send_message(message.chat.id, "📝 Please type your feedback and send it.")
    bot.register_next_step_handler(message, process_feedback)

def process_feedback(message):
    send_email_feedback(message.from_user, message.text)
    bot.send_message(message.chat.id, "✅ Thanks Bujji! Feedback sent to my creator 🚀")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data.startswith("aqi:"):
        city = call.data.split(":")[1]
        bot.answer_callback_query(call.id, "Fetching AQI...")
        bot.send_message(call.message.chat.id, get_aqi(city))
    elif call.data.startswith("forecast:"):
        city = call.data.split(":")[1]
        bot.answer_callback_query(call.id, "Fetching forecast...")
        bot.send_message(call.message.chat.id, get_forecast(city))
    elif call.data.startswith("forecast_loc:"):
        lat, lon = map(float, call.data.split(":")[1].split(","))
        url = f"http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
        data = requests.get(url).json()
        if data.get('cod') == "200":
            lines = ["📅 Forecast for your location (next 24hrs):\n"]
            for item in data['list'][:8]:
                time = item['dt_txt'].split(" ")[1][:5]
                temp = item['main']['temp']
                cond = item['weather'][0]['description']
                lines.append(f"🕒 {time} – 🌡️ {temp}°C – {cond}")
            bot.send_message(call.message.chat.id, "\n".join(lines))
        else:
            bot.send_message(call.message.chat.id, "Couldn't fetch forecast data.")

# 🌐 Webhook setup for Render
WEBHOOK_URL = "https://bujji-weather.onrender.com/webhook"

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        update = telebot.types.Update.de_json(request.data.decode("utf-8"))
        bot.process_new_updates([update])
        return 'OK', 200
    else:
        return 'Invalid request', 403

# 🚀 Main entry point
if __name__ == "__main__":
    print("🤖 Setting webhook and running Bujji Weather Bot...")
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    app.run(host='0.0.0.0', port=10000)
