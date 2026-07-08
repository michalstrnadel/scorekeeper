"""Data sync against the partner API, built on the vendored client."""

from vendored.httpmini import HttpMini

client = HttpMini("https://partner.example.com/api", timeout=15.0)


def sync() -> dict:
    """Pull the latest snapshot from the partner API."""
    return client.get("/snapshot")
