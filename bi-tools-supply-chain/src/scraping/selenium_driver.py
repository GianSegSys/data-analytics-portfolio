from __future__ import annotations

import os
from dataclasses import dataclass
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service


@dataclass(frozen=True)
class SeleniumConfig:
    headless: bool = True
    window_size: str = "1920,1080"
    page_load_timeout: int = 30
    implicit_wait: int = 0  # prefer explicit waits
    chrome_binary: str | None = None  # optional
    driver_path: str | None = None    # optional, if chromedriver not in PATH


def build_chrome_driver(config: SeleniumConfig) -> webdriver.Chrome:
    """
    Create a Chrome WebDriver with sensible defaults for scraping.
    - Headless is enabled by default
    - Disables some automation flags
    - Configurable driver path / chrome binary via config or env vars

    Env vars (optional):
      - CHROME_BINARY
      - CHROMEDRIVER_PATH
      - SELENIUM_HEADLESS=true/false
    """
    headless_env = os.getenv("SELENIUM_HEADLESS")
    headless = config.headless if headless_env is None else headless_env.lower() in ("1", "true", "yes")

    chrome_binary = config.chrome_binary or os.getenv("CHROME_BINARY")
    driver_path = config.driver_path or os.getenv("CHROMEDRIVER_PATH")

    options = Options()
    if headless:
        # new headless mode for recent Chrome
        options.add_argument("--headless=new")
    options.add_argument(f"--window-size={config.window_size}")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--lang=en-US")

    options.add_argument("--log-level=3")
    options.add_argument("--silent")
    options.add_argument("--disable-logging")
    options.add_argument("--v=0")

    # reduce "automation" fingerprints a bit (not a guarantee)
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    if chrome_binary:
        options.binary_location = chrome_binary

    ###service = Service(executable_path=driver_path) if driver_path else Service()
    service = Service(executable_path=driver_path, log_output=os.devnull) if driver_path else Service(log_output=os.devnull)


    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(config.page_load_timeout)
    if config.implicit_wait:
        driver.implicitly_wait(config.implicit_wait)

    return driver
