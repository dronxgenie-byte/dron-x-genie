from playwright.sync_api import sync_playwright
import os
from datetime import datetime

# Создаём папку для скриншотов
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_dir = f"docs/RAZBOR/01_SCREENS/{timestamp}"
os.makedirs(output_dir, exist_ok=True)

print("🔐 Открываю браузер. ЗАЛОГИНЬСЯ ВРУЧНУЮ на dewiar.pro")
print("⏳ После входа нажми ENTER в этом терминале...")
input()  # Ждём, пока пользователь залогинится

# Список страниц для разбора (после авторизации)
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
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(viewport={"width": 1920, "height": 1080})
    page = context.new_page()
    
    # Переходим на главную (уже авторизованы)
    page.goto("https://dewiar.pro/", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(3000)
    
    for name, url in pages:
        print(f"📸 Разбираем: {name} → {url}")
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(2000)
            
            # Скриншот
            screenshot_path = f"{output_dir}/{name}.png"
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"   ✅ Скриншот: {screenshot_path}")
            
            # HTML
            html_path = f"{output_dir}/{name}.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(page.content())
            print(f"   ✅ HTML: {html_path}")
            
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
    
    browser.close()
    print(f"\n🎉 Готово! Все файлы в: {output_dir}")