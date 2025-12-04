#!/usr/bin/env python3
"""
Weather CLI - Get weather information from the National Weather Service (NWS)
"""

import argparse
import requests
import sys
from typing import Optional


class WeatherClient:
    """Client for interacting with the NWS API"""

    BASE_URL = "https://api.weather.gov"

    def __init__(self, station_code: str):
        """
        Initialize the weather client with a 4-letter station code.

        Args:
            station_code: 4-letter ICAO station code (e.g., KMPR)
        """
        self.station_code = station_code.upper()
        self.headers = {
            'User-Agent': '(Weather CLI Tool, contact@example.com)',
            'Accept': 'application/json'
        }

    def get_current_weather(self) -> Optional[dict]:
        """
        Get current weather observations for the station.

        Returns:
            Dictionary containing weather data or None if error
        """
        url = f"{self.BASE_URL}/stations/{self.station_code}/observations/latest"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching current weather: {e}", file=sys.stderr)
            return None

    def get_forecast(self) -> Optional[dict]:
        """
        Get forecast for the station location.

        Returns:
            Dictionary containing forecast data or None if error
        """
        # First, get the station metadata to find the coordinates
        station_url = f"{self.BASE_URL}/stations/{self.station_code}"

        try:
            station_response = requests.get(station_url, headers=self.headers, timeout=10)
            station_response.raise_for_status()
            station_data = station_response.json()

            # Extract coordinates
            geometry = station_data.get('geometry', {})
            coordinates = geometry.get('coordinates', [])

            if len(coordinates) < 2:
                print("Error: Could not determine station coordinates", file=sys.stderr)
                return None

            lon, lat = coordinates[0], coordinates[1]

            # Get the forecast grid endpoint
            points_url = f"{self.BASE_URL}/points/{lat},{lon}"
            points_response = requests.get(points_url, headers=self.headers, timeout=10)
            points_response.raise_for_status()
            points_data = points_response.json()

            # Get the forecast URL
            forecast_url = points_data.get('properties', {}).get('forecast')

            if not forecast_url:
                print("Error: Could not determine forecast URL", file=sys.stderr)
                return None

            # Fetch the actual forecast
            forecast_response = requests.get(forecast_url, headers=self.headers, timeout=10)
            forecast_response.raise_for_status()
            return forecast_response.json()

        except requests.exceptions.RequestException as e:
            print(f"Error fetching forecast: {e}", file=sys.stderr)
            return None


def format_current_weather(data: dict) -> str:
    """Format current weather data for display"""

    properties = data.get('properties', {})

    # Extract relevant information
    station = properties.get('station', 'Unknown').split('/')[-1]
    timestamp = properties.get('timestamp', 'Unknown')

    # Temperature
    temp = properties.get('temperature', {})
    temp_value = temp.get('value')
    temp_unit = temp.get('unitCode', '').split(':')[-1]

    if temp_value is not None and temp_unit == 'degC':
        temp_f = (temp_value * 9/5) + 32
        temp_str = f"{temp_f:.1f}°F ({temp_value:.1f}°C)"
    elif temp_value is not None:
        temp_str = f"{temp_value:.1f}°{temp_unit}"
    else:
        temp_str = "N/A"

    # Description
    description = properties.get('textDescription', 'N/A')

    # Wind
    wind_speed = properties.get('windSpeed', {}).get('value')
    wind_dir = properties.get('windDirection', {}).get('value')

    if wind_speed is not None and wind_dir is not None:
        wind_str = f"{wind_speed:.1f} km/h from {wind_dir}°"
    else:
        wind_str = "N/A"

    # Humidity
    humidity = properties.get('relativeHumidity', {}).get('value')
    humidity_str = f"{humidity:.0f}%" if humidity is not None else "N/A"

    # Dewpoint
    dewpoint = properties.get('dewpoint', {}).get('value')
    if dewpoint is not None:
        dewpoint_f = (dewpoint * 9/5) + 32
        dewpoint_str = f"{dewpoint_f:.1f}°F ({dewpoint:.1f}°C)"
    else:
        dewpoint_str = "N/A"

    # Pressure
    pressure = properties.get('barometricPressure', {}).get('value')
    if pressure is not None:
        pressure_mb = pressure / 100  # Convert Pa to mb/hPa
        pressure_str = f"{pressure_mb:.1f} mb"
    else:
        pressure_str = "N/A"

    # Visibility
    visibility = properties.get('visibility', {}).get('value')
    if visibility is not None:
        visibility_mi = visibility / 1609.34  # Convert meters to miles
        visibility_str = f"{visibility_mi:.1f} mi"
    else:
        visibility_str = "N/A"

    # Wind chill / Heat index
    wind_chill = properties.get('windChill', {}).get('value')
    heat_index = properties.get('heatIndex', {}).get('value')

    feels_like_str = None
    if wind_chill is not None:
        wind_chill_f = (wind_chill * 9/5) + 32
        feels_like_str = f"{wind_chill_f:.1f}°F (Wind Chill)"
    elif heat_index is not None:
        heat_index_f = (heat_index * 9/5) + 32
        feels_like_str = f"{heat_index_f:.1f}°F (Heat Index)"

    # Cloud coverage
    cloud_layers = properties.get('cloudLayers', [])
    if cloud_layers:
        cloud_str = ", ".join([f"{layer.get('amount', 'N/A')} at {layer.get('base', {}).get('value', 'N/A')}m"
                               for layer in cloud_layers])
    else:
        cloud_str = "N/A"

    # Precipitation
    precip_last_hour = properties.get('precipitationLastHour', {}).get('value')
    if precip_last_hour is not None:
        precip_str = f"{precip_last_hour:.2f} mm"
    else:
        precip_str = "N/A"

    output = f"""
Current Weather for {station}
{'=' * 40}
Time: {timestamp}
Conditions: {description}
Temperature: {temp_str}"""

    if feels_like_str:
        output += f"\nFeels Like: {feels_like_str}"

    output += f"""
Dewpoint: {dewpoint_str}
Wind: {wind_str}
Humidity: {humidity_str}
Pressure: {pressure_str}
Visibility: {visibility_str}
Cloud Layers: {cloud_str}
Precipitation (last hour): {precip_str}
"""
    return output.strip()


def format_forecast(data: dict) -> str:
    """Format forecast data for display"""

    properties = data.get('properties', {})
    periods = properties.get('periods', [])

    if not periods:
        return "No forecast data available"

    output = "\nWeather Forecast\n"
    output += "=" * 40 + "\n\n"

    # Show next 14 periods (7 days)
    for period in periods[:14]:
        name = period.get('name', 'Unknown')
        temp = period.get('temperature', 'N/A')
        temp_unit = period.get('temperatureUnit', 'F')
        short_forecast = period.get('shortForecast', 'N/A')
        detailed = period.get('detailedForecast', '')

        output += f"{name}:\n"
        output += f"  Temperature: {temp}°{temp_unit}\n"
        output += f"  {short_forecast}\n"
        if detailed:
            output += f"  {detailed}\n"
        output += "\n"

    return output.strip()


def main():
    """Main CLI entry point"""

    parser = argparse.ArgumentParser(
        description='Get weather information from the National Weather Service',
        prog='weather'
    )

    parser.add_argument(
        '-l', '--location',
        type=str,
        required=True,
        help='4-letter ICAO station code (e.g., KMPR, KJFK, KSFO)'
    )

    parser.add_argument(
        '-f', '--forecast',
        action='store_true',
        help='Get forecast instead of current weather'
    )

    args = parser.parse_args()

    # Validate station code length
    if len(args.location) != 4:
        print(f"Error: Station code must be 4 characters (got '{args.location}')", file=sys.stderr)
        sys.exit(1)

    # Create weather client
    client = WeatherClient(args.location)

    if args.forecast:
        # Get and display forecast
        data = client.get_forecast()
        if data:
            print(format_forecast(data))
        else:
            sys.exit(1)
    else:
        # Get and display current weather
        data = client.get_current_weather()
        if data:
            print(format_current_weather(data))
        else:
            sys.exit(1)


if __name__ == '__main__':
    main()
