# src/scrapers/base/rate_limiter.py
"""
Thread-safe rate limiter for coordinating scraping across parallel workers.
Ensures we don't exceed site rate limits even with multiple workers.
"""
from __future__ import annotations
import threading
import time
from datetime import datetime, timedelta
class RateLimiter:
    """
    Thread-safe rate limiter that coordinates requests across multiple workers.
    
    Uses a sliding window approach: tracks timestamps of recent requests and
    blocks if we would exceed the rate limit.
    
    Example:
        # Shared across all workers scraping IranTalent
        limiter = RateLimiter(requests_per_minute=20)
        
        # In worker thread:
        limiter.wait_if_needed()  # Blocks if rate limit would be exceeded
        scrape_page()  # Now safe to make request
    """

    def __init__(self, requests_per_minute: int):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Maximum requests allowed per minute
        """
        self.requests_per_minute = requests_per_minute
        self.request_times: list[datetime] = []
        self.lock = threading.Lock()



    def wait_if_needed(self) -> float:
        """
        Block if making a request now would exceed the rate limit.
        
        This method is thread-safe and coordinates across all workers
        using the same RateLimiter instance.
        
        Returns:
            float: Seconds waited (0 if no wait needed)
        """
        total_wait = 0.0

        while True:
            with self.lock:
                now = datetime.now()
                cutoff = now - timedelta(minutes=1)

                # Remove requests older than 1 minute (outside sliding window)
                self.request_times = [t for t in self.request_times if t > cutoff]

                # If we still have capacity, record request and proceed
                if len(self.request_times) < self.requests_per_minute:
                    self.request_times.append(now)
                    return total_wait

                # Otherwise compute how long until oldest request expires
                oldest_request = self.request_times[0]
                wait_until = oldest_request + timedelta(minutes=1)
                wait_seconds = max(0.0, (wait_until - now).total_seconds())

            # Sleep outside lock so other workers can make progress
            if wait_seconds > 0:
                time.sleep(wait_seconds)
                total_wait += wait_seconds
        

    def get_stats(self) -> dict[str, int | float]:
        """
        Get current rate limiter statistics.
        
        Returns:
            Dict with: requests_in_window, capacity, utilization_percent
        """
        with self.lock:
            now = datetime.now()
            cutoff = now - timedelta(minutes=1)
            active_requests = [t for t in self.request_times if t > cutoff]
            
            return {
                'requests_in_window': len(active_requests),
                'capacity': self.requests_per_minute,
                'utilization_percent': (len(active_requests) / self.requests_per_minute) * 100
            }
        


class RateLimiterRegistry:
    """
    Registry for managing multiple site-specific rate limiters.
    
    Ensures each site gets exactly one shared RateLimiter instance
    across all workers.
    
    Example:
        registry = RateLimiterRegistry({
            'irantalent': 20,
            'jobinja': 15,
            'jobvision': 20
        })
        
        # In worker threads:
        limiter = registry.get_limiter('irantalent')
        limiter.wait_if_needed()
    """
    
    def __init__(self, rate_limits: dict[str, int]):
        """
        Initialize registry with rate limits for each site.
        
        Args:
            rate_limits: Dict mapping site names to requests_per_minute
                Example: {'irantalent': 20, 'jobinja': 15}
        """
        self._limiters: dict[str, RateLimiter] = {}
        self._lock = threading.Lock()
        
        # Create limiters for each site
        for site, rpm in rate_limits.items():
            self._limiters[site] = RateLimiter(rpm)
    
    def get_limiter(self, site: str) -> RateLimiter:
        """
        Get the rate limiter for a specific site.
        
        Args:
            site: Site identifier (e.g., 'irantalent')
            
        Returns:
            RateLimiter instance for that site
            
        Raises:
            KeyError: If site not found in registry
        """
        if site not in self._limiters:
            raise KeyError(f"No rate limiter configured for site: {site}")
        
        return self._limiters[site]
    
    def get_all_stats(self) -> dict[str, dict[str, int | float]]:
        """
        Get statistics for all rate limiters.
        
        Returns:
            Dict mapping site names to their stats
        """
        return {
            site: limiter.get_stats()
            for site, limiter in self._limiters.items()
        }
