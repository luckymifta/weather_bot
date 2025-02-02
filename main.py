import datetime
import pytz
import requests
import os
from typing import Dict, cast
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv

# Load environment variables from.env file
load_dotenv()

# Fetch sensitive data (tokens, keys) from environment variables
TELEGRAM_BOT_TOKEN = cast(str, os.getenv("TELEGRAM_BOT_TOKEN"))
OPENWEATHER_API_KEY = cast(str, os.getenv("OPENWEATHER_API_KEY"))

# Validate environment variables
if not TELEGRAM_BOT_TOKEN or not OPENWEATHER_API_KEY:
    raise ValueError("TELEGRAM_BOT_TOKEN and OPENWEATHER_API_KEY must be set as environment variables.")

# List of cities for weather updates
CITIES = [
    {"name": "Dili", "lat": "-8.556856", "lon": "125.598753"},
    {"name": "Denpasar", "lat": "-8.650000", "lon": "115.216667"},
    {"name": "Bintaro", "lat": "-6.276806", "lon": "106.718361"},
]

TIME_TO_SEND = "00:00"  # Scheduled time for weather updates in UTC


# Fetch weather data from OpenWeather
def get_forecast(lat: str, lon: str) -> Dict:
    try:
        print(f"Fetching forecast for coordinates: lat={lat}, lon={lon}")
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
        response = requests.get(url)
        print(f"Forecast API response status code: {response.status_code}")
        data = response.json()

        if response.status_code != 200:
            raise Exception(f"Error fetching forecast data: {data.get('message', 'Unknown error')}")

        return data
    except Exception as e:
        print(f"Exception in get_forecast: {e}")
        raise


# Format the weather message
def format_forecast_message(city_name: str, forecast_data: Dict) -> str:
    try:
        forecast_list = forecast_data.get("list", [])
        if not forecast_list:
            return f"Sorry, no hourly forecast data available for {city_name}."

        forecast_date = datetime.date.today()
        hourly_forecast = []

        for entry in forecast_list:
            entry_time = datetime.datetime.fromtimestamp(entry["dt"])
            if entry_time.date() != forecast_date:
                break

            weather_desc = entry["weather"][0]["description"].capitalize()
            formatted_time = entry_time.strftime("%H:%M")
            hourly_forecast.append(f"- {formatted_time} - {weather_desc}")

        hourly_forecast_str = "\n".join(hourly_forecast)
        return (
            f"Weather forecast for {city_name} on {forecast_date}:\n"
            f"Hours:\n{hourly_forecast_str}"
        )
    except Exception as e:
        print(f"Error formatting forecast data for {city_name}: {e}")
        raise


# /start Command Handler
async def start(update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    print(f"Received /start command from Chat ID: {chat_id}")

    # Schedule the daily weather updates
    target_time = datetime.time(
        hour=int(TIME_TO_SEND.split(":")[0]),
        minute=int(TIME_TO_SEND.split(":")[1]),
        tzinfo=pytz.UTC,
    )

    if context.job_queue is not None:
        context.job_queue.run_daily(
            send_daily_weather,
            time=target_time,
            data={"chat_id": chat_id},
            name=str(chat_id),
        )
        print(f"Scheduled daily weather updates at {target_time} UTC for Chat ID: {chat_id}")
    else:
        print("Error: Job queue is not available in the current context.")

    await update.message.reply_text("Weather bot started! You will receive daily updates.")


# /forecast Command Handler
async def forecast(update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    print(f"Received /forecast command from Chat ID: {chat_id}")

    for city in CITIES:
        try:
            forecast_data = get_forecast(city["lat"], city["lon"])
            message = format_forecast_message(city["name"], forecast_data)
            await context.bot.send_message(chat_id=chat_id, text=message)
            print(f"Sent forecast data for {city['name']} to Chat ID: {chat_id}")
        except Exception as e:
            print(f"Error fetching forecast for {city['name']}: {e}")
            await context.bot.send_message(chat_id=chat_id, text=f"Failed to send forecast for {city['name']} — {e}")


# Scheduled Daily Weather Updates
async def send_daily_weather(context: ContextTypes.DEFAULT_TYPE):
    print("Running scheduled weather updates...")
    if context.job is not None and isinstance(context.job.data, dict):
        job_data = context.job.data
        if "chat_id" in job_data:
            chat_id = job_data["chat_id"]

            for city in CITIES:
                try:
                    forecast_data = get_forecast(city["lat"], city["lon"])
                    message = format_forecast_message(city["name"], forecast_data)
                    await context.bot.send_message(chat_id=chat_id, text=message)
                except Exception as e:
                    print(f"Error sending weather update for {city['name']}: {e}")
                    await context.bot.send_message(chat_id=chat_id, text=f"Failed to send forecast for {city['name']} — {e}")


# Main Function
def main():
    print("Starting Weather Bot...")

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("forecast", forecast))

    print("Bot is up and running...")
    application.run_polling()


# Run the Bot
if __name__ == "__main__":
    main()
