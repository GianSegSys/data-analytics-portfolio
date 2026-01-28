from __future__ import annotations

import csv
import logging
import os
import time
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import List

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

###Modificar
###from .selenium_driver import SeleniumConfig, build_chrome_driver
###from .parsers import ProductRecord, Selectors, parse_product_card
from selenium_driver import SeleniumConfig, build_chrome_driver
from parsers import ProductRecord, Selectors, parse_product_card


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


def scrape_listing(
    start_url: str,
    selectors: Selectors,
    max_pages: int = 5,
    sleep_s: float = 1.0
) -> List[ProductRecord]:
    """
    Scrape products from a listing page, following pagination (next button).
    Adjust selectors.next_page_button for the website.
    """
    driver = build_chrome_driver(SeleniumConfig(headless=True))
    wait = WebDriverWait(driver, 20)

    results: List[ProductRecord] = []
    try:
        logger.info("Opening: %s", start_url)
        driver.get(start_url)

        for page in range(1, max_pages + 1):
            logger.info("Scraping page %d/%d", page, max_pages)

            # wait until at least one card appears
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selectors.product_card)))
            cards = driver.find_elements(By.CSS_SELECTOR, selectors.product_card)
            logger.info("Found %d product cards", len(cards))

            for card in cards:
                try:
                    ###record = parse_product_card(card, selectors)
                    record = parse_product_card(driver, card, selectors)
                    # Basic sanity: require URL or name; keep SKU always
                    if record.name or record.product_url:
                        results.append(record)
                except Exception as e:
                    logger.warning("Failed parsing a card: %s", e)

            if page == 0:
                logger.info("No next page button found. Stopping.")
                break

            # pagination
            next_btn = None
            try:
                next_btn = driver.find_element(By.CSS_SELECTOR, selectors.next_page_button)
            except Exception:
                next_btn = None

            if not next_btn:
                logger.info("No next page button found. Stopping.")
                break

            # click next and wait a moment
            try:
                driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
                time.sleep(0.2)
                next_btn.click()
                time.sleep(sleep_s)
            except Exception:
                logger.info("Pagination ended or failed to click next")
                break

        return results

    finally:
        try:
            driver.quit()
        except Exception:
            pass

def save_to_csv(records: List[ProductRecord], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["sku", "name", "price_list", "price_sale", "rating", "reviews_count", "product_url"]
        )
        writer.writeheader()
        for r in records:
            writer.writerow(asdict(r))


def main() -> None:
    # Configure your start URL
    start_url = os.getenv("SCRAPE_START_URL", "https://www.princessauto.com/en/category/Sale")

    selectors = Selectors(
        product_card="div.cc-product-card",

        # attributes on the card
        product_name=".cc-product-card-title .cc-text-overflow",
        product_id="@data-oe-item-id",

        # visible text
        product_sku=".cc-product-sku-container small span:nth-of-type(2)",

        # prices (attributes)
        product_sale_price="@data-oe-item-sale-price",
        product_list_price="@data-oe-item-list-price",

        # rating / reviews (Bazaarvoice)
        product_rating=".bv_averageRating_component_container .bv_text",
        product_reviews_count=".bv_numReviews_component_container .bv_text",

        # fallback source for aria-label
        bv_aria_source="a.bv_main_container",
    )

    max_pages = int(os.getenv("MAX_PAGES", "50"))

    records = scrape_listing(
        start_url=start_url,
        selectors=selectors,
        max_pages=max_pages,
        sleep_s=1.0,
    )
    logger.info("Total records scraped: %d", len(records))

    out = Path("data/raw") / f"products_raw_{date.today().isoformat()}.csv"
    save_to_csv(records, out)
    logger.info("Saved raw data to: %s", out)


if __name__ == "__main__":
    main()
