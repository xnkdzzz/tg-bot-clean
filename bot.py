import os
import json
import time
import requests
import telebot
from bs4 import BeautifulSoup
from threading import Thread
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# === НАСТРОЙКИ ===
BOT_TOKEN = "8591671306:AAEcPay5f5o9U-78iR1BBXhZVhf_2SQS2Dk"
KRISHA_URL = "https://krisha.kz/prodazha/doma-dachi/zharkent/?bounds=&lat=44.21512&lon=80.21276&areas=p44.202342,80.192335,44.203823,80.186842,44.208516,80.181864,44.218887,80.179632,44.228268,80.187872,44.236167,80.200918,44.237772,80.208643,44.236414,80.221518,44.219627,80.243490,44.212714,80.245894,44.208145,80.243147,44.198266,80.232161,44.193820,80.221003,44.192462,80.208986,44.193697,80.197313,44.198390,80.189417,44.203823,80.186499,44.202342,80.192335&zoom=13"  # продаются дома в Жаркенте
USER_AGENT = "Mozilla/5.0 (compatible; KrishaNotifier/1.0; +https://github.com/)"
SEEN_FILE = "seen.json"
CHECK_INTERVAL = 300  # проверка каждые 5 минут

bot = telebot.TeleBot(BOT_TOKEN)
active_users = set()

# === ФАЙЛ С ИСТОРИЕЙ ===
def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            try:
                return set(json.load(f))
            except json.JSONDecodeError:
                return set()
    return set()

def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen), f, ensure_ascii=False, indent=2)

# === ПАРСЕР ===
def fetch_html(url):
    r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
    r.raise_for_status()
    return r.text

def parse_krisha(html):
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("div.a-card")  # карточки объявлений
    ads = []
    for card in cards:
        link_tag = card.find("a", href=True)
        title = card.select_one(".a-card__title")
        price = card.select_one(".a-card__price")
        address = card.select_one(".a-card__subtitle")

        if not link_tag:
            continue

        url = "https://krisha.kz" + link_tag["href"]
        uid = link_tag["href"]
        title_text = title.get_text(strip=True) if title else "Без названия"
        price_text = price.get_text(strip=True) if price else "Цена не указана"
        address_text = address.get_text(strip=True) if address else "Адрес не указан"

        ads.append({
            "id": uid,
            "title": title_text,
            "price": price_text,
            "address": address_text,
            "url": url
        })
    return ads

# === ОТПРАВКА СООБЩЕНИЙ ===
def send_ad(user_id, ad):
    text = (
        f"🆕 {ad['title']}\n"
        f"📍 {ad['address']}\n"
        f"💰 {ad['price']}\n"
        f"🔗 Открыть объявление\n{ad['url']}"
    )
    bot.send_message(user_id, text)

# === ПРОВЕРКА НОВЫХ ===
def check_new_ads():
    seen = load_seen()
    while True:
        try:
            html = fetch_html(KRISHA_URL)
            ads = parse_krisha(html)
            new_ads = [ad for ad in ads if ad["id"] not in seen]
            if new_ads:
                for ad in new_ads:
                    seen.add(ad["id"])
                    for user in active_users:
                        send_ad(user, ad)
                save_seen(seen)
        except Exception as e:
            print("Ошибка при проверке объявлений:", e)
        time.sleep(CHECK_INTERVAL)

# === КНОПКИ ===
def main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("▶️ Старт"), KeyboardButton("⛔ Стоп"))
    return markup

# === КОМАНДЫ ===
@bot.message_handler(commands=["start"])
def start_command(message):
    user_id = message.chat.id
    active_users.add(user_id)
    bot.send_message(
        user_id,
        "✅ Уведомления включены! Показываю текущие объявления о продаже домов:",
        reply_markup=main_menu()
    )

    html = fetch_html(KRISHA_URL)
    ads = parse_krisha(html)
    seen = load_seen()

    if not ads:
        bot.send_message(user_id, "⚠️ Объявления не найдены. Возможно, сайт временно недоступен.")
        return

    for ad in ads[:10]:  # первые 10, чтобы не спамить
        seen.add(ad["id"])
        send_ad(user_id, ad)
    save_seen(seen)

@bot.message_handler(func=lambda msg: msg.text == "▶️ Старт")
def handle_start_button(message):
    start_command(message)

@bot.message_handler(func=lambda msg: msg.text == "⛔ Стоп")
def handle_stop_button(message):
    user_id = message.chat.id
    if user_id in active_users:
        active_users.remove(user_id)
    bot.send_message(user_id, "❌ Уведомления остановлены.", reply_markup=main_menu())

@bot.message_handler(commands=["stop"])
def stop_command(message):
    handle_stop_button(message)

# === ЗАПУСК ===
if __name__ == "__main__":
    print("🚀 Бот запущен и отслеживает объявления...")
    Thread(target=check_new_ads, daemon=True).start()
    bot.infinity_polling()