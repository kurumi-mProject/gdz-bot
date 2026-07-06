import asyncio, sqlite3
from aiogram import Bot

BOT_TOKEN = "8767995288:AAHdu_LqfY14dIu_95rkzjyNGAmJZTHXVcw"
DB = "/root/vpn_bot/vpn.db"

TEXT = """🔥 *Акция «Приведи друга» — сегодня и сейчас!*

Мы запускаем специальную акцию специально для вас:

👥 *Пригласи друга — получите оба по 1 месяцу VPN бесплатно!*

Как это работает:
1. Отправь другу свою реферальную ссылку (раздел 👥 Рефералы)
2. Друг переходит по ссылке и нажимает *«🚀 Начать»*
3. Вы оба мгновенно получаете *+30 дней* доступа

✨ Никаких условий — просто поделись ссылкой!

⏰ Акция действует прямо сейчас. Не упусти момент!"""

async def main():
    bot = Bot(token=BOT_TOKEN)
    conn = sqlite3.connect(DB)
    users = conn.execute("SELECT user_id FROM users").fetchall()
    conn.close()
    ok = fail = 0
    for (uid,) in users:
        try:
            await bot.send_message(uid, TEXT, parse_mode="Markdown")
            ok += 1
            await asyncio.sleep(0.05)
        except Exception:
            fail += 1
    print(f"Отправлено: {ok}, Ошибок: {fail}")
    await bot.session.close()

asyncio.run(main())
