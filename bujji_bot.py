from flask import Flask
import threading
import telebot
from telebot import types
import requests
import random
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# 👇 Create Flask app
app = Flask(__name__)

# 👇 Define a simple route to show the bot is running
@app.route('/')
def home():
    return "Bujji Weather Bot is running! ☁️☀️🌧️"

# 👇 Function to run the Flask server on port 10000 (Render needs this)
def run_flask():
    app.run(host='0.0.0.0', port=10000)

# 👇 Start the Flask server in a new thread (non-blocking)
threading.Thread(target=run_flask).start()

BOT_TOKEN = "7407002704:AAEak_ultW_1f-uAApwjlUwn-10L6J5dSoo"
API_KEY = "cfe48a7245126131a4ac309b754d03fa"

bot = telebot.TeleBot(BOT_TOKEN)

# Local area mappings
local_to_city = {
    # Andhra Pradesh
    "duvvada": "Visakhapatnam",
    "gajuwaka": "Visakhapatnam",
    "anakapalli": "Visakhapatnam",
    "mvp colony": "Visakhapatnam",
    "madhurawada": "Visakhapatnam",
    "rajahmundry": "Rajahmundry",
    "kakinada": "Kakinada",
    "vizianagaram": "Vizianagaram",
    "tirupati": "Tirupati",
    "guntur": "Guntur",
    "vijayawada": "Vijayawada",
    "tenali": "Guntur",
    "ongole": "Ongole",
    "nellore": "Nellore",
    "sriharikota": "Nellore",
    "srikakulam": "Srikakulam",
    "eluru": "Eluru",
    "machilipatnam": "Machilipatnam",
    "tadepalligudem": "Tadepalligudem",
    "narasaraopet": "Guntur",
    "kadapa": "Kadapa",
    "ananthapur": "Anantapur",
    "chittoor": "Chittoor",

    # Telangana
    "madhapur": "Hyderabad",
    "gachibowli": "Hyderabad",
    "ameerpet": "Hyderabad",
    "kukatpally": "Hyderabad",
    "uppal": "Hyderabad",
    "secunderabad": "Hyderabad",
    "lb nagar": "Hyderabad",
    "bhel": "Hyderabad",
    "warangal": "Warangal",
    "karimnagar": "Karimnagar",
    "khammam": "Khammam",
    "nizamabad": "Nizamabad",
    "siddipet": "Siddipet",
    "nalgonda": "Nalgonda",
    "zaheerabad": "Zaheerabad",
    "mahabubnagar": "Mahbubnagar"
}

funny_suggestions = [
    "Don't forget your umbrella ☔",
    "Sunscreen is your bestie today 😎",
    "Perfect weather for a nap 😴",
    "Maybe cancel those beach plans 🌊",
    "Time for chai and pakodi? ☕🍟",
    "Get cozy, it's chilly out! 🧣",
    "Feels like Bujji weather 💖"
]

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

def get_aqi(city):
    url_geo = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={API_KEY}"
    geo_data = requests.get(url_geo).json()
    if not geo_data:
        return "Couldn't find location for AQI."

    lat = geo_data[0]['lat']
    lon = geo_data[0]['lon']

    url_aqi = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={API_KEY}"
    aqi_data = requests.get(url_aqi).json()
    if not aqi_data or 'list' not in aqi_data:
        return "Couldn't fetch AQI data."

    aqi = aqi_data['list'][0]['main']['aqi']
    aqi_text = {
        1: "😃 Good", 2: "🙂 Fair", 3: "😐 Moderate", 4: "😷 Poor", 5: "☠️ Very Poor"
    }

    return f"🌬️ AQI in {city.title()}: {aqi} - {aqi_text.get(aqi, 'Unknown')} 💨"

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

@bot.message_handler(commands=['start'])
def start(message):
    name = message.from_user.first_name
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button = types.KeyboardButton("📍 Send My Location", request_location=True)
    markup.add(button)
    bot.send_message(message.chat.id, f"Hi {name}! 🌤️ Send me a city name or your location to get the weather update.", reply_markup=markup)

@bot.message_handler(content_types=['text'])
def city_weather(message):
    user_input = message.text.lower().strip()
    actual_city = local_to_city.get(user_input)
    if actual_city:
        bot.send_message(message.chat.id, f"📍 '{user_input}' not found. Showing weather for nearby city: {actual_city.title()} 🌐")
    else:
        actual_city = user_input

    weather_info = get_weather(actual_city)
    if weather_info:
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("🔍 Get AQI", callback_data=f"aqi:{actual_city}"),
            InlineKeyboardButton("⏳ Next 24hrs Forecast", callback_data=f"forecast:{actual_city}")
        )
        bot.send_message(message.chat.id, weather_info, reply_markup=markup)
    else:
        bot.send_message(message.chat.id, f"Sorry Bujji! I couldn’t find '{user_input}' 😔\nTry sending your location 📍 for accurate weather!")

@bot.message_handler(content_types=['location'])
def location_weather(message):
    lat = message.location.latitude
    lon = message.location.longitude
    weather_info = get_weather_by_location(lat, lon)
    if weather_info:
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("🔍 Get AQI", callback_data=f"aqi_loc:{lat},{lon}"),
            InlineKeyboardButton("⏳ Next 24hrs Forecast", callback_data=f"forecast_loc:{lat},{lon}")
        )
        bot.send_message(message.chat.id, weather_info, reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "Sorry Bujji! I couldn’t fetch weather info from your location.")

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

    elif call.data.startswith("aqi_loc:"):
        lat, lon = map(float, call.data.split(":")[1].split(","))
        url_aqi = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={API_KEY}"
        aqi_data = requests.get(url_aqi).json()
        if aqi_data and 'list' in aqi_data:
            aqi = aqi_data['list'][0]['main']['aqi']
            aqi_text = {1: "😃 Good", 2: "🙂 Fair", 3: "😐 Moderate", 4: "😷 Poor", 5: "☠️ Very Poor"}
            bot.send_message(call.message.chat.id, f"🌬️ AQI at your location: {aqi} - {aqi_text.get(aqi)} 💨")
        else:
            bot.send_message(call.message.chat.id, "Couldn't fetch AQI data.")

    elif call.data.startswith("forecast_loc:"):
        lat, lon = map(float, call.data.split(":")[1].split(","))
        url = f"http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
        data = requests.get(url).json()
        if data.get('cod') == "200":
            forecast_list = data['list'][:8]
            lines = ["📅 Forecast for your location (next 24hrs):\n"]
            for item in forecast_list:
                time = item['dt_txt'].split(" ")[1][:5]
                temp = item['main']['temp']
                cond = item['weather'][0]['description']
                lines.append(f"🕒 {time} – 🌡️ {temp}°C – {cond}")
            bot.send_message(call.message.chat.id, "\n".join(lines))
        else:
            bot.send_message(call.message.chat.id, "Couldn't fetch forecast data.")

WEBHOOK_URL = "https://your-render-or-railway-url.com/webhook"

# Webhook route to receive updates from Telegram
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    else:
        return 'Invalid request', 403

# Set webhook and run
if __name__ == "__main__":
    print("🤖 Setting webhook and running Bujji Weather Bot...")

    # Remove previous webhook (optional)
    bot.remove_webhook()
    
    # Set new webhook to your hosted URL + /webhook endpoint
    bot.set_webhook(url=WEBHOOK_URL)

    # Run Flask app (on port 10000 for Render compatibility)
    app.run(host="0.0.0.0", port=10000)

