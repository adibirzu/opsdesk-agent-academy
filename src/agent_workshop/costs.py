"""Explicit, auditable estimates. Not a billing API or a spending hard cap."""
from datetime import date
from decimal import Decimal
import math
from urllib.parse import urlsplit


def validate_pricing(pricing, model_id):
    required = {"model_id", "currency", "input_usd_per_million", "output_usd_per_million", "source", "as_of"}
    if not isinstance(pricing, dict) or set(pricing) != required:
        raise ValueError("Pricing requires exact model, USD rates, source and date")
    if pricing["model_id"] != model_id or pricing["currency"] != "USD":
        raise ValueError("Pricing must match the requested model and currency")
    for name in ("input_usd_per_million", "output_usd_per_million"):
        value = pricing[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1_000_000:
            raise ValueError("Invalid configured token price")
    source = urlsplit(str(pricing["source"]))
    if source.scheme != "https" or not source.hostname or source.username or source.password or source.query or source.fragment:
        raise ValueError("Pricing source must be a credential-free HTTPS URL")
    date.fromisoformat(pricing["as_of"])
    return pricing


def estimate_cost(pricing, model_id, input_tokens, output_tokens):
    for value in (input_tokens, output_tokens):
        if value is not None and (isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 1_000_000_000):
            raise ValueError("Usage must be a bounded nonnegative integer or unknown")
    if input_tokens is None or output_tokens is None or model_id != pricing["model_id"]:
        return None
    validate_pricing(pricing, model_id)
    incoming = Decimal(str(pricing["input_usd_per_million"])) * input_tokens / 1_000_000
    outgoing = Decimal(str(pricing["output_usd_per_million"])) * output_tokens / 1_000_000
    return {"input": float(incoming), "output": float(outgoing), "total": float(incoming + outgoing),
            "currency": "USD", "source": pricing["source"], "as_of": pricing["as_of"],
            "basis": "configured_uncached_text_rates", "provider_billed": False}
