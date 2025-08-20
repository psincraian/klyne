"""
HTTP transport for sending analytics data to Klyne API.
Uses only standard library to minimize dependencies.
"""

import json
import logging
import threading
import time
from queue import Empty, Queue
from typing import Any, Dict, List
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# Set up logger
logger = logging.getLogger(__name__)


class HTTPTransport:
    """
    Lightweight HTTP transport for analytics data.
    Sends data asynchronously in background thread to avoid blocking.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://www.klyne.dev",
        batch_size: int = 10,
        flush_interval: int = 30,
        timeout: int = 10,
        max_retries: int = 3,
    ):
        """
        Initialize HTTP transport.

        Args:
            api_key: Klyne API key
            base_url: Base URL for Klyne API
            batch_size: Number of events to batch before sending
            flush_interval: Maximum seconds to wait before sending batch
            timeout: HTTP request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.timeout = timeout
        self.max_retries = max_retries

        # Event queue and worker thread
        self._queue = Queue()
        self._worker_thread = None
        self._shutdown = False
        self._enabled = True

        # Start background worker
        self._start_worker()

    def _start_worker(self):
        """Start the background worker thread."""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._shutdown = False
            self._worker_thread = threading.Thread(
                target=self._worker_loop, daemon=True, name="klyne-transport"
            )
            self._worker_thread.start()

    def _worker_loop(self):
        """Main worker loop for processing events."""
        batch = []
        last_flush = time.time()

        while not self._shutdown:
            try:
                # Try to get an event with timeout
                try:
                    event = self._queue.get(timeout=1.0)
                    if event is None:  # Shutdown signal
                        break
                    batch.append(event)
                except Empty:
                    # No events available, continue
                    pass

                # Check if we should flush the batch
                should_flush = len(batch) >= self.batch_size or (
                    batch and time.time() - last_flush >= self.flush_interval
                )

                if should_flush and batch:
                    self._send_batch(batch)
                    batch = []
                    last_flush = time.time()

            except Exception as e:
                logger.error(f"Error in Klyne transport worker: {e}")
                time.sleep(1)  # Brief pause before continuing

        # Flush remaining events on shutdown
        if batch:
            self._send_batch(batch)

    def _send_batch(self, events: List[Dict[str, Any]]):
        """Send a batch of events to the API."""
        if not self._enabled or not events:
            return

        url = f"{self.base_url}/api/analytics/batch"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "klyne-python-sdk/0.1.0",
        }

        payload = {"events": events}
        data = json.dumps(payload).encode("utf-8")

        for attempt in range(self.max_retries + 1):
            try:
                request = Request(url, data=data, headers=headers)

                with urlopen(request, timeout=self.timeout) as response:
                    if response.status == 200:
                        logger.debug(f"Successfully sent {len(events)} events to Klyne")
                        return
                    else:
                        logger.warning(f"Klyne API returned status {response.status}")

            except HTTPError as e:
                if e.code == 429:  # Rate limit
                    logger.warning("Klyne API rate limit reached, backing off")
                    time.sleep(min(2**attempt, 60))  # Exponential backoff
                elif e.code == 401:  # Unauthorized
                    logger.error(e.msg)
                    logger.error("Klyne API key is invalid")
                    self._enabled = False  # Disable further attempts
                    return
                elif e.code == 403:  # Forbidden
                    logger.error("Klyne API key not authorized for this package")
                    self._enabled = False
                    return
                else:
                    logger.warning(f"Klyne API error {e.code}: {e.reason}")

            except URLError as e:
                logger.warning(f"Network error sending to Klyne: {e.reason}")

            except Exception as e:
                logger.warning(f"Unexpected error sending to Klyne: {e}")

            # Wait before retrying (except on last attempt)
            if attempt < self.max_retries:
                time.sleep(min(2**attempt, 30))

        logger.error(
            f"Failed to send {len(events)} events to Klyne after {self.max_retries + 1} attempts"
        )

    def send_event(self, event: Dict[str, Any]):
        """
        Queue an event for sending.

        Args:
            event: Analytics event dictionary
        """
        if not self._enabled:
            return

        try:
            # Add to queue (non-blocking)
            self._queue.put_nowait(event)
        except Exception as e:
            logger.warning(f"Failed to queue Klyne event: {e}")

    def flush(self, timeout: float = 10.0):
        """
        Flush all pending events.

        Args:
            timeout: Maximum time to wait for flush completion
        """
        if not self._worker_thread or not self._worker_thread.is_alive():
            return

        # Signal flush by checking queue size
        queue_size = self._queue.qsize()
        if queue_size == 0:
            return

        # Wait for queue to be processed
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self._queue.qsize() == 0:
                break
            time.sleep(0.1)

    def shutdown(self, timeout: float = 5.0):
        """
        Shutdown the transport and flush remaining events.

        Args:
            timeout: Maximum time to wait for shutdown
        """
        self._shutdown = True

        # Signal worker to stop
        try:
            self._queue.put_nowait(None)
        except Exception:
            pass

        # Wait for worker to finish
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=timeout)

    def enable(self):
        """Enable the transport."""
        self._enabled = True
        self._start_worker()

    def disable(self):
        """Disable the transport."""
        self._enabled = False

    def is_enabled(self) -> bool:
        """Check if transport is enabled."""
        return self._enabled
