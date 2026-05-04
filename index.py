"""
    Chilean Supermarket Scraping to compare prices.
"""
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

#NOTE - This will be a test with only one page
#TODO - We have to scrap more than 1 page
BASE_URL = "https://www.jumbo.cl/despensa"
HEADERS  = {"User-Agent": "Mozilla/5.0 (compatible; HN-Scraper/1.0)"}

def scrape_spa(url: str) -> list[dict]:
    opts = webdriver.ChromeOptions()
    opts.add_argument("--headless")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=opts
    )

    try:
        print('Starting the scrapping')

        responseDrive = driver.get(url)

        # Wait until a key element appears (JS has finished rendering)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-cnstrc-item-price]")) #NOTE - This just confirms the element exists before timing out
        )
        # NOW pass the rendered HTML to BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'lxml') #NOTE Extract the data

        # Remove #hola from the tree before selecting
        unwanted = soup.select_one('.cmediaContainer')
        print('got sha:::', unwanted)

        if unwanted:
            unwanted.decompose()  # deletes it from the soup entirely

        products = soup.select('.shelf-content [data-cnstrc-item-price]')

        print('num of products:: ', len(products))  # how many matched

        for product in products:
            print({
                "id":    product.get("data-cnstrc-item-id"),
                "name":  product.get("data-cnstrc-item-name"),
                "price": product.get("data-cnstrc-item-price"),
            })

        return True
    except error:
        print('Problems scrapping::: ', error)
    finally:
        driver.quit()

scrape_spa(BASE_URL)

