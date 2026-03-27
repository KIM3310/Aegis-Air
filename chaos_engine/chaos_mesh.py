"""Chaos mesh probe loop for Aegis-Air.

Drives repeated requests against the target checkout API, detects the
first incident signal, and forwards the alert payload to the Aegis-Air
webhook for analysis.
"""

from __future__ import annotations

import datetime
import random
import time
from typing import Any

import requests

TARGET_API_URL: str = "http://localhost:8000/api/checkout"
AEGIS_WEBHOOK_URL: str = "http://localhost:8001/webhook/alert"
REQUEST_TIMEOUT_SEC: int = 5


def simulate_chaos() -> None:
    """Run a chaos probe loop against the target API.

    Sends up to 14 sequential GET requests to the checkout endpoint.
    On the first HTTP 500, forwards the incident payload to the
    Aegis-Air webhook and stops the loop.
    """
    print("[Chaos Engine] Starting checkout probe loop.")

    for i in range(1, 15):
        print(f"   [Request {i}] -> GET {TARGET_API_URL}")
        try:
            start_time: float = time.time()
            response: requests.Response = requests.get(
                TARGET_API_URL, timeout=REQUEST_TIMEOUT_SEC
            )
            latency: float = time.time() - start_time

            if response.status_code == 200:
                print(f"      OK ({latency:.2f}s) - {response.json()}")
            elif response.status_code == 500:
                print(f"      INCIDENT DETECTED: HTTP 500 {response.text}")
                trigger_incident_response(response.status_code, response.text)

                print("\n[Chaos Engine] Stopping after the first confirmed incident.")
                break

        except requests.exceptions.RequestException as exc:
            print(f"      Connection failed: {exc}")

        time.sleep(random.uniform(0.5, 1.5))


def trigger_incident_response(status_code: int, error_text: str) -> None:
    """Forward an incident payload to the Aegis-Air webhook.

    Args:
        status_code: The HTTP status code observed during the probe.
        error_text: The error response body from the target API.
    """
    print("\n[Monitoring Agent] Sending incident payload to Aegis-Air.")

    payload: dict[str, Any] = {
        "service_name": "E-Commerce-Checkout-API",
        "incident_time": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
        "status_code": status_code,
        "error_details": error_text,
    }

    try:
        webhook_response: requests.Response = requests.post(
            AEGIS_WEBHOOK_URL, json=payload, timeout=REQUEST_TIMEOUT_SEC
        )

        if webhook_response.status_code == 200:
            result: dict[str, Any] = webhook_response.json()
            display_rca(result)
        else:
            print(f"Webhook request failed with status {webhook_response.status_code}.")

    except requests.exceptions.RequestException as exc:
        print(f"Aegis-Air webhook is unreachable: {exc}")


def display_rca(result: dict[str, Any]) -> None:
    """Display the RCA report from the Aegis-Air webhook response.

    Args:
        result: The JSON response from the Aegis-Air webhook.
    """
    print("\n" + "=" * 60)
    print("AEGIS-AIR RCA REPORT")
    print("=" * 60)
    print(result.get("rca_report", "No report content."))
    print("=" * 60 + "\n")


if __name__ == "__main__":
    simulate_chaos()
