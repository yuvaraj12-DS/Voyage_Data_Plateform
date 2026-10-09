"""Smoke-test the configured Ollama Cloud/local API without touching Databricks."""
from __future__ import annotations

from .agent import _get_client
from .config import OLLAMA_MODEL


def main() -> None:
    client = _get_client()
    response = client.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": "Reply with exactly: VoyageData model connection PASS"}],
        options={"temperature": 0},
    )
    message = (response.message.content or "").strip()
    if not message:
        raise SystemExit("FAIL: model returned an empty response")
    print("Ollama connection PASS")
    print(f"Configured model: {OLLAMA_MODEL}")
    print(f"Response: {message}")


if __name__ == "__main__":
    main()
