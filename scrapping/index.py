from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
#from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, WebDriverException
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
import itertools
from proxies.index import check_proxy
import threading
import os
from datetime import datetime
import time
import undetected_chromedriver as uc
import random
import uuid

# TODO Save the errors in mongo
# TODO Send an email when a scraping fails with the error and the screenshots

class ScrapingCancelledError(Exception):
    pass

def scrape_all_pages(listObjs: list[dict], alive_proxies: list[str]) -> list[dict]:
    print('listObjs::: ', listObjs)
    all_supermarket_products = []
    cancel_event = threading.Event()

    with ThreadPoolExecutor(max_workers=len(listObjs)) as executor:
        futures = {
            executor.submit(thread_control, obj["url"], obj["supermarket"], alive_proxies, cancel_event): obj
            for obj in listObjs
        }

        for future in as_completed(futures):
            obj = futures[future]
            try:
                products = future.result()
                print(f"  ✓ {obj['supermarket']} → {len(products)} products")
                all_supermarket_products.extend(products)
            except ScrapingCancelledError:
                print(f"  ⚠ {obj['supermarket']} → cancelado por fallo en otro thread")
            except Exception as e:
                print(f"  ✗ {obj['supermarket']} → failed: {e}")
                cancel_event.set()  # 👈 cancela todos si hay error inesperado

    return all_supermarket_products


def thread_control(base_url: str, supermarket: str, alive_proxies: list[str], cancel_event: threading.Event) -> list[dict]:
    all_products = []
    if supermarket == 'lider':
        products = scrape_lider_supermarket(base_url, supermarket, alive_proxies, cancel_event)
        all_products.extend(products)
    else:
        products = scrape_page(base_url, supermarket, alive_proxies, cancel_event)
        all_products.extend(products)
    return all_products

def scrape_page(base_url: str, supermarket: str, alive_proxies: list[str], cancel_event: threading.Event) -> list[dict]:
    all_products = []
    page = 1
    ROTATE_EVERY = 1

    proxy_cycle = itertools.cycle(alive_proxies) if alive_proxies else None
    current_proxy = next(proxy_cycle) if proxy_cycle else None
    
    driver = get_driver(proxy=current_proxy)

    try:                                          # ← wrappear en try/finally
        while True:
            if page > 1 and page % ROTATE_EVERY == 0 and proxy_cycle:
                driver.quit()
                current_proxy = next(proxy_cycle)
                driver = get_driver(proxy=current_proxy)
                print(f"  Rotated to: {current_proxy}")

            if cancel_event.is_set():
                print(f"  ⚠ {supermarket} — cancelado, saliendo...")
                raise ScrapingCancelledError(f"Cancelado por fallo en otro scraper")

            url = f"{base_url}?page={page}" if page > 1 else base_url
            print(f'Scraping page {page} — {url}')

            driver.get(url)

            try:
                WebDriverWait(driver, 20).until(
                    EC.invisibility_of_element_located((By.CSS_SELECTOR, ".shelf-content-skeleton"))
                )

                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-cnstrc-item-price]"))
                )
            except TimeoutException:
                cancel_event.set()

                os.makedirs("error", exist_ok=True)
                driver.save_screenshot(os.path.join("error", f"error_page_{page}.png"))
                with open(os.path.join("error", f"error_page_{page}.html"), "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                print(f'  Timeout on page {page} — title: {driver.title}')
                break

            except WebDriverException as e:
                cancel_event.set()

                print(f'  WebDriver error: {e.msg}')  # .msg es más limpio que el stacktrace completo
                break

            soup = BeautifulSoup(driver.page_source, 'lxml')

            unwanted = soup.select_one('.cmediaContainer')
            if unwanted:
                unwanted.decompose()

            products = soup.select('.shelf-content [data-cnstrc-item-price]')
            print('producs searched::: ', len(products))

            if not products:
                os.makedirs("log", exist_ok=True)
                driver.save_screenshot(os.path.join("log", f"no_products_page_{page}.png"))
                break

            all_products.extend([
                {
                    "id":    p.get("data-cnstrc-item-id"),
                    "name":  p.get("data-cnstrc-item-name"),
                    "price": p.get("data-cnstrc-item-price"),
                    "supermarket": supermarket,
                    "date": datetime.now().isoformat()
                }
                for p in products
            ])

            next_page = soup.select_one(f".seo-paginator-slides [aria-label='Página {page + 1}']")
            print("---------------------")
            print(supermarket, 'next_page:::', next_page)
            print("---------------------")
            
            if not next_page:
                os.makedirs("log", exist_ok=True)
                driver.save_screenshot(os.path.join("log", f"no_more_pages_page{page}.png"))
                print('No more pages.')
                break

            if page == 2:                        # ← mover al final antes de page += 1
                print('Reached page limit.')
                break

            page += 1
    finally:
        driver.quit()                             # ← siempre se ejecuta, incluso con error

    return all_products


def scrape_lider_supermarket(base_url: str, supermarket: str, alive_proxies: list[str], cancel_event: threading.Event) -> list[dict]:
    all_products = []
    page = 1
    ROTATE_EVERY = 1

    proxy_cycle = itertools.cycle(alive_proxies) if alive_proxies else None
    current_proxy = next(proxy_cycle) if proxy_cycle else None
    
    driver = get_driver_lider(proxy=current_proxy)

    try:
        while True:
            if page > 1 and page % ROTATE_EVERY == 0 and proxy_cycle:
                driver.quit()
                current_proxy = next(proxy_cycle)
                driver = get_driver_lider(proxy=current_proxy)
                print(f"  Rotated to: {current_proxy}")

            if cancel_event.is_set():
                print(f"  ⚠ {supermarket} — cancoelad, saliendo...")
                raise ScrapingCancelledError(f"Cancelado por fallo en otro scraper")

            # NOTE main page of lider
            driver.get(base_url)
            time.sleep(random.uniform(3, 7))

            try:
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='HubSpokesNxM']")) #FIXME Esto se va a caer
                )
            except TimeoutException:
                print(f'  Timeout on page {page} — title: {driver.title}')
                cancel_event.set()

                os.makedirs("error", exist_ok=True)
                driver.save_screenshot(os.path.join("error", f"error_page_{page}.png"))
                with open(os.path.join("error", f"error_page_{page}.html"), "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                
                break
            except WebDriverException as e:
                cancel_event.set()

                print(f'  WebDriver error: {e.msg}')  # .msg es más limpio que el stacktrace completo
                break

            soup = BeautifulSoup(driver.page_source, 'lxml')

            containerCategories = soup.select("[data-testid='HubSpokesNxM']")
            print('containerCategories searched::: ', len(containerCategories))
            
            if not containerCategories:
                print('  No containerCategories found.')
                break

            target_link = None
            for container in containerCategories:
                target_link = container.select_one("a[link-identifier='Boton despensa_cate_2026.png']")
                if target_link:
                    break

            if target_link:
                target_url = base_url + target_link.get('href')
                print(f'  Target <a> URL: {target_url}')

                if not target_url:
                    raise Exception("Target URL not found in the link")
                
                time.sleep(random.uniform(2, 8))
                driver.get(target_url)
                time.sleep(random.uniform(1, 3))

                try:
                    WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[link-identifier]"))
                    )
                except TimeoutException:
                    print(f'  Timeout waiting for link-identifier property on page — title: {driver.title}')
                    cancel_event.set()

                    break
                except WebDriverException as e:
                    cancel_event.set()

                    print(f'  WebDriver error: {e.msg}')  # .msg es más limpio que el stacktrace completo
                    break

                soup = BeautifulSoup(driver.page_source, 'lxml')
                print('Page loaded, searching for categories...')

                titles = soup.select("h2")
                allLinks = None
                for h2 in titles:
                    print('h2 found::: ', h2.get_text())
                    if "Para cocinar y disfrutar" in h2.get_text():
                        parent = h2.find_parent("div")
                        if not parent:
                            print('  Parent not found for h2, skipping...')
                            break
                        
                        grandpa = parent.find_parent("section")
                        if not grandpa:
                            print('  Grandparent not found for h2, skipping...')
                            break
                        
                        htmlAllLinks = grandpa.select("a")
                        if not htmlAllLinks:
                            print('  No <a> found in grandparent, skipping...')
                            break
                        
                        allLinks = [base_url + a.get('href') for a in htmlAllLinks if a.get('href')]
                        print('Links found::: ', allLinks)
                        break

                if allLinks:
                    print(f'  Total categories found: {len(allLinks)}')
                    
                    for i, link in enumerate(allLinks):
                        pageProduct = 1
                        print(f'  [{i+1}/{len(allLinks)}] Scraping: {link}')

                        while True:
                            # TODO Add proxypool
                            if cancel_event.is_set():
                                print(f"  ⚠ {supermarket} — cancelado, saliendo...")
                                raise ScrapingCancelledError(f"Cancelado por fallo en otro scraper")

                            url = f"{link}&page={pageProduct}"
                            print(f'Scraping page {pageProduct} — {url}')

                            time.sleep(random.uniform(2, 10))
                            driver.get(url)

                            try:
                                WebDriverWait(driver, 20).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, "[link-identifier]"))
                                )
                            except TimeoutException:
                                cancel_event.set()
                                print(f'  Timeout on page {pageProduct} — title: {driver.title}')
                                break
                            except WebDriverException as e:
                                cancel_event.set()
                                print(f'  WebDriver error: {e.msg}')  # .msg es más limpio que el stacktrace completo
                                break

                            soup = BeautifulSoup(driver.page_source, 'lxml')

                            containerProducts = soup.select('[data-testid="item-stack"]')

                            if not containerProducts:
                                print('Container not founded, skipping to next category...')
                                break

                            products = soup.select("div")
                            print('products searched::: ', products)


                            // TODO END THIS
                            all_products.extend([
                                {
                                    "id": str(uuid.uuid4()),
                                    "name": p.get('[data-automation-id="product-title"]'),
                                    "price": p.select_one('[data-automation-id="product-price"] div').get_text(strip=True) if p.select_one('[data-automation-id="product-price"] div') else 0,
                                    "supermarket": "Lider",
                                    "date": datetime.now().isoformat()
                                }
                                for p in products
                            ])

                            next_page = soup.select_one(f'[data-automation-id="page-number"]')
                            print("---------------------")
                            print(supermarket, 'next_page:::', next_page)
                            print("---------------------")
                            
                            if not next_page:
                                print('No more pages in this category.')
                                break

                            if page == 2:                       # ← mover al final antes de page += 1
                                print('Reached page limit.')
                                break

                            page += 1

                        # delay aleatorio entre categorías
                        delay = random.uniform(4, 9)
                        print(f'  Waiting {delay:.1f}s before next category...')
                        time.sleep(delay)
                break
            else:
                print('  Target <a> not found')
                break
    finally:
        driver.quit()                             # ← siempre se ejecuta, incluso con error

    return all_products

def get_driver(proxy: str = None) -> webdriver.Chrome:
    opts = webdriver.ChromeOptions()

    opts.add_argument("--headless=new")  # use new headless mode
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.binary_location = "/usr/bin/chromium" #Docker

    opts.add_argument("--disable-gpu")
    opts.add_argument("--lang=es-CL")
    opts.add_argument("--disable-extensions")
    # Simular pantalla real
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--start-maximized")

    if proxy:
        validated = get_proxy_or_direct(proxy)
        if validated:
            opts.add_argument(f"--proxy-server=http://{proxy}")
            print(f"  Driver using proxy: {proxy}")
        else:
            print(f"  Driver using direct IP")

    driver = webdriver.Chrome(
        #service=Service(ChromeDriverManager().install()), options=opts
        service=Service("/usr/bin/chromedriver"), options=opts #Docker
    )

    # Patch navigator.webdriver via CDP — this is the key step
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {}, loadTimes: () => {}, csi: () => {}, app: {} };
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['es-CL', 'es'] });
            Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
            Object.defineProperty(screen, 'colorDepth', { get: () => 24 });
        """
    })

    return driver

def get_driver_lider(proxy: str = None) -> uc.Chrome:
    opts = uc.ChromeOptions()

    #opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--lang=es-CL")

    if proxy:
        validated = get_proxy_or_direct(proxy)
        if validated:
            opts.add_argument(f"--proxy-server=http://{proxy}")

    driver = uc.Chrome(
        options=opts,
        driver_executable_path="/usr/bin/chromedriver",  # Docker
        browser_executable_path="/usr/bin/chromium",     # Docker
    )

    return driver

def get_proxy_or_direct(proxy: str) -> dict | None:
    result = check_proxy(proxy) #NOTE Segunda validacion en caso de que ya haya expirado el proxy
    
    if result:
        print(f"  Using proxy: {proxy}")
        return {"http": f"http://{proxy}", "https": f"http://{proxy}"}
    else:
        print(f"  Proxy dead — using direct IP")
        return None
    
