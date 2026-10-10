"""Shared Gemini quota, loaded from backend/rate_limits.toml."""
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import tomllib

CONFIG_PATH = Path(__file__).resolve().parents[1] / 'rate_limits.toml'


@dataclass(frozen=True)
class RateLimits:
    max_requests: int
    window_seconds: int


@lru_cache(maxsize=1)
def load_rate_limits() -> RateLimits:
    data = tomllib.loads(CONFIG_PATH.read_text(encoding='utf-8-sig'))['gemini']
    values = {}
    for name in RateLimits.__dataclass_fields__:
        value = data[name]
        if type(value) is not int or value <= 0:
            raise ValueError(f'{name} must be a positive integer')
        values[name] = value
    return RateLimits(**values)
