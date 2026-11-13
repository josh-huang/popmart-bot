import asyncio
import os

from dotenv import load_dotenv
from playwright.async_api import async_playwright
from telegram import Bot
from telegram.error import TelegramError

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

PRODUCT_URL = (
    "https://www.popmart.com/sg/products/7484/Happy-Halloween-Party-Series-Sitting-Pumpkin-Vinyl-Plush-Pendant"
)

#PRODUCT_URL = (
#    "https://www.popmart.com/sg/products/7039/THE-MONSTERS-Let's-Checkmate-Series-Vinyl-Plush-Doll"
#)
PRODUCT_ID = "7484"

notification_sent = False
_notification_in_flight = False


def as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


async def send_stock_alert(online_stock, lock_stock):
    message = (
        "Popmart restock alert: Halloween Plush Pendant back in stock.\n"
        f"Product: {PRODUCT_URL}"
    )

    try:
        async with Bot(token=TELEGRAM_BOT_TOKEN) as bot:
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        print("Telegram alert sent.")
        return True
    except TelegramError as exc:
        print(f"Failed to send Telegram alert: {exc}")
        return False


async def log_response(response):
    global notification_sent, _notification_in_flight

    url = response.url
    if "productDetails" not in url:
        return

    try:
        data = await response.json()
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

    if notification_sent or _notification_in_flight:
        return

    if online_stock > 0 or lock_stock > 0:
        _notification_in_flight = True
        try:
            notification_sent = await send_stock_alert(online_stock, lock_stock)
        finally:
            _notification_in_flight = False


async def main():
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID before starting the monitor.")
    while True:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            page.on("response", log_response)
            await page.goto(PRODUCT_URL)
            await page.wait_for_timeout(10000)
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
