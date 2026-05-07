from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import requests
import os

# TODO validate how much time spend to request a proxy to avoid the slowest ones

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
RESOURCES  = os.path.join(BASE_DIR, '..', 'resources')

PROXY_FILE        = os.path.join(RESOURCES, 'potentialProxyServer.txt')
VALID_PROXIES_FILE = os.path.join(RESOURCES, 'validProxies.txt')

def parsing_proxies() -> list[int]:
    pool_proxys = []
    
    with open(PROXY_FILE, 'r') as f:
        proxies = f.read().split("\n")
        for p in proxies:
            pool_proxys.append(p)

    return pool_proxys


def check_proxy(proxy: str) -> str | None:
    try:
        response = requests.get(
            "https://ipinfo.io/json",  # test endpoint that returns your IP
            proxies={"http": f"http://{proxy}", "https": f"http://{proxy}"},
            timeout=5
        )
        if response.status_code == 200:
            print(f"  ✓ valid: {proxy}")
            return proxy
    except Exception as e:
        print(f"  ✗ failed: {proxy}, error: {e}")
        return None

def check_proxies(pool) -> list[str]:
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(check_proxy, pool)

    return [r for r in results if r is not None]


def save_valid_proxies(valid_proxies: list[str]) -> None:
    # Load existing proxies if file exists (avoid duplicates)
    existing = set()
    

    if os.path.exists(VALID_PROXIES_FILE):
        with open(VALID_PROXIES_FILE, 'r') as f:
            existing = set(line.strip() for line in f if line.strip())

    # Only add new ones
    new_proxies = [p for p in valid_proxies if p not in existing]

    if not new_proxies:
        print("No new proxies to add.")
        return

    # 'a' = append mode — creates file if doesn't exist, extends if it does
    with open(VALID_PROXIES_FILE, 'a') as f:
        for proxy in new_proxies:
            f.write(proxy + "\n")

    print(f"Added {len(new_proxies)} new proxies ({len(existing)} already existed)")



def main():
    try:
        pool = parsing_proxies()
        valid_proxies = check_proxies(pool)
        return valid_proxies
    except Exception as e:
        print('Problem:: ', e)
        return []
