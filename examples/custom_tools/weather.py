
def get_weather(location: str, units: str = "metric") -> str:
    """Get the current weather for a location"""
    print("get_weather", location, units)
    return f"The current weather in {location} is 20 degrees and cloudy."

