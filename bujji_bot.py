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
import multiprocessing
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Validate environment variables
required_vars = ["BOT_TOKEN", "SENDER_EMAIL", "APP_PASSWORD", "API_KEY", "RECEIVER_EMAIL"]
missing_vars = [var for var in required_vars if not os.environ.get(var)]
if missing_vars:
    raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Initialize Flask app
app = Flask(__name__)

# Configure caching
cache = Cache(config={'CACHE_TYPE': 'SimpleCache'})
cache.init_app(app)
# Adding this temporary route to verify webhook is receiving messages
@app.route('/webhook_log', methods=['POST'])
def webhook_log():
    print("Received update:", request.json)  # Check Render logs for this output
    return 'OK'
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
@bot.message_handler(content_types=['text'])
def handle_city_request(message):
    print(f"Received text: {message.text}")  # Check logs for this
    user_input = message.text.strip().lower()
    print(f"Processed input: {user_input}")  # Verify city name processing
    
    if not validate_city(user_input):
        return bot.reply_to(message, "⚠️ Invalid city name format. Please try again.")
        
    city = CITY_MAPPING.get(user_input, user_input)
    print(f"Looking up city: {city}")  # Debug which city is being searched
    
    weather_data = get_weather_data(city)
    if not weather_data:
        return bot.reply_to(message, "⚠️ City not found. Please check the spelling.")
        
    formatted_weather = format_weather_response(weather_data, city)
    markup = create_weather_markup(city)
    bot.reply_to(message, formatted_weather, reply_markup=markup)
    
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

@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    try:
        if call.data.startswith('aqi:'):
            city = call.data.split(':')[1]
            aqi_data = get_aqi_data(city)
            if aqi_data:
                bot.send_message(call.message.chat.id, f"💨 Air Quality in {city}:\n{AQI_LEVELS.get(aqi_data, 'Unknown')}")
            else:
                bot.answer_callback_query(call.id, "⚠️ Couldn't fetch AQI data")
                
        elif call.data.startswith('forecast:'):
            city = call.data.split(':')[1]
            forecast_data = get_forecast_data(city)
            if forecast_data:
                bot.send_message(call.message.chat.id, f"⏱️ 24h Forecast for {city}:\n{forecast_data}")
            else:
                bot.answer_callback_query(call.id, "⚠️ Couldn't fetch forecast")
                
    except Exception as e:
        logging.error(f"Callback query error: {str(e)}")
        bot.answer_callback_query(call.id, "⚠️ Error processing request")

@cache.memoize(timeout=3600)  # 1 hour cache for AQI
def get_aqi_data(city):
    """Get AQI data from OpenWeatherMap Air Pollution API"""
    try:
        # First get coordinates for the city
        geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={API_KEY}"
        geo_resp = requests.get(geo_url, timeout=5)
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()
        
        if not geo_data:
            return None
            
        lat, lon = geo_data[0]['lat'], geo_data[0]['lon']
        
        # Get air pollution data
        aqi_url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={API_KEY}"
        aqi_resp = requests.get(aqi_url, timeout=5)
        aqi_resp.raise_for_status()
        aqi_data = aqi_resp.json()
        
        # Map AQI value to your levels (1-5)
        aqi = aqi_data['list'][0]['main']['aqi']
        return min(max(1, aqi), 5)  # Ensure it's between 1-5
        
    except Exception as e:
        logging.error(f"AQI API error for {city}: {str(e)}")
        return None
@cache.memoize(timeout=1800)  # 30 minute cache for forecast
def get_forecast_data(city):
    """Get 24-hour forecast from OpenWeatherMap"""
    try:
        url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={API_KEY}&units=metric&cnt=4"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        forecast = []
        for item in data['list'][:4]:  # Next 24 hours (3-hour intervals)
            time_str = datetime.fromtimestamp(item['dt']).strftime('%H:%M')
            forecast.append(
                f"{time_str}: {item['weather'][0]['description']}, "
                f"{item['main']['temp']}°C"
            )
        
        return "⏱️ Next 24 hours:\n" + "\n".join(forecast)
        
    except Exception as e:
        logging.error(f"Forecast API error for {city}: {str(e)}")
        return None
# Change the webhook route to use a more secure path
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "your-secret-path")

@app.route(f'/{WEBHOOK_SECRET}', methods=["POST"])
@limiter.limit("10 per minute")
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    return 'Bad request', 400
    
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

def process_feedback(message):
    user = message.from_user
    try:
        send_email_feedback(user, message.text)
        bot.reply_to(message, "📩 Thanks! Your feedback has been sent.")
    except Exception as e:
        logging.error(f"Feedback processing failed: {str(e)}")
        bot.reply_to(message, "⚠️ Failed to send feedback. Please try again later.")

def send_email_feedback(user, text):
    msg = EmailMessage()
    msg.set_content(
        f"New feedback from Bujji Bot:\n\n"
        f"User: @{user.username or 'N/A'} ({user.first_name} {user.last_name or ''})\n"
        f"User ID: {user.id}\n\n"
        f"Message:\n{text}"
    )
    msg['Subject'] = f"Bujji Feedback from {user.first_name}"
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(SENDER_EMAIL, APP_PASSWORD)
        smtp.send_message(msg)
    logging.info(f"Feedback email sent for user {user.id}")

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
@app.route('/clear-cache', methods=['POST'])
def clear_cache():
    if request.headers.get('X-Auth') == os.environ.get('CACHE_CLEAR_SECRET'):
        cache.clear()
        return "Cache cleared", 200
    return "Unauthorized", 401
# Flask routes
@app.route("/")
def home():
    return Response("Bujji Weather Bot is running! 😎", mimetype="text/plain")

@app.route('/health')
def health_check():
    return {"status": "healthy", "bot": "online"}, 200

if __name__ == "__main__":
    from waitress import serve
    
    try:
        # Verify token
        bot_info = bot.get_me()
        logging.info(f"Starting bot: @{bot_info.username}")
        
        # Configure webhook - use WEBHOOK_SECRET consistently
        webhook_url = f"{RENDER_EXTERNAL_URL}/{WEBHOOK_SECRET}"
        
        logging.info("Configuring webhook...")
        bot.remove_webhook()
        time.sleep(2)
        bot.set_webhook(url=webhook_url)
        
        # Start server
        port = int(os.environ.get("PORT", 10000))  # Render default is 10000
        logging.info(f"Server starting on port {port}")
        serve(
            app,
            host="0.0.0.0",
            port=port,
            threads=4,
            ident="BujjiWeatherBot"
        )
        
    except Exception as e:
        logging.critical(f"Fatal error: {str(e)}")
        raise
