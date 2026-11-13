import asyncio
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import inspect_popmart as monitor
from telegram.error import TelegramError


class AlertTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        monitor.notification_sent = False
        monitor._notification_in_flight = False

    def response(self, online=2, locked=0):
        return SimpleNamespace(
            url="https://example.invalid/productDetails",
            json=AsyncMock(return_value={
                "code": "OK",
                "data": {"id": monitor.PRODUCT_ID, "skus": [{"stock": {
                    "onlineStock": online, "onlineLockStock": locked,
                }}]},
            }),
        )

    async def test_send_waits_for_sdk_and_closes_client(self):
        bot = MagicMock()
        bot.send_message = AsyncMock()
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=bot)
        context.__aexit__ = AsyncMock(return_value=False)
        with patch.object(monitor, "Bot", return_value=context):
            self.assertTrue(await monitor.send_stock_alert(2, 0))
        bot.send_message.assert_awaited_once()
        context.__aexit__.assert_awaited_once()

    async def test_failed_delivery_is_retried_on_next_response(self):
        with patch.object(monitor, "send_stock_alert", AsyncMock(side_effect=[False, True])) as send:
            await monitor.log_response(self.response())
            self.assertFalse(monitor.notification_sent)
            await monitor.log_response(self.response())
            self.assertTrue(monitor.notification_sent)
            self.assertEqual(send.await_count, 2)

    async def test_simultaneous_responses_send_once(self):
        started, finish = asyncio.Event(), asyncio.Event()

        async def deliver(*_args):
            started.set()
            await finish.wait()
            return True

        with patch.object(monitor, "send_stock_alert", AsyncMock(side_effect=deliver)) as send:
            first = asyncio.create_task(monitor.log_response(self.response()))
            await started.wait()
            await monitor.log_response(self.response())
            finish.set()
            await first
            await monitor.log_response(self.response())
            send.assert_awaited_once()

    async def test_missing_invalid_and_zero_stock_do_not_alert(self):
        with patch.object(monitor, "send_stock_alert", AsyncMock()) as send:
            for stock in (None, "unknown", 0, "0", -1):
                await monitor.log_response(self.response(online=stock))
            send.assert_not_awaited()

    async def test_telegram_error_is_a_failed_delivery(self):
        context = MagicMock()
        context.__aenter__ = AsyncMock(side_effect=TelegramError("temporary failure"))
        with patch.object(monitor, "Bot", return_value=context):
            self.assertFalse(await monitor.send_stock_alert(2, 0))

    async def test_missing_configuration_fails_before_opening_browser(self):
        with patch.object(monitor, "TELEGRAM_BOT_TOKEN", ""), patch.object(monitor, "async_playwright") as browser:
            with self.assertRaisesRegex(RuntimeError, "TELEGRAM_BOT_TOKEN"):
                await monitor.main()
            browser.assert_not_called()


if __name__ == "__main__":
    unittest.main()
