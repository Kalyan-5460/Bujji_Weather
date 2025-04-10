from flask import Flask, request, Response
import telebot
from telebot import types
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
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Initialize Flask app
app = Flask(__name__)

# Validate environment variables
required_vars = ["BOT_TOKEN", "API_KEY", "SENDER_EMAIL", "APP_PASSWORD", "RECEIVER_EMAIL"]
missing_vars = [var for var in required_vars if not os.environ.get(var)]
if missing_vars:
    raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")

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
API_KEY = os.environ.get("API_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
APP_PASSWORD = os.environ.get("APP_PASSWORD")
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
    "duvvada": "Visakhapatnam", "gajuwaka": "Visakhapatnam",
    "visakapatnam": "Visakhapatnam", "vizag": "Visakhapatnam",
    "hyderabad": "Hyderabad", "banglore": "Bengaluru",
}

# Utility functions
def validate_city(city):
    return bool(re.match(r'^[a-zA-Z\s\-]+$', city))

def get_funny_tip(temp_c):
    if temp_c > 35: return "🥵 It's boiling! Stay hydrated!"
    elif temp_c > 28: return "😎 Perfect for shades and chilled drinks"
    elif temp_c > 20: return "😊 Nice weather! Enjoy outside"
    elif temp_c > 10: return "🧥 It's chilly. Wear a jacket!"
    else: return "🥶 Bundle up like a snowman!"

# Weather API functions
@cache.memoize(timeout=300)
def get_weather_data(city):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"Weather API error: {str(e)}")
        return None

@cache.memoize(timeout=3600)
def get_aqi_data(lat, lon):
    url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={API_KEY}"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()['list'][0]['main']['aqi']
    except Exception:
        return None

@cache.memoize(timeout=1800)
def get_forecast_data(lat, lon):
    url = f"http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_KEY}&units=metric&cnt=8"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None

# Message formatting
def format_weather(data, original_city=None):
    if not data: return None
    
    city = data['name']
    main = data['main']
    weather = data['weather'][0]
    wind = data['wind']
    sys = data['sys']
    
    response = []
    
    if original_city and original_city.lower() != city.lower():
        response.append(f"📍 '{original_city}' not found. Showing weather for: {city}\n\n")
    
    response.extend([
        f"📍 Weather in {city}:\n",
        f"🌡️ Temp: {main['temp']}°C\n",
        f"☁️ Condition: {weather['description'].title()}\n",
        f"💧 Humidity: {main['humidity']}%\n",
        f"🌬️ Wind: {wind['speed']} m/s\n",
        f"🌅 Sunrise: {datetime.fromtimestamp(sys['sunrise']).strftime('%H:%M')}\n",
        f"🌇 Sunset: {datetime.fromtimestamp(sys['sunset']).strftime('%H:%M')}\n",
        f"{get_funny_tip(main['temp'])}\n"
    ])
    
    return "".join(response)

def format_forecast(forecast_data, city):
    forecast = [f"📅 24h Forecast for {city}:\n\n"]
    for item in forecast_data['list']:
        time_str = datetime.fromtimestamp(item['dt']).strftime('🕒 %H:%M')
        forecast.append(
            f"{time_str} – 🌡️{item['main']['temp']}°C – {item['weather'][0]['description'].title()}\n"
        )
    return "".join(forecast)

# Email feedback
def send_feedback_email(user, message_text):
    try:
        msg = EmailMessage()
        msg.set_content(
            f"New feedback from Bujji Bot:\n\n"
            f"User: @{user.username or 'N/A'} ({user.first_name} {user.last_name or ''})\n"
            f"User ID: {user.id}\n\n"
            f"Message:\n{message_text}"
        )
        msg['Subject'] = f"Bujji Feedback from {user.first_name}"
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.send_message(msg)
        
        logging.info(f"Feedback email sent for user {user.id}")
        return True
    except Exception as e:
        logging.error(f"Failed to send feedback email: {str(e)}")
        return False

# Bot handlers
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_msg = (
        f"Hi {message.from_user.first_name}! 🌤️ I'm Bujji Weather Bot\n\n"
        "Just send me:\n"
        "📍 A city name (e.g. 'Hyderabad')\n"
        "📌 Your location (tap the 📎 icon)\n"
        "📝 /feedback to send suggestions\n"
        "ℹ️ /about to learn more"
    )
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("📍 Share My Location", request_location=True))
    bot.reply_to(message, welcome_msg, reply_markup=markup)

@bot.message_handler(commands=['about'])
def send_about(message):
    about_text = (
        "🌦️ *Bujji Weather Bot*\n\n"
        "Your personal weather assistant with:\n"
        "🔹 Real-time weather updates\n"
        "🔹 Air quality reports\n"
        "🔹 24-hour forecasts\n"
        "🔹 Fun weather tips\n\n"
        "✨ Created with ❤️ by MKV Vinay\n"
        "🌐 Hosted on Render"
    )
    bot.reply_to(message, about_text, parse_mode="Markdown")

@bot.message_handler(commands=['feedback'])
def request_feedback(message):
    msg = bot.reply_to(message, "📝 Please type your feedback or suggestions:")
    bot.register_next_step_handler(msg, process_feedback)

def process_feedback(message):
    try:
        if send_feedback_email(message.from_user, message.text):
            bot.reply_to(message, "📩 Thanks! Your feedback has been sent.")
        else:
            bot.reply_to(message, "⚠️ Failed to send feedback. Please try again later.")
    except Exception as e:
        logging.error(f"Feedback processing error: {str(e)}")
        bot.reply_to(message, "⚠️ An error occurred. Please try again.")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    user_input = message.text.strip()
    
    if not validate_city(user_input):
        return bot.reply_to(message, "⚠️ Please enter a valid city name")
        
    mapped_city = CITY_MAPPING.get(user_input.lower(), user_input)
    weather_data = get_weather_data(mapped_city)
    
    if not weather_data:
        return bot.reply_to(message, f"😔 Couldn't find weather for '{user_input}'\nTry sending your location instead 📍")
    
    # Create inline keyboard
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("💨 AQI", callback_data=f"aqi:{mapped_city}"),
        InlineKeyboardButton("⏱️ Forecast", callback_data=f"forecast:{mapped_city}")
    )
    
    # Send weather report with buttons
    weather_msg = format_weather(weather_data, user_input)
    bot.send_message(message.chat.id, weather_msg, reply_markup=markup)

@bot.message_handler(content_types=['location'])
def handle_location(message):
    loc = message.location
    weather_data = get_weather_data(f"{loc.latitude},{loc.longitude}")
    
    if not weather_data:
        return bot.reply_to(message, "⚠️ Couldn't fetch weather for this location")
    
    # Create inline keyboard
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("💨 AQI", callback_data=f"aqi_loc:{loc.latitude},{loc.longitude}"),
        InlineKeyboardButton("⏱️ Forecast", callback_data=f"forecast_loc:{loc.latitude},{loc.longitude}")
    )
    
    # Send weather report with buttons
    bot.send_message(message.chat.id, format_weather(weather_data), reply_markup=markup)

# Callback handlers for inline buttons
@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    try:
        if call.data.startswith('aqi:'):
            city = call.data.split(':')[1]
            weather_data = get_weather_data(city)
            if weather_data:
                aqi = get_aqi_data(weather_data['coord']['lat'], weather_data['coord']['lon'])
                if aqi:
                    bot.send_message(
                        call.message.chat.id,
                        f"🌬️ Air Quality in {city}: {aqi} - {AQI_LEVELS.get(aqi, 'Unknown')} 💨"
                    )
                else:
                    bot.answer_callback_query(call.id, "⚠️ Couldn't fetch AQI data")
            else:
                bot.answer_callback_query(call.id, "⚠️ Couldn't fetch weather data")
                
        elif call.data.startswith('forecast:'):
            city = call.data.split(':')[1]
            weather_data = get_weather_data(city)
            if weather_data:
                forecast = get_forecast_data(weather_data['coord']['lat'], weather_data['coord']['lon'])
                if forecast:
                    bot.send_message(
                        call.message.chat.id,
                        format_forecast(forecast, city)
                    )
                else:
                    bot.answer_callback_query(call.id, "⚠️ Couldn't fetch forecast")
            else:
                bot.answer_callback_query(call.id, "⚠️ Couldn't fetch weather data")
                
        elif call.data.startswith('aqi_loc:'):
            lat, lon = call.data.split(':')[1].split(',')
            aqi = get_aqi_data(float(lat), float(lon))
            if aqi:
                bot.send_message(
                    call.message.chat.id,
                    f"🌬️ Air Quality: {aqi} - {AQI_LEVELS.get(aqi, 'Unknown')} 💨"
                )
            else:
                bot.answer_callback_query(call.id, "⚠️ Couldn't fetch AQI data")
                
        elif call.data.startswith('forecast_loc:'):
            lat, lon = call.data.split(':')[1].split(',')
            forecast = get_forecast_data(float(lat), float(lon))
            if forecast:
                weather_data = get_weather_data(f"{lat},{lon}")
                city = weather_data['name'] if weather_data else "your location"
                bot.send_message(
                    call.message.chat.id,
                    format_forecast(forecast, city)
                )
            else:
                bot.answer_callback_query(call.id, "⚠️ Couldn't fetch forecast")
                
    except Exception as e:
        logging.error(f"Callback query error: {str(e)}")
        bot.answer_callback_query(call.id, "⚠️ Error processing request")

# Flask routes
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "default-secret-123")

@app.route(f'/{WEBHOOK_SECRET}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
        bot.process_new_updates([update])
        return '', 200
    return 'Bad request', 400

@app.route('/')
def home():
    return "Bujji Weather Bot is running!"

@app.route('/health')
def health_check():
    return {"status": "healthy", "bot": "online"}, 200

# Start server
if __name__ == "__main__":
    # Verify connection
    try:
        bot_info = bot.get_me()
        logging.info(f"Starting bot: @{bot_info.username}")
    except Exception as e:
        logging.critical(f"Failed to connect to Telegram: {str(e)}")
        raise

    # Configure webhook
    port = int(os.environ.get("PORT", 10000))
    bot.remove_webhook()
    time.sleep(1)
    webhook_url = f"{RENDER_EXTERNAL_URL}/{WEBHOOK_SECRET}"
    bot.set_webhook(url=webhook_url)
    logging.info(f"Webhook configured: {webhook_url}")
    
    # Start server
    from waitress import serve
    logging.info(f"Starting server on port {port}")
    serve(app, host="0.0.0.0", port=port)
