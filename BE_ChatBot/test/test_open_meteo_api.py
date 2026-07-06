"""
Test nhanh Open-Meteo API.
Chay: python -m test.test_open_meteo_api

Khong can API key, khong can .env.
"""

import asyncio
import sys
from datetime import date, timedelta

import httpx

# Fix encoding cho Windows PowerShell
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

SEP = "=" * 60

# Weather code mapping (WMO)
WMO = {
    0: "Troi quang", 1: "Gan nhu quang", 2: "May rai rac", 3: "Nhieu may",
    45: "Suong mu", 48: "Suong mu bang gia",
    51: "Mua phun nhe", 53: "Mua phun", 55: "Mua phun day",
    61: "Mua nhe", 63: "Mua vua", 65: "Mua lon",
    80: "Mua rao nhe", 81: "Mua rao vua", 82: "Mua rao lon",
    95: "Giong", 96: "Giong + mua da nhe", 99: "Giong + mua da lon",
}


async def test_geocode(city: str = "Da Nang"):
    """Test Geocoding API."""
    print(f"\n{SEP}")
    print(f"TEST 1: Geocoding API -- '{city}'")
    print(SEP)

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            GEOCODE_URL,
            params={"name": city, "count": 3, "language": "vi"},
        )
        print(f"Status: {resp.status_code}")
        data = resp.json()
        results = data.get("results", [])
        print(f"So ket qua: {len(results)}")

        for r in results:
            print(f"  - {r['name']}, {r.get('country', '?')}")
            print(f"    Lat: {r['latitude']}, Lng: {r['longitude']}")
            print(f"    Population: {r.get('population', 'N/A')}")
            print(f"    Timezone: {r.get('timezone', 'N/A')}")

        if results:
            return results[0]["latitude"], results[0]["longitude"]
    return None


async def test_forecast(lat: float, lng: float, start_date: str, end_date: str):
    """Test Forecast API."""
    print(f"\n{SEP}")
    print(f"TEST 2: Forecast API -- ({lat}, {lng}), {start_date} -> {end_date}")
    print(SEP)

    daily_vars = [
        "temperature_2m_max", "temperature_2m_min",
        "precipitation_probability_max", "rain_sum",
        "weathercode", "uv_index_max", "windspeed_10m_max",
    ]

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            FORECAST_URL,
            params={
                "latitude": lat,
                "longitude": lng,
                "daily": ",".join(daily_vars),
                "timezone": "Asia/Ho_Chi_Minh",
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        print(f"Status: {resp.status_code}")
        data = resp.json()

        if resp.status_code != 200:
            print(f"Error: {data.get('reason', data)}")
            return

        daily = data.get("daily", {})
        times = daily.get("time", [])
        print(f"So ngay: {len(times)}")
        print(f"Timezone: {data.get('timezone', '?')}")

        for i, day in enumerate(times):
            code = daily.get("weathercode", [None])[i]
            weather_str = WMO.get(code, f"Code {code}")
            temp_min = daily.get("temperature_2m_min", [None])[i]
            temp_max = daily.get("temperature_2m_max", [None])[i]
            precip = daily.get("precipitation_probability_max", [None])[i]
            rain = daily.get("rain_sum", [None])[i]
            uv = daily.get("uv_index_max", [None])[i]
            wind = daily.get("windspeed_10m_max", [None])[i]

            print(f"\n  [{day}]")
            print(f"    Nhiet do : {temp_min}-{temp_max} C")
            print(f"    Mua      : {precip}% | {rain}mm")
            print(f"    UV       : {uv}")
            print(f"    Gio      : {wind} km/h")
            print(f"    Thoi tiet: {weather_str}")


async def test_geocode_edge_cases():
    """Test edge cases cho Geocoding."""
    print(f"\n{SEP}")
    print("TEST 3: Geocoding Edge Cases")
    print(SEP)

    test_cases = [
        # (input, expected_found, note)
        ("Da Lat", True, "Ten khong dau"),
        ("Ho Chi Minh", True, "Ten quoc te"),
        ("Sapa", True, "Ten ngan"),
        ("xyzabc123", False, "Ten vo nghia"),
    ]

    async with httpx.AsyncClient(timeout=10) as client:
        for city, expect_found, note in test_cases:
            try:
                resp = await client.get(
                    GEOCODE_URL,
                    params={"name": city, "count": 1, "language": "vi"},
                )
                data = resp.json()
                results = data.get("results", [])
                found = len(results) > 0
                name = results[0]["name"] if results else "N/A"

                if found == expect_found:
                    status = "[PASS]"
                else:
                    status = "[FAIL]"

                print(f"  {status} '{city}' -> {name} ({note})")
            except Exception as e:
                print(f"  [ERR]  '{city}' -> {e}")


async def test_forecast_edge_cases(lat: float = 16.0678, lng: float = 108.2208):
    """Test edge cases cho Forecast."""
    print(f"\n{SEP}")
    print("TEST 4: Forecast Edge Cases")
    print(SEP)

    today = date.today()

    test_cases = [
        # (start, end, expect_ok, description)
        (
            today.isoformat(),
            (today + timedelta(days=2)).isoformat(),
            True,
            "Hom nay + 2 ngay",
        ),
        (
            (today + timedelta(days=7)).isoformat(),
            (today + timedelta(days=9)).isoformat(),
            True,
            "7 ngay toi (trong range)",
        ),
        (
            (today + timedelta(days=20)).isoformat(),
            (today + timedelta(days=22)).isoformat(),
            False,
            "20 ngay toi (ngoai range 16 ngay)",
        ),
        (
            (today - timedelta(days=5)).isoformat(),
            (today - timedelta(days=3)).isoformat(),
            False,
            "Qua khu (nen fail hoac tra data cu)",
        ),
    ]

    async with httpx.AsyncClient(timeout=10) as client:
        for start, end, expect_ok, desc in test_cases:
            try:
                resp = await client.get(
                    FORECAST_URL,
                    params={
                        "latitude": lat, "longitude": lng,
                        "daily": "temperature_2m_max",
                        "timezone": "Asia/Ho_Chi_Minh",
                        "start_date": start, "end_date": end,
                    },
                )
                data = resp.json()
                n = len(data.get("daily", {}).get("time", []))
                ok = resp.status_code == 200 and n > 0

                if ok == expect_ok:
                    status = "[PASS]"
                else:
                    status = "[WARN]"

                print(f"  {status} {desc}: status={resp.status_code}, days={n}")
            except Exception as e:
                print(f"  [ERR]  {desc}: {e}")


async def main():
    print("\nOpen-Meteo API Test Suite")
    print(SEP)
    print("Khong can API key. Tat ca endpoint deu free.")
    print(f"Today: {date.today().isoformat()}")

    # Test 1: Geocode
    coords = await test_geocode("Da Nang")

    # Test 2: Forecast
    if coords:
        today = date.today()
        start = today.isoformat()
        end = (today + timedelta(days=2)).isoformat()
        await test_forecast(coords[0], coords[1], start, end)

    # Test 3 & 4: Edge cases
    await test_geocode_edge_cases()
    await test_forecast_edge_cases()

    print(f"\n{SEP}")
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
