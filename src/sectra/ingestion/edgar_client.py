import json
import logging
import time
from pathlib import Path

import requests

log = logging.getLogger(__name__)


class EdgarClient:
    def __init__(
            self,
            user_agent: str,
            max_rps: float = 8.0,
            max_retries: int = 5,
            timeout: int = 30,
    ):
        if max_rps <= 0:
            raise ValueError("max_rps must be greater than 0")

        if max_retries <= 0:
            raise ValueError("max_retries must be greater than 0")

        # HTTP session with persistent headers
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": user_agent,
            "Accept-Encoding": "gzip, deflate",
        })

        # Rate limiting configuration
        self.min_interval = 1.0 / max_rps
        self._last = 0.0

        # Retry configuration
        self.max_retries = max_retries
        self.timeout = timeout

        # Network request counter (useful for testing cache)
        self.network_calls = 0

    def _throttle(self) -> None:
        """Ensure requests are spaced according to max_rps."""

        now = time.monotonic()
        elapsed = now - self._last

        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)

        self._last = time.monotonic()

    def _get(self, url: str) -> bytes:
        """Perform HTTP GET with throttling and exponential backoff."""

        for attempt in range(self.max_retries):
            self._throttle()
            self.network_calls += 1

            try:
                r = self.session.get(
                    url,
                    timeout=self.timeout,
                )

            except (requests.ConnectionError, requests.Timeout) as exc:
                reason = str(exc)
                retry_after = None

            else:
                if r.status_code == 200:
                    return r.content

                if r.status_code == 404:
                    raise FileNotFoundError(url)

                if r.status_code == 403:
                    raise PermissionError(
                        f"SEC denied {url}: check User-Agent / rate limit"
                    )

                if r.status_code != 429 and r.status_code < 500:
                    r.raise_for_status()

                reason = f"HTTP {r.status_code}"
                retry_after = r.headers.get("Retry-After")

            # Stop after the configured number of attempts
            if attempt == self.max_retries - 1:
                break

            # Respect Retry-After when it contains numeric seconds
            delay = (
                int(retry_after)
                if retry_after and retry_after.isdigit()
                else 2 ** attempt
            )

            log.warning(
                "%s on %s, retry %d/%d in %ds",
                reason,
                url,
                attempt + 1,
                self.max_retries,
                delay,
                )

            time.sleep(delay)

        raise RuntimeError(
            f"Gave up after {self.max_retries} attempts: {url}"
        )

    def fetch(
            self,
            url: str,
            dest: Path,
            refresh: bool = False,
    ) -> bytes:
        """Fetch data with disk caching and atomic writes."""

        dest = Path(dest)

        # Cache hit: return existing file without network request
        if dest.exists() and not refresh:
            log.debug("Cache hit: %s", dest)
            return dest.read_bytes()

        log.debug("Cache miss: %s", dest)

        # Fetch from SEC
        content = self._get(url)

        # Ensure destination directory exists
        dest.parent.mkdir(parents=True, exist_ok=True)

        # Write to temporary file before replacing destination
        temp_dest = dest.with_name(dest.name + ".part")

        try:
            temp_dest.write_bytes(content)

            # Atomic replacement
            temp_dest.replace(dest)

        finally:
            # Remove temporary file if writing/replacement fails
            if temp_dest.exists():
                temp_dest.unlink()

        return content

    def fetch_json(
            self,
            url: str,
            dest: Path,
            refresh: bool = False,
    ) -> dict:
        """Fetch JSON data and deserialize it."""

        return json.loads(
            self.fetch(url, dest, refresh)
        )

    def close(self) -> None:
        """Close the underlying HTTP session."""

        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
