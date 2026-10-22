import requests

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"

HEADERS = {
    "User-Agent": "KrishiMitra/1.0 (Indian agricultural assistant app)"
}


def geocode_location(location: str) -> dict | None:
    """
    Convert a village, district or city name to lat/lng.
    Uses OpenStreetMap Nominatim.
    Returns: { "lat": float, "lng": float, "display_name": str, "district": str, "state": str }
    """
    if not location or not location.strip():
        return None

    params = {
        "q": f"{location.strip()}, India",
        "format": "json",
        "addressdetails": 1,
        "limit": 1,
        "countrycodes": "in",
    }

    try:
        response = requests.get(NOMINATIM_SEARCH_URL, params=params, headers=HEADERS, timeout=10)
        results = response.json()
        if not results:
            return None

        best = results[0]
        addr = best.get("address", {})
        district = (
            addr.get("state_district")
            or addr.get("district")
            or addr.get("county")
            or addr.get("city")
            or addr.get("town")
            or ""
        )
        state = addr.get("state") or ""

        return {
            "lat": float(best["lat"]),
            "lng": float(best["lon"]),
            "display_name": best.get("display_name", location),
            "district": district,
            "state": state,
        }
    except Exception as e:
        print(f"Geocoding failed for '{location}': {e}")
        return None


def reverse_geocode(lat: float, lng: float) -> dict:
    """
    Convert latitude & longitude to address details (district, state, display_name).
    """
    params = {
        "lat": lat,
        "lon": lng,
        "format": "json",
        "addressdetails": 1,
    }

    try:
        response = requests.get(NOMINATIM_REVERSE_URL, params=params, headers=HEADERS, timeout=10)
        data = response.json()
        addr = data.get("address", {})

        district = (
            addr.get("state_district")
            or addr.get("district")
            or addr.get("county")
            or addr.get("city")
            or addr.get("town")
            or ""
        )
        state = addr.get("state") or ""
        village = (
            addr.get("village")
            or addr.get("suburb")
            or addr.get("hamlet")
            or addr.get("neighbourhood")
            or ""
        )

        place_parts = [p for p in [village, district, state] if p]
        location_text = ", ".join(place_parts) if place_parts else data.get("display_name", "India")

        return {
            "display_name": location_text,
            "district": district,
            "state": state,
            "village": village,
        }
    except Exception as e:
        print(f"Reverse geocoding failed for {lat}, {lng}: {e}")
        return {
            "display_name": "Shared Location",
            "district": "",
            "state": "",
            "village": "",
        }