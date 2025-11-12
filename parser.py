import requests
from bs4 import BeautifulSoup

# Получить актуальные объявления аренды квартир посуточно в Астане с Krisha.kz
def fetch_latest_announcements():
    url = "https://krisha.kz/arenda/kvartiry/astana/?das[live.furniture]=1&rent-period=2"  # примерная ссылка на посуточно
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    announcements = []
    for item in soup.select(".a-search-list .a-search-item"):
        title = item.select_one(".a-search-item__title")
        price = item.select_one(".a-search-item__price")
        link = item.select_one("a.a-search-item__link")
        address = item.select_one(".a-search-item__subtitle")
        if title and price and link:
            announcements.append(
                f"🏠 <b>{title.text.strip()}</b>\n"
                f"💵 {price.text.strip()}\n"
                f"{address.text.strip() if address else ''}\n"
                f"https://krisha.kz{link['href']}"
            )
    return announcements