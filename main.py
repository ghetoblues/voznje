import os
import asyncio
import re
import requests
import threading

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from aiogram import Bot as AioBot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

TOKEN_VOZNJE = os.environ.get('TOKEN_VOZNJE')
CHANNEL_ID_VOZNJE = '@muharedvoznje'

bot_voznje = AioBot(token=TOKEN_VOZNJE)
scheduler = AsyncIOScheduler()
api_url = "https://www.srbvoz.rs/wp-json/wp/v2/info_post?per_page=100"

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# ==== Роут для лендинга ====
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# ==== Telegram-бот ====
def read_last_sent_id():
    try:
        with open("last_sent_id.txt", "r") as file:
            return int(file.read().strip())
    except:
        return None

def write_last_sent_id(last_id):
    with open("last_sent_id.txt", "w") as file:
        file.write(str(last_id))

last_sent_id = read_last_sent_id()

def get_news_from_api():
    try:
        response = requests.get(api_url)
        if response.status_code != 200:
            return []
        data = response.json()
        news = []
        for item in data:
            news.append(
                {
                    "id": item["id"],
                    "date": item["date"].split("T")[0],
                    "title": item["title"]["rendered"],
                    "text": re.sub(r"<.*?>", "", item["content"]["rendered"]),
                }
            )
        return news
    except Exception as e:
        print(f"API Error: {e}")
        return []

async def send_news():
    global last_sent_id
    news = get_news_from_api()
    if news:
        new_news = [n for n in news if n["id"] > last_sent_id] if last_sent_id else news
        if new_news:
            latest = new_news[0]
            msg = f"📅 {latest['date']}\n📰 {latest['title']}\n\n{latest['text']}"
            try:
                await bot_voznje.send_message(CHANNEL_ID_VOZNJE, msg, parse_mode="HTML")
                last_sent_id = latest["id"]
                write_last_sent_id(last_sent_id)
            except Exception as e:
                print(f"Send error: {e}")

def start_polling_voznje():
    scheduler.add_job(
        send_news, IntervalTrigger(minutes=5), id="news_polling", replace_existing=True
    )
    scheduler.start()

def start_aiogram_bot():
    async def wrapper():
        await send_news()
        start_polling_voznje()
        while True:
            await asyncio.sleep(3600)
    asyncio.run(wrapper())

if __name__ == "__main__":
    threading.Thread(target=start_aiogram_bot, daemon=True).start()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
