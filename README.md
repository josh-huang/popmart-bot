# Popmart stock monitor

Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in your environment or a local
`.env` file (see `.env.example`). Never commit the populated file. Previously
committed credentials should be revoked and replaced; removing a source-code
default does not remove it from Git history.

Install `python-dotenv`, `playwright`, and `python-telegram-bot~=22.5`, then run
`python -m playwright install chromium` and `python inspect_popmart.py`.

The monitor uses the async Playwright and Telegram APIs. A positive stock response
triggers one notification; failed delivery is retried on a later response.
Overlapping responses share the same in-flight delivery, preventing duplicates.

Run the offline tests with `python -m unittest discover -s tests -v`.
