from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from selenium.webdriver.remote.webdriver import WebDriver

def get_text_content(driver: WebDriver, el: WebElement) -> str:
    """Return full text including nested tags like <strong>."""
    try:
        txt = driver.execute_script("return arguments[0].textContent;", el)
        return (txt or "").strip()
    except Exception:
        return el.text.strip()


@dataclass
class ProductRecord:
    """
    Represents a single product scraped from a listing page.
    """
    sku: str
    name: str
    price_list: Optional[float]
    price_sale: Optional[float]
    rating: Optional[float]         # 0.0 – 5.0
    reviews_count: Optional[int]
    product_url: str

@dataclass(frozen=True)
class Selectors:
    """
    For fields you can extract from the card attributes, use:
      - "@attribute-name"  (e.g. "@data-oe-item-id")
    For fields you can extract from inside elements, use:
      - a CSS selector (e.g. ".cc-product-sale-price .cc-product-after-price")
    """
    # listing page
    product_card: str = "div.cc-product-card"

    # fields
    product_url: str = ""  # optional; can be derived later if needed

    # Name + ID available as attributes on the card
    ###product_name: str = "@data-oe-item-name"
    product_name: str = ".cc-product-card-title .cc-text-overflow"
    product_id: str = "@data-oe-item-id"

    # SKU is visible in a span (second span after "SKU:")
    product_sku: str = ".cc-product-sku-container small span:nth-of-type(2)"

    # Prices: prefer sale price attr if present, else list
    product_sale_price: str = "@data-oe-item-sale-price"
    product_list_price: str = "@data-oe-item-list-price"

    # Rating + reviews (Bazaarvoice)
    # first try numeric text
    product_rating: str = ".bv_averageRating_component_container .bv_text"     # e.g. "5.0"
    product_reviews_count: str = ".bv_numReviews_component_container .bv_text" # e.g. "(1)"

    # fallback: aria-label includes both rating and review count
    bv_aria_source: str = "a.bv_main_container"

    # pagination
    next_page_button: str = "span.cc-pagination-button.cc-next"


_money_re = re.compile(r"([-+]?\d[\d,]*\.?\d*)")
_int_re = re.compile(r"(\d+)")


def _safe_text(el: Optional[WebElement]) -> str:
    return el.text.strip() if el else ""


def _find_optional(parent: WebElement, by: By, selector: str) -> Optional[WebElement]:
    try:
        return parent.find_element(by, selector)
    except Exception:
        return None


def parse_price(text: str) -> Optional[float]:
    """
    Extract a numeric price from strings like "$1,299.99" or "CAD 24.50".
    """
    text = (text or "").strip()
    if not text:
        return None

    m = _money_re.search(text.replace("\u00a0", " "))
    if not m:
        return None

    raw = m.group(1).replace(",", "")
    try:
        return float(Decimal(raw))
    except (InvalidOperation, ValueError):
        return None


def parse_rating(text: str) -> Optional[float]:
    """
    Extract rating 0-5 with one decimal, e.g. "4.6 out of 5" or "4.6".
    """
    text = (text or "").strip()
    if not text:
        return None

    m = _money_re.search(text)  # reuse numeric regex
    if not m:
        return None

    try:
        val = float(Decimal(m.group(1)))
    except (InvalidOperation, ValueError):
        return None

    # clamp to 0..5
    if val < 0:
        val = 0.0
    if val > 5:
        val = 5.0
    return round(val, 1)


def parse_reviews_count(text: str) -> Optional[int]:
    """
    Extract integer from "(123 reviews)" or "123".
    """
    text = (text or "").strip()
    if not text:
        return None

    m = _int_re.search(text.replace(",", ""))
    if not m:
        return None

    try:
        return int(m.group(1))
    except ValueError:
        return None

def extract_value(card: WebElement, selector_or_attr: str) -> str:
    """
    If selector_or_attr starts with '@', read it as an attribute from the card.
    Otherwise treat it as a CSS selector and return the element text.
    """
    if not selector_or_attr:
        return ""

    if selector_or_attr.startswith("@"):
        attr_name = selector_or_attr[1:]
        return (card.get_attribute(attr_name) or "").strip()

    el = _find_optional(card, By.CSS_SELECTOR, selector_or_attr)
    return _safe_text(el)

""""
def parse_product_card(card: WebElement, selectors: Selectors) -> ProductRecord:
    name = extract_value(card, selectors.product_name)
    sku = extract_value(card, selectors.product_sku)

    sale_price_text = extract_value(card, selectors.product_sale_price)
    list_price_text = extract_value(card, selectors.product_list_price)

    price_list = parse_price(list_price_text) if list_price_text else None
    price_sale = parse_price(sale_price_text) if sale_price_text else None
    if price_sale is None:
        price_sale = price_list

    rating_text = extract_value(card, selectors.product_rating)
    reviews_text = extract_value(card, selectors.product_reviews_count)

    rating = parse_rating(rating_text)
    reviews_count = parse_reviews_count(reviews_text)

    if (rating is None or reviews_count is None) and selectors.bv_aria_source:
        a = _find_optional(card, By.CSS_SELECTOR, selectors.bv_aria_source)
        if a:
            aria = (a.get_attribute("aria-label") or "").strip()
            if rating is None:
                rating = parse_rating(aria)
            if reviews_count is None:
                reviews_count = parse_reviews_count(aria)

    # product_url optional: best effort via links
    product_url = ""
    try:
        links = card.find_elements(By.CSS_SELECTOR, "a[href]")
        for link in links:
            href = (link.get_attribute("href") or "").strip()
            if "/product/" in href:
                product_url = href
                break
    except Exception:
        pass

    if not sku:
        sku = "UNKNOWN"

    return ProductRecord(
        sku=sku,
        name=name,
        price_list=price_list,
        price_sale=price_sale,
        rating=rating,
        reviews_count=reviews_count,
        product_url=product_url,
    )
"""
def parse_product_card(driver: WebDriver, card: WebElement, selectors: Selectors) -> ProductRecord:
    name_el = _find_optional(card, By.CSS_SELECTOR, selectors.product_name)
    name = get_text_content(driver, name_el) if name_el else ""

    sku = extract_value(card, selectors.product_sku)

    sale_price_text = extract_value(card, selectors.product_sale_price)
    list_price_text = extract_value(card, selectors.product_list_price)

    price_list = parse_price(list_price_text) if list_price_text else None
    price_sale = parse_price(sale_price_text) if sale_price_text else None
    if price_sale is None:
        price_sale = price_list

    rating = parse_rating(extract_value(card, selectors.product_rating))
    reviews_count = parse_reviews_count(extract_value(card, selectors.product_reviews_count))
    ###rating_text = extract_value(card, selectors.product_rating)
    ###reviews_text = extract_value(card, selectors.product_reviews_count)
    ###rating = parse_rating(rating_text)
    ###reviews_count = parse_reviews_count(reviews_text)

    if rating is None or reviews_count is None:
        a = _find_optional(card, By.CSS_SELECTOR, selectors.bv_aria_source)
        if a:
            aria = (a.get_attribute("aria-label") or "").strip()
            rating = rating if rating is not None else parse_rating(aria)
            reviews_count = reviews_count if reviews_count is not None else parse_reviews_count(aria)

    ###if (rating is None or reviews_count is None) and selectors.bv_aria_source:
        ###a = _find_optional(card, By.CSS_SELECTOR, selectors.bv_aria_source)
        ###if a:
            ###aria = (a.get_attribute("aria-label") or "").strip()
            ###if rating is None:
                ###rating = parse_rating(aria)
            ###if reviews_count is None:
                ###reviews_count = parse_reviews_count(aria)

#############

    # product_url optional: best effort via links
    product_url = ""
    try:
        links = card.find_elements(By.CSS_SELECTOR, "a[href]")
        for link in links:
            href = (link.get_attribute("href") or "").strip()
            if "/product/" in href:
                product_url = href
                break
    except Exception:
        pass

    if not sku:
        sku = "UNKNOWN"

    return ProductRecord(
        sku=sku,
        name=name,
        price_list=price_list,
        price_sale=price_sale,
        rating=rating,
        reviews_count=reviews_count,
        product_url=product_url,
    )

