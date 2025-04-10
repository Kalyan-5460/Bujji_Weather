from flask import Flask, request
from flask import Response
import threading
import telebot
from telebot import types
import requests
import random
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import smtplib
from email.mime.text import MIMEText
from email.message import EmailMessage
import os
import logging

app = Flask(__name__)

@app.route("/", methods=["GET", "HEAD"])
def home():
    if request.method == "HEAD":
        return "", 200  # respond with headers only
    return "Welcome to Bujji Weather Bot! ☀️🌧️❄️", 200
@app.route('/webhook', methods=["POST"])
def webhook():
    update = request.get_json()
    bot.process_new_updates([telebot.types.Update.de_json(update)])
    return '', 200


# Load environment variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
APP_PASSWORD = os.environ.get("APP_PASSWORD")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL")

bot = telebot.TeleBot(BOT_TOKEN)

# Funny tips generator
def get_funny_tip(temp_c, condition):
    if temp_c > 35:
        return "\ud83e\udd75 It's boiling! Stay hydrated and wear sunscreen! \u2600\ufe0f"
    elif temp_c > 28:
        return "\ud83d\ude0e Warm and sunny \u2013 perfect for shades and chilled drinks."
    elif temp_c > 20:
        return "\ud83d\ude0a Nice weather! Go for a walk or chill outside."
    elif temp_c > 10:
        return "\ud83e\udde5 It's getting chilly. Wear a jacket, bujji!"
    else:
        return "\ud83e\udd76 Brrr! Bundle up like a snowman!"

# AQI levels
aqi_levels = {1: "\ud83d\ude03 Good", 2: "\ud83d\ude42 Fair", 3: "\ud83d\ude10 Moderate", 4: "\ud83e\udd37 Poor", 5: "\u2620\ufe0f Very Poor"}

# City mapping
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

# Weather by city
def get_weather(city):
    API_KEY = os.environ.get("API_KEY")
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
        f"\ud83d\udccd Weather in {city.title()}:\n"
        f"\ud83c\udf21\ufe0f Temp: {temp}\u00b0C\n"
        f"\u2601\ufe0f Condition: {condition}\n"
        f"\ud83d\udca7 Humidity: {humidity}%\n"
        f"{tip}"
    )

# Weather by coordinates
def get_weather_by_location(lat, lon):
    API_KEY = os.environ.get("API_KEY")
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
        f"\ud83d\udccd Weather in {city}:\n"
        f"\ud83c\udf21\ufe0f Temp: {temp}\u00b0C\n"
        f"\u2601\ufe0f Condition: {condition}\n"
        f"\ud83d\udca7 Humidity: {humidity}%\n"
        f"{tip}"
    )

# AQI

def get_aqi(city):
    API_KEY = os.environ.get("API_KEY")
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
    return f"\ud83c\udf2c\ufe0f AQI in {city.title()}: {aqi} - {aqi_levels.get(aqi, 'Unknown')} \ud83d\udca8"

# Forecast
def get_forecast(city):
    API_KEY = os.environ.get("API_KEY")
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={API_KEY}&units=metric"
    data = requests.get(url).json()
    if data.get('cod') != "200":
        return "Couldn't fetch forecast data."

    forecast_list = data['list'][:8]
    lines = [f"\ud83d\udcc5 Forecast for {city.title()} (next 24hrs):\n"]
    for item in forecast_list:
        time = item['dt_txt'].split(" ")[1][:5]
        temp = item['main']['temp']
        cond = item['weather'][0]['description']
        lines.append(f"\ud83d\udd52 {time} – \ud83c\udf21\ufe0f {temp}\u00b0C – {cond}")
    return "\n".join(lines)

# Feedback
@bot.message_handler(commands=['feedback'])
def ask_feedback(message):
    msg = bot.send_message(message.chat.id, "\ud83d\udcdd Please type your feedback below:")
    bot.register_next_step_handler(msg, process_feedback)

def process_feedback(message):
    user = message.from_user
    feedback_message = f"Feedback from @{user.username or user.first_name}:\n\n{message.text}"
    send_email_feedback(user, message.text)
    bot.send_message(message.chat.id, "\ud83d\ude4f Thanks Bujji! Your feedback has been sent successfully.")

def send_email_feedback(user, text):
    subject = f"Bujji Bot Feedback from {user.first_name or user.username}"
    body = f"User @{user.username or 'N/A'} ({user.id}) said:\n\n{text}"

    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(SENDER_EMAIL, APP_PASSWORD)
            smtp.send_message(msg)
        logging.info("Feedback sent from user: %s", user.username)

            
    except Exception as e:
        logging.error("Email sending failed: %s", e)

    
# Location handler
@bot.message_handler(content_types=['location'])
def handle_location(message):
    loc = message.location
    weather = get_weather_by_location(loc.latitude, loc.longitude)
    if weather:
        bot.send_message(message.chat.id, weather)
    else:
        bot.send_message(message.chat.id, "Sorry, couldn't fetch weather for your location.")

# Text handler
@bot.message_handler(content_types=['text'])
def handle_text(message):
    user_input = message.text.lower().strip()
    actual_city = local_to_city.get(user_input, user_input)
    if actual_city != user_input:
        bot.send_message(message.chat.id, f"\ud83d\udccd '{user_input}' not found. Showing weather for: {actual_city.title()} \ud83c\udf10")
    weather = get_weather(actual_city)
    if weather:
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("\ud83d\udd0d Get AQI", callback_data=f"aqi:{actual_city}"),
            InlineKeyboardButton("\u23f3 24hrs Forecast", callback_data=f"forecast:{actual_city}")
        )
        bot.send_message(message.chat.id, weather, reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "City not found. Please check the spelling or try a nearby city.")

# Inline buttons
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data.startswith("aqi:"):
        city = call.data.split(":")[1]
        aqi_info = get_aqi(city)
        bot.send_message(call.message.chat.id, aqi_info)
    elif call.data.startswith("forecast:"):
        city = call.data.split(":")[1]
        forecast = get_forecast(city)
        bot.send_message(call.message.chat.id, forecast)

# Start command
@bot.message_handler(commands=['start'])
def start_cmd(message):
    name = message.from_user.first_name
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("\ud83d\udccd Send My Location", request_location=True))
    bot.send_message(message.chat.id, f"Hi {name}! \ud83c\udf24\ufe0f Send a city name or share your location for weather updates.", reply_markup=markup)
@bot.message_handler(commands=['help'])
def help_cmd(message):
    bot.send_message(message.chat.id, (
        "Hi Bujji! Here's what I can do:\n\n"
        "📍 Share your location for weather\n"
        "🏙️ Send a city name\n"
        "💨 Get AQI info\n"
        "⏱️ Get 24-hour forecast\n"
        "📝 Send feedback using /feedback"
    ))

@app.route('/' + BOT_TOKEN, methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    bot.process_new_updates([update])
    return "ok", 200
@app.route('/favicon.ico')
def favicon():
    return '', 204
@app.errorhandler(Exception)
def handle_error(e):
    logging.error("Unhandled exception: %s", e)
    return "Something went wrong.", 500
@bot.message_handler(commands=['about'])
def about_cmd(message):
    bot.send_message(message.chat.id, (
        "🔹 Hi,This is Bujji\n"
        "🌦️ *Bujji Weather Bot* – Your personal weather buddy!\n\n"
        "🔹 Get real-time weather updates 🌍\n"
        "🔹 Know the AQI (Air Quality Index) 💨\n"
        "🔹 See 24-hour forecasts ⏱️\n"
        "🔹 Share your location or type a city name 📍\n"
        "🔹 Fun tips based on weather 😄\n"
        "🔹 Give feedback with /feedback 📝\n\n"
        "✨ Created with ❤️ by Malapareddy Kalyan Venkat Vinay. Always improving for you!\n"
        "🌐 Hosted 24/7 on Render\n\n"
        "_Type /help to see what I can do!_"
    ), parse_mode="Markdown")
    
bot.remove_webhook()
bot.set_webhook(url=f"https://bujji-weather.onrender.com/{BOT_TOKEN}")
def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    import time

    # Set your public URL where Flask app is hosted (e.g., Render)
    WEBHOOK_URL = f"https://bujji-weather.onrender.com/{BOT_TOKEN}"  # Change this to your actual domain + token

    # Remove any existing webhook
    bot.remove_webhook()
    time.sleep(1)  # small delay to ensure removal

    # Set webhook to the correct public URL
    bot.set_webhook(url=WEBHOOK_URL)

    # Run the Flask app
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))



