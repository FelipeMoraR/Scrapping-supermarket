"""
    Chilean Supermarket Scraping to compare prices.
"""

from proxies.index import main 
from scrapping.index import scrape_all_pages
import csv
import os

URL_JUMBO = "https://www.jumbo.cl/despensa"
URL_SANTAISABEL = "https://www.santaisabel.cl/despensa"
HEADERS  = {"User-Agent": "Mozilla/5.0 (compatible; HN-Scraper/1.0)"}

# NOTE Crating the file with proxies
#valid_proxies = main()
#print("valid_proxies::: ", valid_proxies)

import csv
import os
from datetime import datetime

def save_to_csv(products: list[dict], filename: str = None) -> None:
    if not products:
        print("No products to save.")
        return

    os.makedirs("output", exist_ok=True)

    # Nombre con timestamp para no sobreescribir
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"output/products_{timestamp}.csv"

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "name", "price", "supermarket"])
        writer.writeheader()
        writer.writerows(products)

    print(f"  CSV saved → {filename} ({len(products)} products)")

try:
    products = scrape_all_pages([{ 'url': URL_JUMBO, 'supermarket': 'jumbo' }, { 'url': URL_SANTAISABEL, 'supermarket': 'sabta-isabel' }], [])
    print('Products::: ', products)

    save_to_csv(products)
except Exception as e:
    print('BROTHER THIS SHIET EXPLOTED::: ', e)



