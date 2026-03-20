#!/usr/bin/env python3
import os
import asyncio
from fastapi import FastAPI
import uvicorn
from contextlib import asynccontextmanager
from telegram.ext import Application, CommandHandler

# Токен из переменной окружения
TOKEN = os.environ.get("TELEGRAM_TOKEN")

if not TOKEN:
    raise Exception("TELEGRAM_TOKEN not set")

app = FastAPI()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Запускаем Telegram-бота
    telegram_app = Application.builder().token(TOKEN).build()

    async def start(update, context):
        await update.message.reply_text("Бот работает!")

    async def status(update, context):
        await update.message.reply_text("Статус: OK")

    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("status", status))

    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.updater.start_polling()
    print("Telegram bot started")
    yield
    # Остановка при завершении
    await telegram_app.stop()

app.router.lifespan_context = lifespan

@app.get("/")
def root():
    return {"status": "alive"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
