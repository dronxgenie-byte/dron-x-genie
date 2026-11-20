from playwright.sync_api import sync_playwright
import os
from datetime import datetime

# Создаём папку для скриншотов
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_dir = f"docs/RAZBOR/01_SCREENS/{timestamp}"
os.makedirs(output_dir, exist_ok=True)

# Список страниц для разбора
pages = [
    ("dashboard", "https://dewiar.pro/"),
    ("calendar", "https://dewiar.pro/calendar"),
    ("tasks", "https://dewiar.pro/tasks"),
    ("family", "https://dewiar.pro/family"),
    ("health", "https://dewiar.pro/health"),
    ("investments", "https://dewiar.pro/investments"),
    ("letter", "https://dewiar.pro/letter"),
    ("settings", "https://dewiar.pro/settings"),
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # headless=False чтобы видеть процесс
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    
    for name, url in pages:
        print(f"📸 Разбираем: {name} → {url}")
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(2000)  # ждём загрузки
            
            # Скриншот
            screenshot_path = f"{output_dir}/{name}.png"
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"   ✅ Скриншот сохранён: {screenshot_path}")
            
            # HTML-структура
            html_path = f"{output_dir}/{name}.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(page.content())
            print(f"   ✅ HTML сохранён: {html_path}")
            
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
    
    browser.close()
    print(f"\n🎉 Готово! Все файлы в: {output_dir}")