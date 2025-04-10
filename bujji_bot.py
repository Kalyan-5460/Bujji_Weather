from flask import Flask, request, Response
import telebot
from telebot import types, util
import requests
from email.message import EmailMessage
import os
import re
import logging
import time
from datetime import datetime
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import smtplib

# Initialize Flask app
app = Flask(__name__)

# Configure caching
cache = Cache(config={'CACHE_TYPE': 'SimpleCache'})
cache.init_app(app)

# Configure rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Load environment variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
APP_PASSWORD = os.environ.get("APP_PASSWORD")
API_KEY = os.environ.get("API_KEY")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://bujji-weather.onrender.com")

# Initialize Telegram bot
bot = telebot.TeleBot(BOT_TOKEN)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Constants
AQI_LEVELS = {
    1: "😃 Good",
    2: "🙂 Fair", 
    3: "😐 Moderate",
    4: "🤧 Poor",
    5: "☠️ Very Poor"
}

CITY_MAPPING = {
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


# Utility functions
def validate_city(city):
    """Validate city name format"""
    return bool(re.match(r'^[a-zA-Z\s\-]+$', city))

def get_funny_tip(temp_c, condition):
    """Generate humorous weather tips"""
    if temp_c > 35:
        return "🥵 It's boiling! Stay hydrated and wear sunscreen! ☀️"
    elif temp_c > 28:
        return "😎 Warm and sunny - perfect for shades and chilled drinks."
    elif temp_c > 20:
        return "😊 Nice weather! Go for a walk or chill outside."
    elif temp_c > 10:
        return "🤕 It's getting chilly. Wear a jacket, bujji!"
    else:
        return "🥶 Brrr! Bundle up like a snowman!"

# Weather data functions with caching
@cache.memoize(timeout=300)  # 5 minute cache
def get_weather_data(city):
    """Fetch weather data from API with caching"""
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Weather API error for {city}: {str(e)}")
        return None

def format_weather_response(data, city):
    """Format weather data into user-friendly message"""
    if not data:
        return None
        
    main = data['main']
    weather = data['weather'][0]
    wind = data['wind']
    sys = data['sys']
    
    return (
        f"📍 Weather in {city.title()}:\n"
        f"🌡️ Temp: {main['temp']}°C\n"
        f"☁️ Condition: {weather['description']}\n"
        f"💧 Humidity: {main['humidity']}%\n"
        f"🌬️ Wind: {wind['speed']} m/s\n"
        f"🌅 Sunrise: {datetime.fromtimestamp(sys['sunrise']).strftime('%H:%M')}\n"
        f"🌇 Sunset: {datetime.fromtimestamp(sys['sunset']).strftime('%H:%M')}\n"
        f"{get_funny_tip(main['temp'], weather['description'])}"
    )

# Bot command handlers
@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Handle /start command"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("📍 Send My Location", request_location=True))
    bot.reply_to(message, 
                f"Hi {message.from_user.first_name}! 🌤️ Send a city name or share your location for weather updates.",
                reply_markup=markup)

@bot.message_handler(commands=['help'])
def send_help(message):
    """Handle /help command"""
    help_text = (
        "Hi Bujji! Here's what I can do:\n\n"
        "📍 Share your location for weather\n"
        "🏙️ Send a city name\n"
        "💨 Get AQI info\n"
        "⏱️ Get 24-hour forecast\n"
        "📝 Send feedback using /feedback"
    )
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['about'])
def send_about(message):
    """Handle /about command"""
    about_text = (
        "🌦️ *Bujji Weather Bot* - Your personal weather buddy!\n\n"
        "🔹 Real-time weather updates\n"
        "🔹 Air Quality Index (AQI)\n" 
        "🔹 24-hour forecasts\n"
        "🔹 Location-based weather\n"
        "🔹 Fun weather tips\n\n"
        "✨ Created with ❤️ by MKV Vinay\n"
        "🌐 Hosted on Render"
    )
    bot.reply_to(message, about_text, parse_mode="Markdown")

@bot.message_handler(commands=['feedback'])
def request_feedback(message):
    """Handle /feedback command"""
    msg = bot.reply_to(message, "📝 Please type your feedback below:")
    bot.register_next_step_handler(msg, process_feedback)

# Weather data handlers
@bot.message_handler(content_types=['location'])
def handle_location(message):
    """Handle location messages"""
    loc = message.location
    weather_data = get_weather_by_coords(loc.latitude, loc.longitude)
    if weather_data:
        bot.reply_to(message, weather_data)
    else:
        bot.reply_to(message, "⚠️ Couldn't fetch weather for your location.")

@bot.message_handler(content_types=['text'])
@limiter.limit("5 per minute", key_func=lambda m: m.from_user.id)
def handle_city_request(message):
    """Handle city name requests"""
    user_input = message.text.strip()
    
    if not validate_city(user_input):
        return bot.reply_to(message, "⚠️ Invalid city name format. Please try again.")
        
    city = CITY_MAPPING.get(user_input.lower(), user_input)
    weather_data = get_weather_data(city)
    
    if not weather_data:
        return bot.reply_to(message, "⚠️ City not found. Please check the spelling.")
        
    formatted_weather = format_weather_response(weather_data, city)
    markup = create_weather_markup(city)
    bot.reply_to(message, formatted_weather, reply_markup=markup)

# Helper functions
def create_weather_markup(city):
    """Create inline keyboard for weather options"""
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("💨 AQI", callback_data=f"aqi:{city}"),
        InlineKeyboardButton("⏱️ Forecast", callback_data=f"forecast:{city}")
    )
    return markup

def get_weather_by_coords(lat, lon):
    """Get weather by coordinates"""
    url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return format_weather_response(data, data['name'])
    except requests.exceptions.RequestException as e:
        logging.error(f"Location weather error: {str(e)}")
        return None

# Flask routes
@app.route("/")
def home():
    return Response("Bujji Weather Bot is running! 😎", mimetype="text/plain")

@app.route(f'/{BOT_TOKEN}', methods=["POST"])
@limiter.limit("10 per minute")
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    bot.process_new_updates([update])
    return "ok", 200

@app.route('/health')
def health_check():
    return {"status": "healthy"}, 200

if __name__ == "__main__":
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=f"{RENDER_EXTERNAL_URL}/{BOT_TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
