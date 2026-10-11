"""Private Google Apps Script storage used by the deployed Streamlit app.

The script URL and shared secret live in Streamlit Secrets (or local environment
variables), never in source control.  The script itself owns the Google Sheet
and Drive folder through the researcher's Google account.
"""

import base64
import json
import os
from typing import Any, Dict, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen


MAX_AUDIO_BYTES = 5 * 1024 * 1024


def _settings() -> Dict[str, str]:
    """Read storage settings without requiring Streamlit during unit tests."""
    url = os.getenv("GOOGLE_APPS_SCRIPT_URL", "").strip()
    secret = os.getenv("GOOGLE_APPS_SCRIPT_SECRET", "").strip()
    if url and secret:
        return {"url": url, "secret": secret}

    try:
        import streamlit as st

        settings = st.secrets.get("google_storage", {})
        url = str(settings.get("apps_script_url", "")).strip()
        secret = str(settings.get("apps_script_secret", "")).strip()
    except Exception:
        return {}

    return {"url": url, "secret": secret} if url and secret else {}


def is_configured() -> bool:
    return bool(_settings())


def _post(payload: Dict[str, Any]) -> Dict[str, Any]:
    settings = _settings()
    if not settings:
        raise RuntimeError(
            "Google storage is not configured yet. Ask the researcher to finish the private Google setup before collecting submissions."
        )

    body = json.dumps({"secret": settings["secret"], **payload}).encode("utf-8")
    request = Request(
        settings["url"],
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        raise RuntimeError("Google storage could not be reached. Please try again.") from error

    if not result.get("ok"):
        raise RuntimeError(result.get("error", "Google storage rejected this request."))
    return result


def load_state() -> Optional[Dict[str, Any]]:
    """Return the last saved database snapshot, or None for a new Sheet."""
    result = _post({"action": "load_state"})
    return result.get("state")


def save_state(state: Dict[str, Any]) -> None:
    _post({"action": "save_state", "state": state})


def upload_voice_memo(audio_bytes: bytes, session_token: str) -> str:
    """Upload a recorded WAV file and return its private Drive URL."""
    if not audio_bytes:
        raise ValueError("Please record your voice memo before submitting.")
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise ValueError("That recording is over the 5 MB limit. Please re-record a shorter memo (about two minutes or less).")

    result = _post(
        {
            "action": "upload_audio",
            "session_token": session_token,
            "audio_base64": base64.b64encode(audio_bytes).decode("ascii"),
        }
    )
    return str(result["url"])
