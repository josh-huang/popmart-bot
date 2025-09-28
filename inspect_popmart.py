import os

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from telegram import Bot
from telegram.error import TelegramError

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8485166311:AAHOshRbMlbmIC6KTI_kEHCVtFrqZu-e9oc")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "1202430855")

if not TELEGRAM_CHAT_ID:
    raise RuntimeError(
        "TELEGRAM_CHAT_ID environment variable is required so the bot knows where to send alerts."
    )

PRODUCT_URL = (
    "https://www.popmart.com/sg/products/7484/Happy-Halloween-Party-Series-Sitting-Pumpkin-Vinyl-Plush-Pendant"
)

#PRODUCT_URL = (
#    "https://www.popmart.com/sg/products/7039/THE-MONSTERS-Let's-Checkmate-Series-Vinyl-Plush-Doll"
#)
PRODUCT_ID = "7484"

bot = Bot(token=TELEGRAM_BOT_TOKEN)
notification_sent = False


def as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def send_stock_alert(online_stock, lock_stock):
    message = (
        "Popmart restock alert: Halloween Plush Pendant back in stock.\n"
        f"Product: {PRODUCT_URL}"
    )

    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        print("Telegram alert sent.")
    except TelegramError as exc:
        print(f"Failed to send Telegram alert: {exc}")


def log_response(response):
    global notification_sent

    url = response.url
    if "productDetails" not in url:
        return

    try:
        data = response.json()
    except Exception as exc:
        print(f"Error parsing JSON from {url}: {exc}")
        return

    if data.get("code") != "OK":
        return

    product_data = data.get("data") or {}
    if str(product_data.get("id")) != PRODUCT_ID:
        return

    try:
        stock_info = product_data["skus"][0]["stock"]
    except (KeyError, IndexError, TypeError) as exc:
        print(f"Unexpected stock payload: {exc}")
        return

    online_stock = as_int(stock_info.get("onlineStock"))
    lock_stock = as_int(stock_info.get("onlineLockStock"))

    print("Stock info:", stock_info)

    if notification_sent:
        return

    if online_stock != 0 or lock_stock != 0:
        send_stock_alert(online_stock, lock_stock)
        notification_sent = True


def main():
    while True:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            page.on("response", log_response)
            page.goto(PRODUCT_URL)
            page.wait_for_timeout(10000)
            browser.close()


if __name__ == "__main__":
    main()
