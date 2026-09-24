from services.weather_service import get_live_weather

latitude = 27.33
longitude = 88.61

data = get_live_weather(latitude, longitude)

print("\n===== LIVE WEATHER DATA =====")

for key, value in data.items():
    print(f"{key}: {value}")