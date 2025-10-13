﻿# bot.py (ShieldX v3.1 Final Moderate)
# Keep this file as a single module. Replace your existing bot.py with this.
import asyncio
import json
import os
import threading
import time
import tempfile
import shutil
import traceback
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from flask import Flask
from pyrogram import Client, filters, types
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, RPCError, ChatWriteForbidden
from dotenv import load_dotenv

# Optional system stats
try:
    import psutil
except Exception:
    psutil = None

# ---------------------------
# CONFIG / ENV
# ---------------------------
load_dotenv()
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", 0)) if os.getenv("OWNER_ID") else 0

# Extra owners
def parse_owner_ids(s: str) -> List[int]:
    if not s:
        return []
    parts = [p.strip() for p in s.split(",") if p.strip()]
    ids: List[int] = []
    for p in parts:
        try:
            ids.append(int(p))
        except:
            continue
    return ids

CO_OWNER_IDS = parse_owner_ids(os.getenv("CO_OWNER_IDS", ""))

RENDER_API_KEY = os.getenv("RENDER_API_KEY", "")
RENDER_SERVICE_ID = os.getenv("RENDER_SERVICE_ID", "")
RENDER_HEALTH_URL = os.getenv("RENDER_HEALTH_URL", "")

HF_API_KEY = os.getenv("HF_API_KEY", "")  # optional for NSFW HF

DATA_FILE = "data.json"  # persistent per-chat settings

# ---------------------------
# DEFAULT MESSAGES / LOCALES
# ---------------------------
MESSAGES = {
    "en-in": {
        "start_dm": "ðŸ›¡ï¸ *ShieldX Protection*\nI keep your groups clean. Use buttons below.",
        "start_group": "ðŸ›¡ï¸ ShieldX active in this group.",
        "help_dm": "âœ¨ *ShieldX Commands*\n\nâ€¢ /clean [time] â€” enable auto-clean (admins)\nâ€¢ /clean off â€” disable auto-clean\nâ€¢ /cleanall â€” delete last 24h media (owner)\nâ€¢ /nsfw on|off|status â€” NSFW detection\nâ€¢ /status â€” system health (DM)\nâ€¢ /reload â€” owner only\n\nDefault auto-clean: 30 minutes.",
        "help_group": "ðŸ“© Sent you a DM with commands.",
        "auto_on": "âœ… Auto-clean enabled â€” interval: {t}.",
        "auto_off": "ðŸ›‘ Auto-clean disabled.",
        "auto_set": "âœ… Auto-clean set to {t}.",
        "cleanall_start": "ðŸ§¹ Clearing media from last 24 hours...",
        "cleanall_done": "âœ… {n} media items removed (last 24h).",
        "only_admin": "âš ï¸ Only group admins can use this.",
        "only_owner": "âš ï¸ Only group owner or co-owner can use this.",
        "status_text": "ðŸ§¹ Auto-clean: {on} | Interval: {t}",
        "ping_text": "ðŸ“ Pong! {ms}ms",
    },
    "hi": {
        "start_dm": "ðŸ›¡ï¸ ShieldX â€” à¤†à¤ªà¤•à¤¾ auto-clean à¤¸à¤¹à¤¾à¤¯à¤•à¥¤ à¤¨à¥€à¤šà¥‡ à¤¬à¤Ÿà¤¨à¥à¤¸ à¤¦à¥‡à¤–à¥‡à¤‚à¥¤",
        "start_group": "ðŸ›¡ï¸ ShieldX à¤¸à¤®à¥‚à¤¹ à¤®à¥‡à¤‚ à¤¸à¤•à¥à¤°à¤¿à¤¯ à¤¹à¥ˆà¥¤",
        "help_dm": "à¤•à¤®à¤¾à¤‚à¤¡:\n/clean [time]\n/clean off\n/cleanall\n/nsfw on|off|status\n/status\n/reload",
        "help_group": "à¤•à¤®à¤¾à¤‚à¤¡ DM à¤®à¥‡à¤‚ à¤­à¥‡à¤œ à¤¦à¥€ à¤—à¤ˆ à¤¹à¥ˆà¤‚à¥¤",
        "auto_on": "âœ… Auto-clean à¤šà¤¾à¤²à¥‚ â€” à¤…à¤‚à¤¤à¤°à¤¾à¤²: {t}.",
        "auto_off": "ðŸ›‘ Auto-clean à¤¬à¤‚à¤¦ à¤•à¤¿à¤¯à¤¾ à¤—à¤¯à¤¾à¥¤",
        "auto_set": "âœ… Auto-clean à¤¸à¥‡à¤Ÿ à¤•à¤¿à¤¯à¤¾ à¤—à¤¯à¤¾ â€” à¤…à¤‚à¤¤à¤°à¤¾à¤² {t}.",
        "cleanall_start": "ðŸ§¹ à¤ªà¤¿à¤›à¤²à¥‡ 24 à¤˜à¤‚à¤Ÿà¥‡ à¤•à¥‡ à¤®à¥€à¤¡à¤¿à¤¯à¤¾ à¤¹à¤Ÿà¤¾à¤ à¤œà¤¾ à¤°à¤¹à¥‡ à¤¹à¥ˆà¤‚...",
        "cleanall_done": "âœ… {n} à¤®à¥€à¤¡à¤¿à¤¯à¤¾ à¤¹à¤Ÿà¤¾à¤ à¤—à¤ (à¤ªà¤¿à¤›à¤²à¥‡ 24 à¤˜à¤‚à¤Ÿà¥‡)à¥¤",
        "only_admin": "âš ï¸ à¤•à¥‡à¤µà¤² group admins à¤‰à¤ªà¤¯à¥‹à¤— à¤•à¤° à¤¸à¤•à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤",
        "only_owner": "âš ï¸ à¤•à¥‡à¤µà¤² group owner à¤¯à¤¾ co-owner à¤‰à¤ªà¤¯à¥‹à¤— à¤•à¤° à¤¸à¤•à¤¤à¥‡ à¤¹à¥ˆà¤‚à¥¤",
        "status_text": "Auto-clean: {on} | Interval: {t}",
        "ping_text": "ðŸ“ Pong! {ms}ms",
    }
}
DEFAULT_LOCALE = "en-in"
SUPPORTED_LOCALES = list(MESSAGES.keys())

# ---------------------------
# STORAGE HANDLING
# ---------------------------
def

