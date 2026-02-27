"""
Daladan Platform — Rate Limiting Configuration
Uses slowapi to enforce per-IP rate limits.
Includes a highly restrictive limiter for AI/LLM endpoints.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# ── Global rate limiter (keyed by client IP) ──
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["60/minute"],          # Global: 60 req/min per IP
    storage_uri="memory://",               # In-memory store (production: use Redis)
)

# ── Rate limit strings for specific endpoint tiers ──
RATE_LIMIT_AI = "5/minute"          # Very restrictive: LLM billing protection
RATE_LIMIT_AUTH = "10/minute"       # Auth endpoints: prevent brute force
RATE_LIMIT_WRITE = "30/minute"      # Write endpoints (POST/PUT/DELETE)
RATE_LIMIT_READ = "120/minute"      # Read-heavy endpoints
