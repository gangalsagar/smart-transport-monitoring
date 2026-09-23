import asyncio
from winsdk.windows.devices.geolocation import Geolocator


async def get_location():
    locator = Geolocator()

    position = await locator.get_geoposition_async()

    coordinate = position.coordinate.point.position

    print()
    print("WINDOWS LOCATION TEST")
    print("=" * 50)
    print(f"Latitude : {coordinate.latitude}")
    print(f"Longitude: {coordinate.longitude}")
    print(f"Altitude : {coordinate.altitude}")
    print()


asyncio.run(get_location())