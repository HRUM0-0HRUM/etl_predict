import os
import re
import time
import random
from datetime import datetime

import pandas as pd
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

SEARCH_URL = (
    "https://www.dns-shop.ru/search/?q=%D1%81%D0%BC%D0%B0%D1%80%D1%82%D1%84%D0%BE%D0%BD"
    "&category=17a8a01d16404e77"
)
LINKS_FILE = "links.csv"
OUT_FILE = "dns_smartphones.csv"

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


def pause(a=3.0, b=7.0):
    time.sleep(random.uniform(a, b))


def wait_for(driver, css, timeout=45):
    """Ждём появления элемента. Пока идёт проверка Qrator, просто ждём:
    страница сама перезагрузится."""
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
    if ask:   # только для первой страницы: даём шанс обновить вручную
        input("Элемент не появился за 45 с. Нажмите F5 в окне браузере, "
              "дождитесь загрузки страницы и нажмите Enter...")
        return wait_for(driver, css, 30)
    return False


def parse_price(text):
    digits = re.sub(r"[^\d]", "", text.split("₽")[0])
    return int(digits) if digits else None


# ---------- ЭТАП 1: ссылки и цены ----------
def collect_links(driver):
    if not open_page(driver, SEARCH_URL, SEL["card"], ask=True):
        raise RuntimeError("Не удалось открыть выдачу")

    items = {}          # url -> данные (убирает дубли)
    stagnant = 0        # сколько скроллов подряд не появлялось новых карточек
    while stagnant < 5:
        # плавный скролл вниз, чтобы сработала подгрузка
        for _ in range(6):
            driver.execute_script("window.scrollBy(0, window.innerHeight * 1.2);")
            time.sleep(random.uniform(1.0, 2.0))


        time.sleep(random.uniform(2.5, 4.0))

        before = len(items)
        for card in driver.find_elements(By.CSS_SELECTOR, SEL["card"]):
            try:
                a = card.find_element(By.CSS_SELECTOR, SEL["link"])
                url = a.get_attribute("href")
                if not url or url in items:
                    continue
                try:
                    price = parse_price(card.find_element(By.CSS_SELECTOR, SEL["price"]).text)
                except Exception:
                    price = None
                items[url] = {"name": a.text.strip(), "url": url, "price": price}
            except Exception:
                continue

        if len(items) >= 700:
            print("Достигнут лимит в 700 ссылок. Остановка сбора.")
            break

        stagnant = stagnant + 1 if len(items) == before else 0
        print(f"Собрано ссылок: {len(items)}")

    df = pd.DataFrame(items.values())
    df.to_csv(LINKS_FILE, index=False, encoding="utf-8-sig")
    print(f"Ссылки сохранены в {LINKS_FILE}: {len(df)}")
    return df


# ---------- ЭТАП 2: характеристики ----------
def expand_specs(driver):
    """Нажимает кнопку «раскрыть все характеристики», если она есть."""
    btns = driver.find_elements(By.CSS_SELECTOR, SEL["expand_btn"])
    if not btns:
        return
    btn = btns[0]
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
    time.sleep(random.uniform(0.5, 1.2))
    try:
        btn.click()
    except Exception:
        driver.execute_script("arguments[0].click();", btn)   # если клик перекрыт
    time.sleep(random.uniform(1.0, 2.0))


def get_specs(driver, url):
    if not open_page(driver, url, SEL["group"]):
        raise RuntimeError("страница товара не загрузилась")

    

    # характеристики подгружаются при скролле
    for _ in range(5):
        driver.execute_script("window.scrollBy(0, window.innerHeight * 1.2);")
        time.sleep(random.uniform(1.0, 2.0))


    expand_specs(driver)

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
            # при совпадении названий в разных группах добавляем имя группы
            key = title if title not in specs else f"{group_name} | {title}"
            specs[key] = value
    return specs


def main():
    driver = uc.Chrome()      # окно видимое, headless не включать
    try:
        # этап 1 (если ссылки уже собраны, берём из файла)
        if os.path.exists(LINKS_FILE):
            links = pd.read_csv(LINKS_FILE)
            print(f"Ссылки загружены из {LINKS_FILE}: {len(links)}")
        else:
            links = collect_links(driver)

        # продолжение с места остановки
        done = set()
        rows = []
        if os.path.exists(OUT_FILE):
            old = pd.read_csv(OUT_FILE)
            rows = old.to_dict("records")
            done = set(old["url"])

        total = len(links)
        for i, item in enumerate(links.to_dict("records"), 1):
            if item["url"] in done:
                continue

            # 1. ЛЕГКАЯ ОЧИСТКА ПАМЯТИ каждые 5 товаров (без перезапуска, безопасно)
            if i > 1 and (i - 1) % 5 == 0:
                try:
                    driver.execute_script("window.localStorage.clear(); window.sessionStorage.clear();")
                    driver.delete_all_cookies()
                except Exception:
                    pass # Игнорируем ошибки очистки, если страница еще не до конца загружена

            # 2. ПОЛНЫЙ ПЕРЕЗАПУСК каждые 15 товаров (чаще, чем было)
            if i > 1 and (i - 1) % 15 == 0:
                print(f"\n[Система] Плановый перезапуск браузера (обработано {i-1} товаров)...")
                try:
                    driver.quit()
                except Exception:
                    pass
                time.sleep(3)
                driver = uc.Chrome()

            success = False

            # Делаем максимум 2 попытки: основная + одна резервная с перезапуском
            for attempt in range(2):
                try:
                    # ВАЖНО: Пауза ПЕРЕД открытием страницы сбивает простые анти-бот проверки
                    pause(2.0, 5.0) 
                    
                    specs = get_specs(driver, item["url"])
                    success = True
                    break  # Если успешно, выходим из цикла попыток
                    
                except Exception as e:
                    print(f"[{i}/{total}] Попытка {attempt+1} не удалась: {e}")
                    
                    if attempt == 0:
                        print("[Система] Попытка восстановления: перезапуск браузера...")
                        try:
                            driver.quit()
                        except Exception:
                            pass
                        
                        time.sleep(5)  # Даём системе "остыть"
                        
                        try:
                            driver = uc.Chrome()
                        except Exception as uc_err:
                            print(f"[Критическая ошибка] Не удалось запустить браузер: {uc_err}")
                            print("[Система] Ждём 15 секунд перед повторной инициализацией...")
                            time.sleep(15)
                            driver = uc.Chrome() # Последняя попытка поднять браузер
            
            # Если обе попытки провалились, просто пропускаем товар и идём дальше
            if not success:
                print(f"[{i}/{total}] ⚠️ Пропуск товара (не удалось загрузить после 2 попыток): {item['url']}")
                continue

            rows.append({**item, **specs,
                         "scraped_at": datetime.now().isoformat(timespec="seconds")})
            print(f"[{i}/{total}] {item['name']} ({len(specs)} характеристик)")
            
            pd.DataFrame(rows).to_csv(OUT_FILE, index=False, encoding="utf-8-sig")
            
            pause(3.0, 7.0)

        
        print(f"Готово: {len(rows)} товаров -> {OUT_FILE}")
    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    main()