import datetime
import pytz
import requests
from typing import Dict, Any
from telegram.ext import Application, CommandHandler, ContextTypes

TELEGRAM_BOT_TOKEN = "8002908706:AAGbbTTrpG9iWM9H7DxSQG7a52qIlQfY5Dw"
OPENWEATHER_API_KEY = "2c2754389b3b214fe1818b6a1487678e"

CITIES = [
    {"name": "Dili", "lat": "-8.556856", "lon": "125.598753"},
    {"name": "Denpasar", "lat": "-8.650000", "lon": "115.216667"},
    {"name": "Bintaro", "lat": "-6.276806", "lon": "106.718361"},
]

TIME_TO_SEND = "00:00"  # Time in UTC


# Fetch hourly weather forecast from OpenWeather
def get_forecast(lat: str, lon: str) -> Dict:
    try:
        print(f"Fetching forecast for coordinates: lat={lat}, lon={lon}")
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
        response = requests.get(url)
        print(f"Forecast API response status code: {response.status_code}")
        print(f"Forecast API response: {response.text}")
        data = response.json()

        if response.status_code != 200:
            raise Exception(f"Error fetching forecast data: {data.get('message', 'Unknown error')}")

        return data
    except Exception as e:
        print(f"Exception in get_forecast: {e}")
        raise


# Format the forecast message
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


# /start command
async def start(update, context: ContextTypes.DEFAULT_TYPE):
    print("Received /start command")
    chat_id = update.effective_chat.id

    target_time = datetime.time(
        hour=int(TIME_TO_SEND.split(":")[0]),
        minute=int(TIME_TO_SEND.split(":")[1]),
        tzinfo=pytz.UTC,
    )
    print(f"Scheduling daily weather updates at {target_time} UTC")

    if context.job_queue is not None:
        context.job_queue.run_daily(
            send_daily_weather,
            time=target_time,
            data={"chat_id": chat_id},
            name=str(chat_id),
        )

    await update.message.reply_text("Weather bot started! You will receive daily updates.")


# /forecast command
async def forecast(update, context: ContextTypes.DEFAULT_TYPE):
    try:
        print("Received /forecast command")
        chat_id = update.effective_chat.id
        for city in CITIES:
            try:
                forecast_data = get_forecast(city["lat"], city["lon"])
                message = format_forecast_message(city["name"], forecast_data)
                await context.bot.send_message(chat_id=chat_id, text=message)
            except Exception as e:
                print(f"Error fetching forecast for {city['name']}: {e}")
                await context.bot.send_message(chat_id=chat_id, text=f"Failed to fetch forecast for {city['name']} — {e}")
    except Exception as e:
        print(f"Error in `/forecast` command handler: {e}")


# Send daily weather updates
async def send_daily_weather(context: ContextTypes.DEFAULT_TYPE):
    print("Executing send_daily_weather...")
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
                    print(f"Error sending message for {city['name']}: {e}")


# Main function
def main():
    print("Starting bot...")
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("forecast", forecast))

    print("Bot running...")
    application.run_polling()

if __name__ == "__main__":
    main()
