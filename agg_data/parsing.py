import os
import re
import time
import random
from datetime import datetime
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

import pandas as pd
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

# ================= НАСТРОЙКИ =================
BASE_URL = ("https://www.dns-shop.ru/catalog/17a8a01d16404e77/smartfony/"
            "?stock=now-today-tomorrow-later&brand={}")

BRANDS = [
    "apple", "honor", "huawei", "poco", "realme", "samsung", "xiaomi", "google", "infinix", "iqoo", "motorola", "nothing", "oneplus", "oppo", "sharp", "sony", "tcl", "tecno", "vivo", "blackview", "cubot", "lava", "nubia", "oukitel", "unihertz", "kenshi", "rikor"
]
SEARCH_URLS = [BASE_URL.format(b) for b in BRANDS]


LINKS_FILE = "links.csv"
OUT_FILE = "dns_smartphones.csv"

MAX_PAGES = 30              # предохранитель для постраничного перехода (?p=2, ?p=3...)
MAX_NEW_PER_SEGMENT = 600   # предохранитель на один бренд
TRIM_DOM = True             # если число ссылок перестаёт расти раньше времени, поставьте False
NO_IMAGES = True            # без картинок меньше памяти и трафика
COLLECT_MORE = True         # True: дособрать ссылки по всем сегментам; False: взять links.csv как есть

SEL = {
    "card": "div.catalog-product",
    "link": "a.catalog-product__name",
    "price": "div.product-buy__price",
    "expand_btn": "button.product-characteristics__expand, a.product-characteristics__expand, "
                  "div.product-characteristics__expand",
    "group": "div.product-characteristics__group",
    "group_title": ".product-characteristics__group-title",
    "spec_title": "div.product-characteristics__spec-title",
    "spec_value": "div.product-characteristics__spec-value",
}

JS_HARVEST = """
const card = arguments[0], link = arguments[1], price = arguments[2];
return Array.from(document.querySelectorAll(card)).map(c => {
  const a = c.querySelector(link);
  const p = c.querySelector(price);
  return a ? {url: a.href, name: a.innerText.trim(), price: p ? p.innerText : ''} : null;
}).filter(Boolean);
"""

JS_TRIM = """
const cs = document.querySelectorAll(arguments[0]);
for (let i = 0; i < cs.length - 8; i++) cs[i].remove();
"""


# ================= ОБЩИЕ ФУНКЦИИ =================
def pause(a=3.0, b=7.0):
    time.sleep(random.uniform(a, b))


def make_driver():
    opts = uc.ChromeOptions()      # опции нельзя использовать повторно: создаём заново
    if NO_IMAGES:
        opts.add_argument("--blink-settings=imagesEnabled=false")
    return uc.Chrome(options=opts)


def wait_for(driver, css, timeout=45):
    end = time.time() + timeout
    while time.time() < end:
        if driver.find_elements(By.CSS_SELECTOR, css):
            return True
        time.sleep(1)
    return False


def open_page(driver, url, css, ask=False):
    driver.get(url)
    if wait_for(driver, css):
        return True
    if ask:
        input("Элемент не появился за 45 с. Нажмите F5 в окне браузера, "
              "дождитесь загрузки страницы и нажмите Enter...")
        return wait_for(driver, css, 30)
    return False


def parse_price(text):
    digits = re.sub(r"[^\d]", "", text.split("₽")[0])
    return int(digits) if digits else None


def with_page(url, n):
    u = urlparse(url)
    q = parse_qs(u.query)
    q["p"] = [str(n)]
    return urlunparse(u._replace(query=urlencode(q, doseq=True)))


def safe_quit(driver):
    try:
        driver.quit()
    except Exception:
        pass


# ================= ЭТАП 1: ССЫЛКИ =================
def save_links(items):
    pd.DataFrame(items.values()).to_csv(LINKS_FILE, index=False, encoding="utf-8-sig")


def scroll_segment(driver, url, items, first=False):
    """Открывает одну страницу выдачи и скроллит её, собирая карточки в items."""
    if not open_page(driver, url, SEL["card"], ask=first):
        print(f"Не удалось открыть {url}")
        return
    stagnant = 0
    added = 0
    while stagnant < 5 and added < MAX_NEW_PER_SEGMENT:
        for _ in range(4):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(1.0, 2.0))
        time.sleep(random.uniform(2.0, 3.5))

        data = driver.execute_script(JS_HARVEST, SEL["card"], SEL["link"], SEL["price"])
        new = 0
        for d in data:
            if d["url"] and d["url"] not in items:
                items[d["url"]] = {"name": d["name"], "url": d["url"],
                                   "price": parse_price(d["price"]) if d["price"] else None}
                new += 1
        added += new
        stagnant = stagnant + 1 if new == 0 else 0

        if TRIM_DOM:
            driver.execute_script(JS_TRIM, SEL["card"])

        save_links(items)
        print(f"  Всего ссылок: {len(items)} (+{new})")


def collect_links():
    """ГЛАВНЫЙ ЦИКЛ ПО СТАРТОВЫМ ССЫЛКАМ: каждый бренд = свой браузер."""
    items = {}
    if os.path.exists(LINKS_FILE):
        for r in pd.read_csv(LINKS_FILE).to_dict("records"):
            items[r["url"]] = r
        print(f"Уже есть ссылок: {len(items)}")

    for n, url in enumerate(SEARCH_URLS, 1):
        print(f"\n=== Сегмент {n}/{len(SEARCH_URLS)}: {url} ===")
        driver = make_driver()
        try:
            for page in range(1, MAX_PAGES + 1):
                page_url = url if page == 1 else with_page(url, page)
                before = len(items)
                scroll_segment(driver, page_url, items, first=(n == 1 and page == 1))
                if len(items) == before:    # новых ссылок нет: страницы кончились
                    break
        except Exception as e:
            print(f"Ошибка в сегменте {n}: {e}")
        finally:
            safe_quit(driver)
        time.sleep(5)

    save_links(items)
    print(f"\nСсылки сохранены в {LINKS_FILE}: {len(items)}")
    return pd.DataFrame(items.values())


# ================= ЭТАП 2: ХАРАКТЕРИСТИКИ =================
def expand_specs(driver):
    btns = driver.find_elements(By.CSS_SELECTOR, SEL["expand_btn"])
    if not btns:
        return
    btn = btns[0]
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
    time.sleep(random.uniform(0.5, 1.2))
    try:
        btn.click()
    except Exception:
        driver.execute_script("arguments[0].click();", btn)
    time.sleep(random.uniform(1.0, 2.0))


def get_specs(driver, url):
    if not open_page(driver, url, SEL["group"]):
        raise RuntimeError("страница товара не загрузилась")

    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_attempts, no_change_count = 0, 0
    while scroll_attempts < 15:
        driver.execute_script(
            f"window.scrollBy({{top: {random.randint(300, 700)}, behavior: 'smooth'}});")
        time.sleep(random.uniform(0.8, 1.8))

        if len(driver.find_elements(By.CSS_SELECTOR, SEL["group"])) >= 3:
            break

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            no_change_count += 1
            if no_change_count >= 2:
                driver.execute_script("window.scrollBy({top: -200, behavior: 'smooth'});")
                time.sleep(random.uniform(0.5, 1.0))
                driver.execute_script("window.scrollBy({top: 400, behavior: 'smooth'});")
                time.sleep(random.uniform(0.8, 1.5))
                no_change_count = 0
        else:
            last_height = new_height
            no_change_count = 0
        scroll_attempts += 1

    time.sleep(random.uniform(1.0, 2.0))
    expand_specs(driver)
    time.sleep(random.uniform(1.5, 2.5))

    specs = {}
    for group in driver.find_elements(By.CSS_SELECTOR, SEL["group"]):
        try:
            group_name = group.find_element(By.CSS_SELECTOR, SEL["group_title"]).text.strip()
        except Exception:
            group_name = ""
        for li in group.find_elements(By.CSS_SELECTOR, "ul li"):
            try:
                title = li.find_element(By.CSS_SELECTOR, SEL["spec_title"]).text.strip()
                value = li.find_element(By.CSS_SELECTOR, SEL["spec_value"]).text.strip()
            except Exception:
                continue
            if not title:
                continue
            key = title if title not in specs else f"{group_name} | {title}"
            specs[key] = value
    return specs


# ================= MAIN =================
def main():
    # ЭТАП 1: ссылки по всем стартовым URL
    if COLLECT_MORE or not os.path.exists(LINKS_FILE):
        links = collect_links()
    else:
        links = pd.read_csv(LINKS_FILE)
        print(f"Ссылки загружены из {LINKS_FILE}: {len(links)}")

    # ЭТАП 2: характеристики по каждой ссылке
    driver = make_driver()
    try:
        rows, done = [], set()
        if os.path.exists(OUT_FILE):
            old = pd.read_csv(OUT_FILE)
            rows = old.to_dict("records")
            done = set(old["url"])

        total = len(links)
        for i, item in enumerate(links.to_dict("records"), 1):
            if item["url"] in done:
                continue

            if i > 1 and (i - 1) % 5 == 0:      # лёгкая очистка
                try:
                    driver.execute_script("window.localStorage.clear(); window.sessionStorage.clear();")
                    driver.delete_all_cookies()
                except Exception:
                    pass

            if i > 1 and (i - 1) % 15 == 0:     # плановый перезапуск браузера
                print(f"\n[Система] Плановый перезапуск браузера (обработано {i-1})...")
                safe_quit(driver)
                time.sleep(3)
                driver = make_driver()

            specs, success = None, False
            for attempt in range(2):
                try:
                    pause(2.0, 5.0)
                    specs = get_specs(driver, item["url"])
                    success = True
                    break
                except Exception as e:
                    print(f"[{i}/{total}] Попытка {attempt+1} не удалась: {e}")
                    if attempt == 0:
                        print("[Система] Перезапуск браузера...")
                        safe_quit(driver)
                        time.sleep(5)
                        try:
                            driver = make_driver()
                        except Exception as err:
                            print(f"[Ошибка] Не удалось запустить браузер: {err}. Ждём 15 с...")
                            time.sleep(15)
                            driver = make_driver()

            if not success:
                print(f"[{i}/{total}] Пропуск товара: {item['url']}")
                continue

            rows.append({**item, **specs,
                         "scraped_at": datetime.now().isoformat(timespec="seconds")})
            print(f"[{i}/{total}] {item['name']} ({len(specs)} характеристик)")
            pd.DataFrame(rows).to_csv(OUT_FILE, index=False, encoding="utf-8-sig")
            pause(3.0, 7.0)

        print(f"Готово: {len(rows)} товаров -> {OUT_FILE}")
    finally:
        safe_quit(driver)


if __name__ == "__main__":
    main()