"""
    Chilean Supermarket Scraping to compare prices.
"""

from proxies.index import main 
from scrapping.index import scrape_all_pages

BASE_URL = "https://www.jumbo.cl/despensa"
HEADERS  = {"User-Agent": "Mozilla/5.0 (compatible; HN-Scraper/1.0)"}

# Crating the file with proxies
valid_proxies = main()
print("valid_proxies::: ", valid_proxies)

products = scrape_all_pages(BASE_URL, valid_proxies)
print("products::: ", products)


