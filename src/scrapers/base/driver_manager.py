# src/scrapers/base/driver_manager.py
"""
Selenium WebDriver lifecycle management.
Handles driver creation, configuration, and cleanup.
"""
from __future__ import annotations
import logging
from typing import Literal
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger(__name__)


class DriverManager:
    """
    Manages Selenium WebDriver lifecycle for scrapers.
    
    Provides factory methods for creating properly configured drivers
    and ensures proper cleanup.
    
    Design:
    - Lazy initialization (create driver when needed)
    - Each worker gets its own driver instance
    - Automatic cleanup on context exit
    
    Example:
        with DriverManager.create_driver() as driver:
            driver.get("https://example.com")
            # ... scraping logic
        # Driver automatically cleaned up
    """
    
    @staticmethod
    def get_chrome_options(headless: bool = True) -> Options:
        """
        Get standard Chrome options for scraping.
        
        Args:
            headless: Whether to run in headless mode
            
        Returns:
            Configured Chrome Options
        """
        chrome_options = Options()
        
        # Basic options
        if headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        # User agent
        chrome_options.add_argument(
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        # Anti-detection measures
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        return chrome_options
    
    @staticmethod
    def create_driver(headless: bool = True, timeout: int = 40) -> webdriver.Chrome:
        """
        Create a new Chrome WebDriver with anti-detection settings.
        
        Args:
            headless: Whether to run in headless mode
            timeout: Page load timeout in seconds
            
        Returns:
            Configured Chrome WebDriver
        """
        chrome_options = DriverManager.get_chrome_options(headless)
        driver = webdriver.Chrome(options=chrome_options)
        
        # Remove webdriver property to avoid detection
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            '''
        })
        
        # Set timeout
        driver.set_page_load_timeout(timeout)
        
        logger.debug(f"Created Chrome driver (headless={headless}, timeout={timeout}s)")
        
        return driver
    
    @staticmethod
    def cleanup_driver(driver: webdriver.Chrome | None) -> None:
        """
        Safely cleanup a WebDriver instance.
        
        Args:
            driver: Driver to cleanup (None-safe)
        """
        if driver:
            try:
                driver.quit()
                logger.debug("Driver cleaned up successfully")
            except Exception as e:
                logger.warning(f"Error cleaning up driver: {e}")


class DriverContext:
    """
    Context manager for WebDriver lifecycle.
    
    Ensures driver is properly cleaned up even if exceptions occur.
    
    Example:
        with DriverContext() as driver:
            driver.get("https://example.com")
            # ... scraping logic
        # Driver automatically cleaned up
    """
    
    def __init__(self, headless: bool = True, timeout: int = 40):
        """
        Initialize driver context.
        
        Args:
            headless: Whether to run in headless mode
            timeout: Page load timeout in seconds
        """
        self.headless = headless
        self.timeout = timeout
        self.driver: webdriver.Chrome | None = None
    
    def __enter__(self) -> webdriver.Chrome:
        """Create and return driver on context entry."""
        self.driver = DriverManager.create_driver(
            headless=self.headless,
            timeout=self.timeout
        )
        return self.driver
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleanup driver on context exit."""
        DriverManager.cleanup_driver(self.driver)
        self.driver = None
        return False  # Don't suppress exceptions