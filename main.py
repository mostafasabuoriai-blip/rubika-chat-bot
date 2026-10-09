"""
🤖 بات تحلیل شخصیت روبیکا
+ پروفایل + چک عضویت + نسبت رابطه + سیستم صف
"""
import asyncio
import json
import random
import re
import sqlite3
import time
from datetime import datetime

from bot_api import RubikaBot
from analyzer import analyze_personality, analyze_friendship
from questions import QUESTIONS, FRIENDSHIP_QUESTIONS
import config


RESULT_FOOTER = (
    "\n\n━━━━━━━━━━━━━━━━━━━━\n"
    "🔗 این بات رو به دوستات معرفی کن!\n"
    "📢 کانال ما: @Mostafa_sabuori\n"
    "👤 سازنده: @Mostafasabuori\n\n"
    "💡 اگه نظر یا پیشنهادی داری، خوشحال می‌شیم بهمون بگی! 💌"
)


def parse_answers(text: str) -> list:
    numbered = re.split(r'\s*[\n]+\s*(?=[۰-۹0-9]+[\.\-\)\s])', text.strip())
    numbered = [n.strip() for n in numbered if n.strip()]
    if len(numbered) >= 5:
        return numbered
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    return [l for l in lines if len(l) > 1]


def init_db():
    conn = sqlite3.connect(config.DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            age TEXT,
            gender TEXT,
            state TEXT DEFAULT 'idle',
            friend_role TEXT,
            relationship TEXT,
            answers TEXT,
            match_code TEXT,
            partner_id TEXT,
            sender_id TEXT,
            created_at TEXT
        )
    """)
    for col in ["age", "gender", "friend_role", "sender_id", "relationship"]:
        try:
            c.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT")
        except sqlite3.OperationalError:
            pass
    c.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            type TEXT DEFAULT 'personal',
            result TEXT,
            partner_id TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    return conn


# ================================================================
# دکمه‌ها
# ================================================================

def menu_keypad():
    return {
        "rows": [
            {"buttons": [{"id": "btn_personality", "type": "Simple",
                          "button_text": "🧠 تحلیل شخصیت من"}]},
            {"buttons": [{"id": "btn_friends", "type": "Simple",
                          "button_text": "👥 تحلیل من و دوستم"}]},
            {"buttons": [{"id": "btn_profile", "type": "Simple",
                          "button_text": "👤 پروفایل من"}]},
            {"buttons": [{"id": "btn_history", "type": "Simple",
                          "button_text": "📜 تحلیل‌های من"}]},
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
    }


def friends_keypad():
    return {
        "rows": [
            {"buttons": [{"id": "btn_friend_new", "type": "Simple",
                          "button_text": "🆕 شروع تست جدید"}]},
            {"buttons": [{"id": "btn_friend_code", "type": "Simple",
                          "button_text": "🔢 وارد کردن کد دوست"}]},
            {"buttons": [{"id": "btn_back", "type": "Simple",
                          "button_text": "❌ بازگشت"}]},
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
    }


def relationship_keypad():
    return {
        "rows": [
            {"buttons": [{"id": "rel_friend", "type": "Simple",
                          "button_text": "👫 دوست"}]},
            {"buttons": [{"id": "rel_family", "type": "Simple",
                          "button_text": "👨‍👩‍👧 مادر/پدر و فرزند"}]},
            {"buttons": [{"id": "rel_sibling", "type": "Simple",
                          "button_text": "👧👦 خواهر/برادر"}]},
            {"buttons": [{"id": "rel_couple", "type": "Simple",
                          "button_text": "💑 زن و شوهر"}]},
            {"buttons": [{"id": "rel_colleague", "type": "Simple",
                          "button_text": "💼 همکار"}]},
            {"buttons": [{"id": "btn_cancel", "type": "Simple",
                          "button_text": "❌ انصراف"}]},
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True,
    }


def profile_keypad():
    return {
        "rows": [
            {"buttons": [{"id": "btn_edit_name", "type": "Simple",
                          "button_text": "✏️ ویرایش اسم"}]},
            {"buttons": [{"id": "btn_edit_age", "type": "Simple",
                          "button_text": "✏️ ویرایش سن"}]},
            {"buttons": [{"id": "btn_edit_gender", "type": "Simple",
                          "button_text": "✏️ ویرایش جنسیت"}]},
            {"buttons": [{"id": "btn_back", "type": "Simple",
                          "button_text": "❌ بازگشت"}]},
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
    }


def gender_keypad():
    return {
        "rows": [
            {"buttons": [{"id": "btn_male", "type": "Simple",
                          "button_text": "👨 مرد"}]},
            {"buttons": [{"id": "btn_female", "type": "Simple",
                          "button_text": "👩 زن"}]},
            {"buttons": [{"id": "btn_back", "type": "Simple",
                          "button_text": "❌ بازگشت"}]},
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
    }


def join_keypad():
    return {
        "rows": [
            {"buttons": [{"id": "btn_joined", "type": "Simple",
                          "button_text": "✅ عضو شدم — نتیجه رو نشون بده"}]},
            {"buttons": [{"id": "btn_cancel", "type": "Simple",
                          "button_text": "❌ انصراف"}]},
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
    }


def cancel_keypad():
    return {
        "rows": [
            {"buttons": [{"id": "btn_cancel", "type": "Simple",
                          "button_text": "❌ انصراف"}]},
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
    }


# ================================================================
# منطق بات
# ================================================================

class ChatBot:
    def __init__(self, bot: RubikaBot, conn):
        self.bot = bot
        self.conn = conn
        self.recent_welcome = {}
        self.ai_queue = asyncio.Queue()

    async def start(self):
        asyncio.create_task(self._ai_worker())

    # ── Worker صف AI ──

    async def _ai_worker(self):
        while True:
            request = await self.ai_queue.get()
            try:
                if request["type"] == "personal":
                    await self._do_personal(request)
                elif request["type"] == "friends":
                    await self._do_friends(request)
            except Exception as e:
                print(f"[AI WORKER] خطا: {e}")
                try:
                    self.update_user(request["user_id"], state="idle")
                    await self.send(request["user_id"],
                        "😔 مشکلی پیش اومد — دوباره تلاش کن!",
                        menu_keypad())
                except Exception:
                    pass
            finally:
                self.ai_queue.task_done()

    async def _do_personal(self, request):
        user_id = request["user_id"]
        try:
            profile = request.get("profile", {})
            result = await analyze_personality(
                request["answers"],
                user_name=profile.get("name") or "دوست من",
                age=profile.get("age"),
                gender=profile.get("gender"),
            )
            self.save_analysis(user_id, result, "personal")
            self.update_user(user_id, state="idle")
            await self.send(user_id, result + RESULT_FOOTER, menu_keypad())
            print(f"[AI DONE] کاربر: {user_id[:15]}...")
        except Exception as e:
            print(f"[AI ERROR] {e}")
            self.update_user(user_id, state="idle")
            await self.send(user_id,
                "😔 مشکلی پیش اومد — دوباره تلاش کن!",
                menu_keypad())

    async def _do_friends(self, request):
        user_a_id = request["user_a_id"]
        user_b_id = request["user_b_id"]
        try:
            result = await analyze_friendship(
                request["answers_a"], request["answers_b"],
                request["profile_a"], request["profile_b"],
                request.get("relationship", "دوست"),
            )
            self.save_analysis(user_a_id, result, "friends", user_b_id)
            self.save_analysis(user_b_id, result, "friends", user_a_id)
            self.update_user(user_a_id, state="idle")
            self.update_user(user_b_id, state="idle")

            await self.send(user_a_id, result + RESULT_FOOTER, menu_keypad())

            data_b = {
                "chat_id": user_b_id,
                "text": result + RESULT_FOOTER,
                "chat_keypad_type": "New",
                "chat_keypad": menu_keypad(),
            }
            self.bot._post("sendMessage", data_b)
            print(f"[AI DONE] جفت!")
        except Exception as e:
            print(f"[AI ERROR] {e}")
            self.update_user(user_a_id, state="idle")
            self.update_user(user_b_id, state="idle")
            await self.send(user_a_id,
                "😔 مشکلی پیش اومد — دوباره تلاش کن!",
                menu_keypad())

    # ── دیتابیس ──

    def get_user(self, user_id):
        c = self.conn.cursor()
        c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        row = c.fetchone()
        if row is None:
            c.execute(
                "INSERT INTO users (user_id, state, created_at) VALUES (?, 'idle', ?)",
                (user_id, datetime.now().isoformat())
            )
            self.conn.commit()
            return self._empty_user(user_id)

        col_names = [desc[0] for desc in c.description]
        data = dict(zip(col_names, row))

        defaults = {
            "name": None, "age": None, "gender": None, "state": "idle",
            "friend_role": None, "relationship": None, "answers": None,
            "match_code": None, "partner_id": None, "sender_id": None,
        }
        for key, default in defaults.items():
            if key not in data or data[key] is None:
                data[key] = default

        return data

    def _empty_user(self, user_id):
        return {"user_id": user_id, "name": None, "age": None, "gender": None,
                "state": "idle", "friend_role": None, "relationship": None,
                "answers": None, "match_code": None, "partner_id": None,
                "sender_id": None}

    def update_user(self, user_id, **kwargs):
        fields = ", ".join([f"{k}=?" for k in kwargs])
        values = list(kwargs.values()) + [user_id]
        self.conn.cursor().execute(
            f"UPDATE users SET {fields} WHERE user_id=?", values
        )
        self.conn.commit()

    def save_analysis(self, user_id, result, analysis_type="personal", partner_id=None):
        self.conn.cursor().execute(
            "INSERT INTO analyses (user_id, type, result, partner_id, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, analysis_type, result, partner_id, datetime.now().isoformat())
        )
        self.conn.commit()

    def get_history(self, user_id):
        c = self.conn.cursor()
        c.execute(
            "SELECT result, type, created_at FROM analyses "
            "WHERE user_id=? ORDER BY id DESC LIMIT 3",
            (user_id,)
        )
        return c.fetchall()

    def find_by_code(self, match_code):
        c = self.conn.cursor()
        c.execute(
            "SELECT user_id, name, age, gender, answers, relationship FROM users "
            "WHERE match_code=? AND answers IS NOT NULL",
            (match_code,)
        )
        return c.fetchone()

    def get_profile(self, user):
        return {
            "name": user.get("name") or "",
            "age": user.get("age") or "",
            "gender": user.get("gender") or "",
        }

    # ── ارسال ──

    async def send(self, chat_id, text, keypad=None):
        data = {"chat_id": chat_id, "text": text}
        if keypad:
            data["chat_keypad_type"] = "New"
            data["chat_keypad"] = keypad
        self.bot._post("sendMessage", data)

    # ── چک عضویت ──

    def check_membership(self, chat_id):
        if not config.REQUIRE_CHANNEL_JOIN:
            return True
        if not config.CHANNEL_ID:
            return True
        user = self.get_user(chat_id)
        sender_id = user.get("sender_id") or ""
        if not sender_id:
            return None
        return self.bot.is_channel_member(config.CHANNEL_ID, sender_id)

    # ── نمایش پروفایل ──

    async def show_profile(self, chat_id, user):
        name = user.get("name") or "❓ تنظیم نشده"
        age = user.get("age") or "❓ تنظیم نشده"
        gender = user.get("gender") or "❓ تنظیم نشده"

        await self.send(chat_id,
            f"👤 پروفایل تو:\n\n"
            f"📛 اسم: {name}\n"
            f"🎂 سن: {age}\n"
            f"🚻 جنسیت: {gender}\n\n"
            f"اینا به تحلیل‌هات کمک می‌کنه — هرچی کامل‌تر، تحلیل بهتر! ✨",
            profile_keypad())

    # ── مدیریت آپدیت ──

    async def handle_update(self, update: dict):
        if not isinstance(update, dict):
            return

        update_type = update.get("type", "")
        chat_id = update.get("chat_id")

        if not chat_id:
            return

        if update_type == "RemovedMessage":
            return

        if update_type == "StartedBot":
            self.recent_welcome[chat_id] = time.time()
            self.get_user(chat_id)
            await self.send(chat_id,
                "سلام! 👋\n\n"
                "🎉 خوش اومدی!\n\n"
                "وقتی آخرین بار عمیقاً به خودت نگاه کردی، کِی بود؟ 🤔\n\n"
                "🧠 با من می‌تونی:\n"
                "• بفهمی چه آدمی هستی\n"
                "• نقاط قوت و ضعفت رو بشناسی\n"
                "• ببینی چقدر با اطرافیانت جوری 👥\n\n"
                "از پایین شروع کن — ببین چی دراومد! 👇",
                menu_keypad())
            print(f"[START] کاربر: {chat_id[:15]}...")
            return

        if update_type == "StoppedBot":
            print(f"[STOP] کاربر: {chat_id[:15]}...")
            return

        if update_type == "NewMessage":
            msg = update.get("new_message", {})
            text = msg.get("text", "")

            if not text or not text.strip():
                return

            sender_id = msg.get("sender_id", "")
            if sender_id:
                u = self.get_user(chat_id)
                if not u.get("sender_id"):
                    self.update_user(chat_id, sender_id=sender_id)

            print(f"[MSG] chat={chat_id[:15]}... text={str(text)[:50]}")

            user = self.get_user(chat_id)
            state = user["state"]

            # ═══════════ دکمه‌های اصلی ═══════════

            if text == "🧠 تحلیل شخصیت من":
                await self._btn_personality(chat_id, user)
                return

            elif text == "👥 تحلیل من و دوستم":
                self.update_user(chat_id, state="friend_choosing")
                await self.send(chat_id,
                    "👥 حالت مقایسه!\n\n"
                    "دوست داری خودت تست بسازی و کد بگیری،\n"
                    "یا کد طرف مقابل رو وارد کنی؟",
                    friends_keypad())
                return

            elif text == "👤 پروفایل من":
                self.update_user(chat_id, state="profile_menu")
                await self.show_profile(chat_id, user)
                return

            elif text == "📜 تحلیل‌های من":
                await self._show_history(chat_id, user)
                return

            elif text == "❌ انصراف":
                self.update_user(chat_id, state="idle", answers=None,
                                 match_code=None, partner_id=None, friend_role=None)
                await self.send(chat_id, "باشه! هر وقت خواستی دوباره بیا 🌟", menu_keypad())
                return

            # ═══════════ دکمه‌ی عضو شدم ═══════════

            elif text == "✅ عضو شدم — نتیجه رو نشون بده":
                user = self.get_user(chat_id)
                if user["state"] != "waiting_join":
                    await self.send(chat_id, "اول تست رو کامل کن! 🤷", menu_keypad())
                    return

                is_member = self.check_membership(chat_id)

                if is_member is False:
                    await self.send(chat_id,
                        "❌ هنوز عضو نشدی!\n\n"
                        f"🔗 {config.CHANNEL_LINK}\n\n"
                        f"عضو شو و دوباره بزن!",
                        join_keypad())
                    return

                # ✅ عضو شد — ادامه بده

                # حالت شخصی
                if user.get("friend_role") is None:
                    answers = json.loads(user["answers"] or "[]")
                    if not answers:
                        await self.send(chat_id, "مشکلی پیش اومد — دوباره تلاش کن!", menu_keypad())
                        return

                    self.update_user(chat_id, state="processing")
                    await self.send(chat_id,
                        "⏳ در حال تحلیل شخصیتت...\n\nیه ذره صبر کن! 🧠")

                    profile = self.get_profile(user)
                    await self.ai_queue.put({
                        "type": "personal",
                        "user_id": chat_id,
                        "answers": answers,
                        "profile": profile,
                    })
                    return

                # ✅ حالت دوستانه — joiner
                elif user.get("friend_role") == "joiner":
                    self.update_user(chat_id, state="entering_code")
                    await self.send(chat_id,
                        "✅ ممنون!\n\n"
                        "🔢 حالا کد طرف مقابل رو بفرست (۴ رقم):",
                        cancel_keypad())
                    return

                # ✅ حالت دوستانه — creator
                elif user.get("friend_role") == "creator":
                    code = str(random.randint(1000, 9999))
                    self.update_user(chat_id, match_code=code, state="waiting_friend")
                    await self.send(chat_id,
                        f"✅ جواب‌هات ثبت شد!\n\n"
                        f"🔗 کد تو: «{code}»\n\n"
                        f"این کد رو بفرست براش!\n\n"
                        f"اونم باید:\n"
                        f"۱. این بات رو باز کنه\n"
                        f"۲. «👥 تحلیل من و دوستم» بزنه\n"
                        f"۳. «🔢 وارد کردن کد» بزنه\n"
                        f"۴. تست بده و کد رو وارد کنه\n\n"
                        f"🎉 نتیجه براتون میاد!",
                        cancel_keypad())
                    return

            # ═══════════ دکمه‌های دوستانه ═══════════

            elif text == "🆕 شروع تست جدید":
                await self._btn_friend_new(chat_id, user)
                return

            elif text == "🔢 وارد کردن کد دوست":
                await self._btn_friend_code(chat_id, user)
                return

            # ═══════════ دکمه‌های نسبت ═══════════

            elif text == "👫 دوست":
                await self._set_relationship(chat_id, user, "دوست")
                return

            elif text == "👨‍👩‍👧 مادر/پدر و فرزند":
                await self._set_relationship(chat_id, user, "مادر/پدر و فرزند")
                return

            elif text == "👧👦 خواهر/برادر":
                await self._set_relationship(chat_id, user, "خواهر/برادر")
                return

            elif text == "💑 زن و شوهر":
                await self._set_relationship(chat_id, user, "زن و شوهر")
                return

            elif text == "💼 همکار":
                await self._set_relationship(chat_id, user, "همکار")
                return

            # ═══════════ دکمه‌های پروفایل ═══════════

            elif text == "✏️ ویرایش اسم":
                self.update_user(chat_id, state="profile_name")
                await self.send(chat_id,
                    f"اسمت چیه؟\n\n(فعلی: {user.get('name') or 'تنظیم نشده'})",
                    cancel_keypad())
                return

            elif text == "✏️ ویرایش سن":
                self.update_user(chat_id, state="profile_age")
                await self.send(chat_id,
                    f"سن‌ت چنده؟ (فقط عدد بنویس)\n\n(فعلی: {user.get('age') or 'تنظیم نشده'})",
                    cancel_keypad())
                return

            elif text == "✏️ ویرایش جنسیت":
                self.update_user(chat_id, state="profile_gender")
                await self.send(chat_id, "جنسیتت رو انتخاب کن:", gender_keypad())
                return

            elif text == "👨 مرد":
                self.update_user(chat_id, gender="مرد", state="profile_menu")
                user = self.get_user(chat_id)
                await self.show_profile(chat_id, user)
                return

            elif text == "👩 زن":
                self.update_user(chat_id, gender="زن", state="profile_menu")
                user = self.get_user(chat_id)
                await self.show_profile(chat_id, user)
                return

            # ═══════════ بازگشت ═══════════

            elif text == "❌ بازگشت":
                self.update_user(chat_id, state="idle")
                await self.send(chat_id, "منوی اصلی 👇", menu_keypad())
                return

            # ═══════════ /start ═══════════

            if text.strip().lower() in ("/start", "start", "شروع"):
                if chat_id in self.recent_welcome and time.time() - self.recent_welcome[chat_id] < 10:
                    await self.send(chat_id, "انتخاب کن 👇", menu_keypad())
                    return
                await self.send(chat_id,
                    "سلام! 👋\n\n🎉 خوش اومدی!\n\nاز پایین شروع کن! 👇",
                    menu_keypad())
                return

            # ═══════════ متن عادی ═══════════

            await self._handle_text(chat_id, user, text, state)
            return

        print(f"[UNKNOWN] type={update_type}")

    # ═══════════ هندلر دکمه‌ها ═══════════

    async def _btn_personality(self, chat_id, user):
        if user["name"]:
            self.update_user(chat_id, state="asking_questions",
                             match_code=None, partner_id=None, answers=None,
                             friend_role=None)
            questions_text = "\n\n".join(QUESTIONS)
            await self.send(chat_id,
                f"{user['name']} جان! 🌟\n\n"
                f"این ۱۰ سوال رو جواب بده:\n\n"
                f"{questions_text}\n\n"
                f"💬 هر جواب رو یه خط بنویس — همه رو با هم بفرست",
                cancel_keypad())
        else:
            self.update_user(chat_id, state="asking_name")
            await self.send(chat_id,
                "خوش اومدی! 🌟\n\nاسمت چیه؟ (اسم خودت رو بنویس!)",
                cancel_keypad())

    async def _btn_friend_new(self, chat_id, user):
        self.update_user(chat_id, friend_role="creator")

        if user["name"]:
            self.update_user(chat_id, state="asking_relationship",
                             match_code=None, partner_id=None, answers=None)
            await self.send(chat_id,
                "👍 حالا بگو نسبت شما دو نفر چیه؟\n\n"
                "این کمک می‌کنه تحلیل دقیق‌تر باشه!",
                relationship_keypad())
        else:
            self.update_user(chat_id, state="asking_name_friend")
            await self.send(chat_id,
                "خوش اومدی! 🌟\n\n"
                "⚠️ اسم «خودت» رو بنویس — نه اسم دوستت!\n\n"
                "اسمت چیه؟",
                cancel_keypad())

    async def _btn_friend_code(self, chat_id, user):
        self.update_user(chat_id, friend_role="joiner")

        if user["answers"]:
            self.update_user(chat_id, state="entering_code")
            await self.send(chat_id,
                "🔢 کد طرف مقابل رو بفرست (۴ رقم):",
                cancel_keypad())
        else:
            if user["name"]:
                self.update_user(chat_id, state="asking_questions_friend",
                                 match_code=None, partner_id=None, answers=None)
                questions_text = "\n\n".join(FRIENDSHIP_QUESTIONS)
                await self.send(chat_id,
                    f"{user['name']} جان! 🌟\n\n"
                    f"اول باید خودت تست رو بدی:\n\n"
                    f"{questions_text}\n\n"
                    f"💬 هر جواب رو یه خط بنویس\n\n"
                    f"بعدش کد طرف مقابل رو ازت می‌پرسم! 🔢",
                    cancel_keypad())
            else:
                self.update_user(chat_id, state="asking_name_friend")
                await self.send(chat_id,
                    "اسمت چیه؟\n\n"
                    "⚠️ اسم «خودت» رو بنویس — نه اسم دوستت!\n\n"
                    "(بعدش تست می‌دی و کد رو وارد می‌کنی)",
                    cancel_keypad())

    async def _set_relationship(self, chat_id, user, relationship):
        self.update_user(chat_id, relationship=relationship,
                         state="asking_questions_friend",
                         match_code=None, partner_id=None, answers=None)

        questions_text = "\n\n".join(FRIENDSHIP_QUESTIONS)
        await self.send(chat_id,
            f"عالی! 🌟\n\n"
            f"نسبت «{relationship}» ثبت شد.\n\n"
            f"این ۱۰ سوال رو درباره رابطه‌ت با اون جواب بده:\n\n"
            f"{questions_text}\n\n"
            f"💬 هر جواب رو یه خط بنویس — همه رو با هم بفرست\n\n"
            f"بعدش کد می‌گیری که بفرستی براش! 🔗",
            cancel_keypad())

    async def _show_history(self, chat_id, user):
        history = self.get_history(chat_id)
        if not history:
            await self.send(chat_id,
                "هنوز تحالیلی نداری! 🤷\n\nاول یه تست بده:",
                menu_keypad())
        else:
            await self.send(chat_id, f"📜 {len(history)} تحلیل اخیرت:\n")
            for i, (result, rtype, date) in enumerate(history, 1):
                emoji = "👥" if rtype == "friends" else "🧠"
                await self.send(chat_id,
                    f"{emoji} تحلیل {i} — {date[:10]}\n\n{result}\n")
            await self.send(chat_id, "همه‌ی تحلیل‌هات ⬆️", menu_keypad())

    # ═══════════ متن عادی ═══════════

    async def _handle_text(self, chat_id, user, text, state):
        # ── اسم (شخصی) ──
        if state == "asking_name":
            name = text.strip()[:30]
            self.update_user(chat_id, name=name, state="asking_questions", answers=None)
            questions_text = "\n\n".join(QUESTIONS)
            await self.send(chat_id,
                f"سلام {name}! 🌟\n\n"
                f"این ۱۰ سوال رو جواب بده:\n\n"
                f"{questions_text}\n\n"
                f"💬 هر جواب رو یه خط بنویس — همه رو با هم بفرست",
                cancel_keypad())

        # ── اسم (دوستانه) ──
        elif state == "asking_name_friend":
            name = text.strip()[:30]
            role = user.get("friend_role") or "creator"
            self.update_user(chat_id, name=name, state="asking_relationship" if role == "creator" else "asking_questions_friend", answers=None)

            if role == "joiner":
                questions_text = "\n\n".join(FRIENDSHIP_QUESTIONS)
                await self.send(chat_id,
                    f"سلام {name}! 🌟\n\n"
                    f"این ۱۰ سوال رو درباره رابطه‌ت با اون جواب بده:\n\n"
                    f"{questions_text}\n\n"
                    f"💬 هر جواب رو یه خط بنویس\n\n"
                    f"بعدش کد طرف مقابل رو ازت می‌پرسم! 🔢",
                    cancel_keypad())
            else:
                await self.send(chat_id,
                    f"سلام {name}! 🌟\n\n"
                    f"حالا بگو نسبت شما دو نفر چیه؟\n\n"
                    f"این کمک می‌کنه تحلیل دقیق‌تر باشه!",
                    relationship_keypad())

        # ── جواب‌های تست ──
        elif state in ("asking_questions", "asking_questions_friend"):
            answers = parse_answers(text)

            if len(answers) < 5:
                await self.send(chat_id,
                    "😅 جواب‌هات کامل نیست!\n\n"
                    "هر جواب رو یه خط بنویس و همه رو با هم بفرست",
                    cancel_keypad())
                return

            answers_json = json.dumps(answers, ensure_ascii=False)
            self.update_user(chat_id, answers=answers_json)

            # ── شخصی ──
            if state == "asking_questions":
                is_member = self.check_membership(chat_id)

                if is_member is False:
                    self.update_user(chat_id, state="waiting_join")
                    await self.send(chat_id,
                        f"📢 برای دیدن نتیجه، اول عضو کانال ما شو!\n\n"
                        f"🔗 {config.CHANNEL_LINK}\n\n"
                        f"عضو که شدی، دکمه پایین رو بزن 👇",
                        join_keypad())
                    return

                self.update_user(chat_id, state="processing")

                queue_pos = self.ai_queue.qsize()
                if queue_pos > 0:
                    await self.send(chat_id,
                        f"⏳ {queue_pos} نفر قبل از شما در صفه\n"
                        f"حدود {queue_pos * 60} ثانیه صبر کن! 🙏")
                else:
                    await self.send(chat_id,
                        "⏳ در حال تحلیل شخصیتت...\n\nیه ذره صبر کن! 🧠")

                profile = self.get_profile(user)
                await self.ai_queue.put({
                    "type": "personal",
                    "user_id": chat_id,
                    "answers": answers,
                    "profile": profile,
                })

            # ── دوستانه ──
            elif state == "asking_questions_friend":
                role = user.get("friend_role") or "creator"

                # ✅ چک عضویت توی حالت دوستانه
                is_member = self.check_membership(chat_id)

                if is_member is False:
                    self.update_user(chat_id, state="waiting_join")
                    await self.send(chat_id,
                        f"📢 برای دیدن نتیجه، اول عضو کانال ما شو!\n\n"
                        f"🔗 {config.CHANNEL_LINK}\n\n"
                        f"عضو که شدی، دکمه پایین رو بزن 👇",
                        join_keypad())
                    return

                if role == "creator":
                    code = str(random.randint(1000, 9999))
                    self.update_user(chat_id, match_code=code, state="waiting_friend")

                    await self.send(chat_id,
                        f"✅ جواب‌هات ثبت شد!\n\n"
                        f"🔗 کد تو: «{code}»\n\n"
                        f"این کد رو برای طرف مقابل بفرست. اونم باید:\n"
                        f"۱. این بات رو باز کنه\n"
                        f"۲. «👥 تحلیل من و دوستم» رو بزنه\n"
                        f"۳. «🔢 وارد کردن کد» رو انتخاب کنه\n"
                        f"۴. تست رو بده و کد تو رو وارد کنه\n\n"
                        f"بعد هر دوتون نتیجه می‌گیرید! 🎉\n\n"
                        f"⏳ منتظر می‌مونم...")

                elif role == "joiner":
                    self.update_user(chat_id, state="entering_code")
                    await self.send(chat_id,
                        "✅ جواب‌هات ثبت شد!\n\n"
                        "🔢 حالا کد طرف مقابل رو بفرست (۴ رقم):",
                        cancel_keypad())

        # ── کد ──
        elif state == "entering_code":
            await self._handle_code(chat_id, user, text)

        # ── پروفایل: اسم ──
        elif state == "profile_name":
            name = text.strip()[:30]
            self.update_user(chat_id, name=name, state="profile_menu")
            user = self.get_user(chat_id)
            await self.send(chat_id, f"✅ اسمت ذخیره شد: {name} 🌟")
            await self.show_profile(chat_id, user)

        # ── پروفایل: سن ──
        elif state == "profile_age":
            age = text.strip()
            if not age.isdigit() or not (1 <= int(age) <= 120):
                await self.send(chat_id, "❌ سن باید عدد بین ۱ تا ۱۲۰ باشه!", cancel_keypad())
                return
            self.update_user(chat_id, age=age, state="profile_menu")
            user = self.get_user(chat_id)
            await self.send(chat_id, f"✅ سن‌ت ذخیره شد: {age} 🎂")
            await self.show_profile(chat_id, user)

        # ── پیش‌فرض ──
        else:
            await self.send(chat_id,
                "از منوی پایین انتخاب کن 👇",
                menu_keypad())

    # ── مدیریت کد ──

    async def _handle_code(self, chat_id, user, text):
        code = text.strip()

        if not code.isdigit() or len(code) != 4:
            await self.send(chat_id,
                "❌ کد باید ۴ رقم باشه! مثلاً: 7231",
                cancel_keypad())
            return

        partner = self.find_by_code(code)
        if not partner:
            await self.send(chat_id,
                "❌ این کد پیدا نشد! کد درست رو بگیر.",
                cancel_keypad())
            return

        partner_id, p_name, p_age, p_gender, partner_answers_json, p_relationship = partner

        if partner_id == chat_id:
            await self.send(chat_id,
                "😅 این کد خودته!",
                cancel_keypad())
            return

        partner_answers = json.loads(partner_answers_json)
        user_answers = json.loads(user["answers"] or "[]")

        if not user_answers:
            await self.send(chat_id,
                "اول باید خودت تست رو بدی!",
                menu_keypad())
            return

        profile_a = self.get_profile(user)
        profile_b = {"name": p_name or "کاربر ۲", "age": p_age or "", "gender": p_gender or ""}

        self.update_user(chat_id, partner_id=partner_id, state="processing")
        self.update_user(partner_id, partner_id=chat_id, state="processing")

        queue_pos = self.ai_queue.qsize()
        if queue_pos > 0:
            await self.send(chat_id, f"⏳ {queue_pos} نفر قبل از شما 🙏")
        else:
            await self.send(chat_id, "⏳ در حال تحلیل شما دو نفر... 🤝")

        self.bot.send_message(partner_id,
            "🎉 طرف مقابل کد رو وارد کرد!\n⏳ در حال تحلیل شما دو نفر...")

        await self.ai_queue.put({
            "type": "friends",
            "user_a_id": chat_id,
            "user_b_id": partner_id,
            "answers_a": user_answers,
            "answers_b": partner_answers,
            "profile_a": profile_a,
            "profile_b": profile_b,
            "relationship": p_relationship or "دوست",
        })


# ================================================================
# اجرای اصلی
# ================================================================

async def run():
    import os
    print("=" * 55)
    print("  🤖 بات تحلیل شخصیت — روبیکا")
    print("=" * 55)

    bot = RubikaBot(config.BOT_TOKEN)
    me = bot.get_me()

    if not me:
        print("  ❌ اتصال برقرار نشد!")
        return

    print(f"  ✅ متصل شد!")
    print(f"  🤖 @{config.BOT_USERNAME}")

    print("  🧹 در حال پاک کردن آپدیت‌های قدیمی...")
    bot.skip_old_updates()

    print(f"  📡 در حال گوش دادن...")
    print("=" * 55)

    conn = init_db()
    chatbot = ChatBot(bot, conn)
    await chatbot.start()

    max_runtime = int(os.environ.get("MAX_RUNTIME", "0"))
    start_time = time.time()

    try:
        error_count = 0
        while True:
            if max_runtime > 0 and (time.time() - start_time) > max_runtime:
                print("\n⏰ زمان تمام شد — اجرای بعدی...")
                break

            updates = bot.get_updates()

            if updates is None:
                error_count += 1
                if error_count == 1:
                    print("⚠️ اتصال قطع شد...")
                await asyncio.sleep(min(2 + error_count, 30))
                continue

            if error_count > 0:
                print("✅ اتصال برقرار شد!")
            error_count = 0

            if updates:
                for update in updates:
                    try:
                        await chatbot.handle_update(update)
                    except Exception as e:
                        print(f"[ERROR] {type(e).__name__}: {e}")
                continue

            await asyncio.sleep(0.5)

    except KeyboardInterrupt:
        print("\n👋 بات خاموش شد!")
    finally:
        conn.close()
        _trigger_next_run()


def _trigger_next_run():
    import os
    if os.environ.get("TRIGGER_NEXT") != "1":
        return

    pat = os.environ.get("GH_PAT")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not pat or not repo:
        return

    try:
        import requests
        url = f"https://api.github.com/repos/{repo}/actions/workflows/bot.yml/dispatches"
        r = requests.post(
            url,
            headers={"Authorization": f"Bearer {pat}"},
            json={"ref": "main"},
            timeout=30,
        )
        if r.status_code == 204:
            print("✅ اجرای بعدی trigger شد!")
        else:
            print(f"⚠️ trigger: {r.status_code}")
    except Exception as e:
        print(f"❌ trigger خطا: {e}")


if __name__ == "__main__":
    asyncio.run(run())
