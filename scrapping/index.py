from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import itertools
from proxies.index import check_proxy
    
def scrape_all_pages(base_url: str, alive_proxies: list[str]) -> list[dict]:
    all_products = []
    page = 1
    ROTATE_EVERY = 1

    proxy_cycle = itertools.cycle(alive_proxies) if alive_proxies else None
    current_proxy = next(proxy_cycle) if proxy_cycle else None
    print('current_proxy::: ', current_proxy)
    
    driver = get_driver(proxy=current_proxy)

    try:                                          # ← wrappear en try/finally
        while True:
            # Rotar en página 5, 10, 15... (no en página 1)
            if page > 1 and page % ROTATE_EVERY == 0 and proxy_cycle:
                driver.quit()
                current_proxy = next(proxy_cycle)
                driver = get_driver(proxy=current_proxy)
                print(f"  Rotated to: {current_proxy}")

            url = f"{base_url}?page={page}" if page > 1 else base_url
            print(f'Scraping page {page} — {url}')

            driver.get(url)

            try:
                print("Downloading and executing js of DOM...")
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-cnstrc-item-price]"))
                )
            except Exception as e:
                print('Error waiting the driver::: ', e)
                break

            soup = BeautifulSoup(driver.page_source, 'lxml')

            unwanted = soup.select_one('.cmediaContainer')
            if unwanted:
                unwanted.decompose()

            products = soup.select('.shelf-content [data-cnstrc-item-price]')
            print(f'  Found {len(products)} products')

            if not products:
                break

            all_products.extend([
                {
                    "id":    p.get("data-cnstrc-item-id"),
                    "name":  p.get("data-cnstrc-item-name"),
                    "price": p.get("data-cnstrc-item-price"),
                }
                for p in products
            ])

            next_page = soup.select_one(f".seo-paginator-slides [aria-label='Página {page + 1}']")
            if not next_page:
                print('No more pages.')
                break

            if page == 10:                        # ← mover al final antes de page += 1
                print('Reached page limit.')
                break

            page += 1

    finally:
        driver.quit()                             # ← siempre se ejecuta, incluso con error

    return all_products


def get_driver(proxy: str = None) -> webdriver.Chrome:
    opts = webdriver.ChromeOptions()
    opts.add_argument("--headless")
    opts.add_argument("--disable-blink-features=AutomationControlled")

    if proxy:
        validated = get_proxy_or_direct(proxy)
        if validated:
            opts.add_argument(f"--proxy-server=http://{proxy}")
            print(f"  Driver using proxy: {proxy}")
        else:
            print(f"  Driver using direct IP")

    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=opts
    )

def get_proxy_or_direct(proxy: str) -> dict | None:
    result = check_proxy(proxy) #NOTE Segunda validacion en caso de que ya haya expirado el proxy
    
    if result:
        print(f"  Using proxy: {proxy}")
        return {"http": f"http://{proxy}", "https": f"http://{proxy}"}
    else:
        print(f"  Proxy dead — using direct IP")
        return None