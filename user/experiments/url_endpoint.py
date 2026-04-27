"""Helpers for building and testing Transport NSW API endpoint URLs.

The README documents four endpoint families:
- timetable
- trip update
- vehicle position
- alert

This module keeps the URL rules in one place so experiment scripts can import
and test endpoints without hardcoding paths.
"""

from __future__ import annotations

import os
import time
from typing import Literal

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("TRANSPORT_NSW_API_KEY")

MAX_REQUESTS_PER_SECOND = 5
MAX_REQUESTS_PER_DAY = 20000
_MIN_REQUEST_INTERVAL_SECONDS = 1 / MAX_REQUESTS_PER_SECOND
_LAST_REQUEST_AT = 0.0
_REQUEST_COUNT = 0

EndpointFamily = Literal["timetable", "trip_update", "vehicle_position", "alert"]
ApiVersion = Literal["v1", "v2"]

ENDPOINT_REGISTRY: dict[EndpointFamily, dict[ApiVersion, dict[str, object]]] = {
    "timetable": {
        "v1": {
            "base_url": "https://api.transport.nsw.gov.au/v1/gtfs/schedule",
            "paths": {
                "buses": "/buses",
                "ferries": "/ferries/sydneyferries",
                "lightrail": "/lightrail",
                "nswtrains": "/nswtrains",
                "sydneytrains": "/sydneytrains",
            },
        },
        "v2": {
            "base_url": "https://api.transport.nsw.gov.au/v2/gtfs/schedule",
            "paths": {
                "metro": "/metro",
            },
        },
    },
    "trip_update": {
        "v1": {
            "base_url": "https://api.transport.nsw.gov.au/v1/gtfs/realtime",
            "paths": {
                "buses": "/buses",
                "ferries": "/ferries/sydneyferries",
                "lightrail": "/lightrail",
                "nswtrains": "/nswtrains",
                "metro": "/metro",
            },
        },
        "v2": {
            "base_url": "https://api.transport.nsw.gov.au/v2/gtfs/realtime",
            "paths": {
                "sydneytrains": "/sydneytrains",
                "buses": "/buses",
                "ferries": "/ferries/sydneyferries",
                "lightrail": "/lightrail",
                "nswtrains": "/nswtrains",
                "metro": "/metro",
            },
        },
    },
    "vehicle_position": {
        "v2": {
            "base_url": "https://api.transport.nsw.gov.au/v2/gtfs/vehiclepos",
            "paths": {
                "sydneytrains": "/sydneytrains",
                "metro": "/metro",
                "lightrail": "/lightrail/innerwest",

            },
        },
    },
    "alert": {
        "v2": {
            "base_url": "https://api.transport.nsw.gov.au/v2/gtfs/alerts",
            "paths": {
                "all": "/all",
                "buses": "/buses",
                "ferries": "/ferries/sydneyferries",
                "lightrail": "/lightrail",
                "nswtrains": "/nswtrains",
                "sydneytrains": "/sydneytrains",
                "metro": "/metro",
            },
        },
    },
}


def get_headers() -> dict[str, str]:
    if not API_KEY:
        raise RuntimeError("TRANSPORT_NSW_API_KEY is not set")
    return {"Authorization": f"apikey {API_KEY}"}


def _throttle_request() -> None:
    global _LAST_REQUEST_AT, _REQUEST_COUNT

    if _REQUEST_COUNT >= MAX_REQUESTS_PER_DAY:
        raise RuntimeError("Daily Transport NSW API request limit reached")

    now = time.monotonic()
    elapsed = now - _LAST_REQUEST_AT
    if _LAST_REQUEST_AT and elapsed < _MIN_REQUEST_INTERVAL_SECONDS:
        time.sleep(_MIN_REQUEST_INTERVAL_SECONDS - elapsed)

    _LAST_REQUEST_AT = time.monotonic()
    _REQUEST_COUNT += 1


def get_endpoint_url(family: EndpointFamily, service_name: str, version: ApiVersion | None = None) -> str:
    """Return the full URL for a documented endpoint."""

    family_registry = ENDPOINT_REGISTRY.get(family)
    if family_registry is None:
        raise ValueError(f"Unknown endpoint family: {family}")

    if version is None:
        version = "v2" if family in {"vehicle_position", "alert"} else "v1"

    version_registry = family_registry.get(version)
    if version_registry is None:
        raise ValueError(f"Unsupported version '{version}' for family '{family}'")

    paths = version_registry["paths"]
    if service_name not in paths:
        raise ValueError(f"Unknown service name '{service_name}' for family '{family}' and version '{version}'")

    base_url = version_registry["base_url"]
    return f"{base_url}{paths[service_name]}"


def request_endpoint(family: EndpointFamily, service_name: str, version: ApiVersion | None = None, timeout: int = 30) -> requests.Response:
    """Request a configured endpoint and return the response object."""

    _throttle_request()
    url = get_endpoint_url(family, service_name, version)
    return requests.get(url, headers=get_headers(), timeout=timeout)


def test_endpoints(family: EndpointFamily, version: ApiVersion | None = None) -> dict[str, dict[str, object]]:
    """Probe every configured endpoint in a family and return the results."""

    family_registry = ENDPOINT_REGISTRY[family]
    version = version or ("v2" if family in {"vehicle_position", "alert"} else "v1")
    version_registry = family_registry.get(version)
    if version_registry is None:
        raise ValueError(f"Unsupported version '{version}' for family '{family}'")

    headers = get_headers()
    results: dict[str, dict[str, object]] = {}

    for service_name in version_registry["paths"]:
        _throttle_request()
        url = get_endpoint_url(family, service_name, version)
        print(f"Testing {family} endpoint: {service_name} ({version})")
        response = requests.get(url, headers=headers, timeout=30)

        results[service_name] = {
            "url": url,
            "status_code": response.status_code,
            "ok": response.status_code == 200,
            "body": response.text,
        }

        if response.status_code == 200:
            print(f"✅ {service_name} endpoint is working")
        else:
            print(f"❌ {service_name} endpoint is not working. Status code: {response.status_code}")
            print(response.text)

    return results


if __name__ == "__main__":
    for family_name in ENDPOINT_REGISTRY:
        test_endpoints(family_name)