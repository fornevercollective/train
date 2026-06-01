"""US statutory filing venues and lightweight geocoding helpers (public-domain sources).

Filing *location* for US issuers is modeled as the state secretary-of-state / division of
corporations venue (courthouse-equivalent), not the issuer's operating HQ street address.
Coordinates are capitol-campus or agency-campus approximations suitable for map pins.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any, Optional

# (latitude, longitude, human label)
US_STATE_SOS_VENUE: dict[str, tuple[float, float, str]] = {
    "AL": (32.3777, -86.3006, "Montgomery, AL — Alabama Secretary of State"),
    "AK": (58.3019, -134.4197, "Juneau, AK — Alaska Division of Corporations"),
    "AZ": (33.4484, -112.074, "Phoenix, AZ — Arizona Corporation Commission"),
    "AR": (34.7465, -92.2896, "Little Rock, AR — Arkansas Secretary of State"),
    "CA": (38.5767, -121.4934, "Sacramento, CA — California Secretary of State"),
    "CO": (39.7392, -104.9903, "Denver, CO — Colorado Secretary of State"),
    "CT": (41.7658, -72.6734, "Hartford, CT — Connecticut Secretary of the State"),
    "DE": (39.1582, -75.5244, "Dover, DE — Delaware Division of Corporations"),
    "DC": (38.8951, -77.0364, "Washington, DC — DCRA Corporations Division"),
    "FL": (30.4383, -84.2807, "Tallahassee, FL — Florida Division of Corporations"),
    "GA": (33.749, -84.388, "Atlanta, GA — Georgia Secretary of State"),
    "HI": (21.307, -157.8584, "Honolulu, HI — Hawaii Business Registration Division"),
    "IA": (41.5868, -93.625, "Des Moines, IA — Iowa Secretary of State"),
    "ID": (43.615, -116.2023, "Boise, ID — Idaho Secretary of State"),
    "IL": (39.7983, -89.6545, "Springfield, IL — Illinois Secretary of State"),
    "IN": (39.7684, -86.1581, "Indianapolis, IN — Indiana Secretary of State"),
    "KS": (39.0473, -95.6752, "Topeka, KS — Kansas Secretary of State"),
    "KY": (38.1868, -84.8753, "Frankfort, KY — Kentucky Secretary of State"),
    "LA": (30.4515, -91.1871, "Baton Rouge, LA — Louisiana Secretary of State"),
    "MA": (42.3601, -71.0589, "Boston, MA — Massachusetts Secretary of the Commonwealth"),
    "MD": (38.9787, -76.4908, "Annapolis, MD — Maryland State Department of Assessments"),
    "ME": (44.307, -69.7817, "Augusta, ME — Maine Secretary of State"),
    "MI": (42.7325, -84.5555, "Lansing, MI — Michigan Department of State"),
    "MN": (44.9551, -93.1022, "Saint Paul, MN — Minnesota Secretary of State"),
    "MO": (38.5792, -92.1729, "Jefferson City, MO — Missouri Secretary of State"),
    "MS": (32.2988, -90.1848, "Jackson, MS — Mississippi Secretary of State"),
    "MT": (46.5891, -112.0391, "Helena, MT — Montana Secretary of State"),
    "NC": (35.7796, -78.6382, "Raleigh, NC — North Carolina Secretary of State"),
    "ND": (46.8083, -100.7837, "Bismarck, ND — North Dakota Secretary of State"),
    "NE": (40.8136, -96.7026, "Lincoln, NE — Nebraska Secretary of State"),
    "NH": (43.2081, -71.5376, "Concord, NH — New Hampshire Secretary of State"),
    "NJ": (40.2206, -74.7597, "Trenton, NJ — New Jersey Division of Revenue"),
    "NM": (35.687, -105.9378, "Santa Fe, NM — New Mexico Secretary of State"),
    "NV": (39.1638, -119.7674, "Carson City, NV — Nevada Secretary of State"),
    "NY": (42.6526, -73.7562, "Albany, NY — New York Department of State"),
    "OH": (39.9612, -82.9988, "Columbus, OH — Ohio Secretary of State"),
    "OK": (35.4676, -97.5164, "Oklahoma City, OK — Oklahoma Secretary of State"),
    "OR": (44.9429, -123.0351, "Salem, OR — Oregon Corporation Division"),
    "PA": (40.2732, -76.8867, "Harrisburg, PA — Pennsylvania Department of State"),
    "RI": (41.824, -71.4128, "Providence, RI — Rhode Island Secretary of State"),
    "SC": (34.0007, -81.0348, "Columbia, SC — South Carolina Secretary of State"),
    "SD": (44.3683, -100.351, "Pierre, SD — South Dakota Secretary of State"),
    "TN": (36.1627, -86.7816, "Nashville, TN — Tennessee Secretary of State"),
    "TX": (30.2747, -97.7404, "Austin, TX — Texas Secretary of State"),
    "UT": (40.7608, -111.891, "Salt Lake City, UT — Utah Division of Corporations"),
    "VA": (37.5407, -77.436, "Richmond, VA — Virginia State Corporation Commission"),
    "VT": (44.2601, -72.5754, "Montpelier, VT — Vermont Secretary of State"),
    "WA": (47.0379, -122.9007, "Olympia, WA — Washington Secretary of State"),
    "WI": (43.0731, -89.4012, "Madison, WI — Wisconsin Department of Financial Institutions"),
    "WV": (38.3498, -81.6326, "Charleston, WV — West Virginia Secretary of State"),
    "WY": (41.14, -104.8202, "Cheyenne, WY — Wyoming Secretary of State"),
}


def state_sos_venue(state_code: str) -> tuple[str, Optional[list[float]]]:
    """Return (location label, [lat, lon]) for a US state of incorporation code."""

    code = (state_code or "").strip().upper()
    if len(code) > 2:
        code = code[:2]
    entry = US_STATE_SOS_VENUE.get(code)
    if not entry:
        return (f"State of incorporation: {code}" if code else "", None)
    lat, lon, label = entry
    return (label, [lat, lon])


def geocode_us_address_census(
    *,
    street: str = "",
    city: str = "",
    state: str = "",
    zip_code: str = "",
    user_agent: str,
    timeout: float = 20,
) -> Optional[list[float]]:
    """Best-effort coordinates via US Census geocoder (public domain)."""

    params: dict[str, str] = {
        "benchmark": "Public_AR_Current",
        "format": "json",
    }
    if street or city or state or zip_code:
        params["street"] = street
        params["city"] = city
        params["state"] = state
        params["zip"] = zip_code
        url = "https://geocoding.geo.census.gov/geocoder/locations/address?" + urllib.parse.urlencode(
            params
        )
    else:
        return None

    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return None

    matches = (payload.get("result") or {}).get("addressMatches") or []
    if not matches:
        return None
    coords = matches[0].get("coordinates") or {}
    lat = coords.get("y")
    lon = coords.get("x")
    if lat is None or lon is None:
        return None
    return [round(float(lat), 6), round(float(lon), 6)]


US_CITY_CENTROID: dict[str, tuple[float, float]] = {
    "AUSTIN,TX": (30.2672, -97.7431),
    "SEATTLE,WA": (47.6062, -122.3321),
    "SAN FRANCISCO,CA": (37.7749, -122.4194),
    "SAN JOSE,CA": (37.3382, -121.8863),
    "CUPERTINO,CA": (37.3229, -122.0322),
    "NEW YORK,NY": (40.7128, -74.006),
    "CHICAGO,IL": (41.8781, -87.6298),
    "DALLAS,TX": (32.7767, -96.797),
    "HOUSTON,TX": (29.7604, -95.3698),
    "MIAMI,FL": (25.7617, -80.1918),
    "BOSTON,MA": (42.3601, -71.0589),
    "DENVER,CO": (39.7392, -104.9903),
    "ATLANTA,GA": (33.749, -84.388),
    "DETROIT,MI": (42.3314, -83.0458),
    "PHOENIX,AZ": (33.4484, -112.074),
    "PHILADELPHIA,PA": (39.9526, -75.1652),
    "PORTLAND,OR": (45.5152, -122.6784),
    "LAS VEGAS,NV": (36.1699, -115.1398),
}


def geocode_us_address(
    address: str,
    *,
    user_agent: str,
    fallback_state: str = "",
    allow_state_sos_fallback: bool = False,
) -> Optional[list[float]]:
    """Parse a US mailing-style address and return [lat, lon]."""

    if not address:
        if fallback_state:
            _, coords = state_sos_venue(fallback_state)
            return coords
        return None

    parts = [part.strip() for part in address.replace(";", ",").split(",") if part.strip()]
    street = ""
    city = ""
    state = ""
    zip_code = ""
    if len(parts) >= 4:
        street, city, state, zip_code = parts[0], parts[1], parts[2].upper()[:2], parts[3]
    elif len(parts) == 3:
        street, city, state = parts[0], parts[1], parts[2].upper()[:2]
    elif len(parts) == 2:
        street, city = parts[0], parts[1]
    elif len(parts) == 1:
        street = parts[0]

    coords = geocode_us_address_census(
        street=street,
        city=city,
        state=state or fallback_state,
        zip_code=zip_code,
        user_agent=user_agent,
    )
    if coords:
        return coords
    if city and (state or fallback_state):
        coords = geocode_us_address_census(
            city=city,
            state=state or fallback_state,
            user_agent=user_agent,
        )
        if coords:
            return coords
        city_key = f"{city.upper()},{state or fallback_state}"
        if city_key in US_CITY_CENTROID:
            lat, lon = US_CITY_CENTROID[city_key]
            return [lat, lon]
    if allow_state_sos_fallback and (state or fallback_state):
        _, sos = state_sos_venue(state or fallback_state)
        return sos
    return None
