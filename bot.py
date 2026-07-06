import asyncio
import re
import io
import logging
from PIL import Image, ImageDraw, ImageFont
from playwright.async_api import async_playwright
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder

BOT_TOKEN = "8234414620:AAHkd-i_X1__CZWWnIFNGVDyI02SbjaNLHY"
GDZ_BASE = "https://gdz.ru"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


class S(StatesGroup):
    choosing = State()


def parse_query(text: str):
    m = re.search(r"([а-яёА-ЯЁ ]+?)\s+(\d+)\s+класс\s+(\d+)\s+упр", text, re.I)
    if m:
        return m.group(1).strip(), m.group(2), m.group(3)
    return None


async def google_gdz_url(subject: str, grade: str, page) -> str | None:
    query = f"gdz.ru {subject} {grade} класс"
    # DuckDuckGo не блокирует headless
    await page.goto(
        f"https://duckduckgo.com/html/?q={query.replace(' ', '+')}",
        wait_until="domcontentloaded", timeout=30000
    )
    links = await page.query_selector_all("a[href]")
    for l in links:
        href = await l.get_attribute("href") or ""
        m = re.search(r'https?://gdz\.ru/[^&"\s]+', href)
        if m:
            return m.group(0).rstrip("/") + "/"
    return None


async def get_books(gdz_url: str, page) -> list:
    await page.goto(gdz_url, wait_until="domcontentloaded", timeout=30000)
    books = []
    seen = set()
    links = await page.query_selector_all("a")
    for l in links:
        href = await l.get_attribute("href") or ""
        if not href.startswith("http"):
            href = GDZ_BASE + href if href.startswith("/") else ""
        if not href or href in seen or "gdz.ru" not in href:
            continue
        if href.count("/") < 5:
            continue
        seen.add(href)
        img_el = await l.query_selector("img")
        if not img_el:
            continue
        img_src = await img_el.get_attribute("src") or ""
        if not img_src.startswith("http"):
            img_src = GDZ_BASE + img_src
        title_el = await l.query_selector("span, div, p")
        title = (await title_el.inner_text()).strip() if title_el else ""
        books.append({"title": title or href.split("/")[-2], "href": href, "img": img_src})
    return books


async def get_exercise_images(book_url: str, exercise: str, page) -> list[bytes]:
    await page.goto(book_url, wait_until="domcontentloaded", timeout=30000)
    ex_link = None
    for l in await page.query_selector_all("a[href]"):
        href = await l.get_attribute("href") or ""
        txt = (await l.inner_text()).strip()
        if f"/{exercise}/" in href or txt == exercise or txt == f"№{exercise}":
            ex_link = href
            break
    if ex_link:
        if not ex_link.startswith("http"):
            ex_link = GDZ_BASE + ex_link
        await page.goto(ex_link, wait_until="domcontentloaded", timeout=30000)

    results = []
    for el in await page.query_selector_all("img"):
        src = await el.get_attribute("src") or await el.get_attribute("data-src") or ""
        if not src or any(x in src for x in ["logo", "icon", "banner", "adv"]):
            continue
        if not src.startswith("http"):
            src = GDZ_BASE + src
        try:
            resp = await page.request.get(src)
            data = await resp.body()
            img = Image.open(io.BytesIO(data)).convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=90)
            results.append(buf.getvalue())
        except Exception:
            continue
    return results


async def download_img(src: str, page) -> Image.Image:
    try:
        resp = await page.request.get(src)
        data = await resp.body()
        return Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        return Image.new("RGB", (200, 280), (50, 50, 50))


def make_grid(images: list) -> bytes:
    tw, th, cols, rows, gap = 200, 280, 3, 2, 8
    canvas = Image.new("RGB", (cols * tw + (cols + 1) * gap, rows * th + (rows + 1) * gap), (20, 20, 20))
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
    except Exception:
        font = ImageFont.load_default()
    for i, img in enumerate(images[:6]):
        c, r = i % cols, i // cols
        x, y = gap + c * (tw + gap), gap + r * (th + gap)
        canvas.paste(img.resize((tw, th), Image.LANCZOS), (x, y))
        draw.rectangle([x, y, x + 32, y + 32], fill=(0, 0, 0))
        draw.text((x + 4, y + 2), str(i + 1), fill="white", font=font)
    buf = io.BytesIO()
    canvas.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


async def send_books_page(target, books: list, offset: int):
    chunk = books[offset:offset + 6]
    async with async_playwright() as pw:
        br = await pw.chromium.launch(headless=True)
        page = await br.new_page()
        images = [await download_img(b["img"], page) for b in chunk]
        await br.close()

    grid = make_grid(images)
    kb = InlineKeyboardBuilder()
    for i in range(len(chunk)):
        kb.button(text=str(i + 1), callback_data=f"pick_{offset + i}")
    if offset + 6 < len(books):
        kb.button(text="Далее ➡️", callback_data=f"page_{offset + 6}")
    kb.adjust(3)

    caption = "\n".join(f"{i+1}. {b['title']}" for i, b in enumerate(chunk))
    photo = BufferedInputFile(grid, "books.jpg")
    if isinstance(target, Message):
        await target.answer_photo(photo, caption=caption, reply_markup=kb.as_markup())
    else:
        await target.message.answer_photo(photo, caption=caption, reply_markup=kb.as_markup())


@dp.message(Command("start"))
async def cmd_start(msg: Message):
    await msg.answer("Отправь запрос:\n<b>математика 8 класс 5 упр</b>", parse_mode="HTML")


@dp.message(F.text)
async def handle_query(msg: Message, state: FSMContext):
    parsed = parse_query(msg.text)
    if not parsed:
        await msg.answer("Формат: <b>математика 8 класс 5 упр</b>", parse_mode="HTML")
        return

    subject, grade, exercise = parsed
    status = await msg.answer(f"🔍 Гуглю: gdz.ru {subject} {grade} класс...")

    async with async_playwright() as pw:
        br = await pw.chromium.launch(headless=True)
        page = await br.new_page()
        gdz_url = await google_gdz_url(subject, grade, page)
        if not gdz_url:
            await status.edit_text("❌ Не нашёл ссылку на gdz.ru через Google.")
            await br.close()
            return
        await status.edit_text(f"✅ {gdz_url}\n⏳ Загружаю учебники...")
        books = await get_books(gdz_url, page)
        await br.close()

    if not books:
        await status.edit_text("❌ Учебники не найдены на странице.")
        return

    await status.delete()
    await state.set_state(S.choosing)
    await state.update_data(books=books, exercise=exercise)
    await send_books_page(msg, books, 0)


@dp.callback_query(F.data.startswith("page_"), S.choosing)
async def cb_page(cb: CallbackQuery, state: FSMContext):
    offset = int(cb.data.split("_")[1])
    data = await state.get_data()
    await cb.answer()
    await send_books_page(cb, data["books"], offset)


@dp.callback_query(F.data.startswith("pick_"), S.choosing)
async def cb_pick(cb: CallbackQuery, state: FSMContext):
    idx = int(cb.data.split("_")[1])
    data = await state.get_data()
    book = data["books"][idx]
    exercise = data["exercise"]

    await cb.answer()
    await cb.message.answer(f"📖 <b>{book['title']}</b>\n🔍 Ищу упражнение {exercise}...", parse_mode="HTML")

    async with async_playwright() as pw:
        br = await pw.chromium.launch(headless=True)
        page = await br.new_page()
        imgs = await get_exercise_images(book["href"], exercise, page)
        await br.close()

    if not imgs:
        await cb.message.answer("❌ Картинки решения не найдены.")
    else:
        for i, img_bytes in enumerate(imgs):
            await cb.message.answer_photo(
                BufferedInputFile(img_bytes, f"sol_{i+1}.jpg"),
                caption=f"{i+1}/{len(imgs)}" if len(imgs) > 1 else None
            )
    await state.clear()


if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
