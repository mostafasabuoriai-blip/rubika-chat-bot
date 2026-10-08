"""
ربات روبیکا — لایه API
اتصال به Rubika Bot API v3
"""
import requests


class RubikaBot:
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://botapi.rubika.ir/v3/{token}"
        self.next_offset_id = None
        self._last_error = None
        self.session = requests.Session()  # ✅ اتصال دائمی — سرعت بیشتر!

    def _post(self, method: str, data: dict = None):
        url = f"{self.base_url}/{method}"
        try:
            response = self.session.post(  # ✅ session.post — نه requests.post
                url,
                json=data or {},
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            return response.json()
        except Exception as e:
            error_name = type(e).__name__
            if self._last_error != error_name:
                print(f"[API] خطا ({method}): {error_name}")
                self._last_error = error_name
            return None

    # ── اطلاعات بات ──

    def get_me(self):
        return self._post("getMe")

    # ── دریافت آپدیت‌ها ──

    def get_updates(self):
        data = {}
        if self.next_offset_id:
            data["offset_id"] = self.next_offset_id
        result = self._post("getUpdates", data)

        if not result:
            return None  # None یعنی اررور — [] یعنی پیام جدید نیست

        updates = []

        if isinstance(result, dict):
            if "data" in result and isinstance(result["data"], dict):
                d = result["data"]
                if "updates" in d:
                    updates = d["updates"]
                elif "update" in d:
                    updates = [d["update"]]
                if "next_offset_id" in d:
                    self.next_offset_id = d["next_offset_id"]
            elif "updates" in result:
                updates = result["updates"]
            elif isinstance(result.get("data"), list):
                updates = result["data"]

        if not isinstance(updates, list):
            updates = []

        return updates

    # ── رد کردن آپدیت‌های قدیمی ──

    def skip_old_updates(self):
        """آپدیت‌های قدیمی رو رد کن — فقط جدیدا رو گوش بده"""
        total = 0
        while True:
            updates = self.get_updates()
            if not updates:
                break
            total += len(updates)
            if total > 200:
                break
        return total

    # ── ارسال پیام ──

    def send_message(self, chat_id: str, text: str,
                     chat_keypad: dict = None,
                     reply_to_message_id: str = None) -> dict:
        data = {
            "chat_id": chat_id,
            "text": text,
        }
        if chat_keypad:
            data["chat_keypad_type"] = "New"
            data["chat_keypad"] = chat_keypad
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id
        return self._post("sendMessage", data)

    # ── چک عضویت در کانال ──

    def is_channel_member(self, channel_id: str, user_id: str):
        """چک عضویت کاربر در کانال"""
        if not channel_id or not user_id:
            return None

        result = self._post("getChatMember", {
            "chat_id": channel_id,
            "user_id": user_id,
        })

        if not result:
            return None

        import json
        print(f"[MEMBERSHIP] {json.dumps(result, ensure_ascii=False)[:400]}")

        status = result.get("status", "")

        if status == "OK":
            data = result.get("data", {})
            member = data.get("chat_member", {})
            if member:
                member_status = member.get("status", "")
                if member_status.lower() in ("left", "kicked", "banned"):
                    return False
                return True
            return False

        # ❌ INVALID_INPUT = کاربر عضو نیست
        return False

    # ── استخراج اطلاعات از آپدیت ──

    @staticmethod
    def parse_update(update: dict):
        """استخراج اطلاعات از آپدیت"""
        if not isinstance(update, dict):
            return None, None, None, None

        update_type = update.get("type", "")
        chat_id = update.get("chat_id")
        text = None
        button_id = None
        message_id = None

        if update_type == "NewMessage":
            msg = update.get("new_message", {})
            text = msg.get("text")
            message_id = msg.get("message_id")

        elif update_type == "RemovedMessage":
            return None, None, None, None

        return chat_id, text, button_id, message_id
