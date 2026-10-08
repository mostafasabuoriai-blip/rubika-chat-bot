"""
تحلیل با Groq API — سریع، بدون مرورگر ⚡
"""
import requests
import config


# ================================================================
# پرامپت‌ها
# ================================================================

def build_personality_prompt(answers: list, user_name: str = "",
                              age: str = "", gender: str = "") -> str:
    qa_text = "\n".join([
        f"سوال {i+1}: جواب: {ans}" for i, ans in enumerate(answers)
    ])

    profile = user_name
    if age:
        profile += f"، {age} ساله"
    if gender:
        profile += f"، {gender}"

    return f"""تو یه روانشناس خودمونی هستی که برای یه کانال فارسی کار می‌کنه.
یه نفر به اسم {profile} این جواب‌ها رو به ۱۰ سوال شخصیت‌شناسی داده:

{qa_text}

⚠️ قوانین محتوا:
- اگه کلمات رکیک یا نامناسب هست، کاملاً نادیده‌شان بگیر
- تحلیل رو همیشه تمیز نگه دار

حالا تحلیل شخصیتش رو با این فرمت بنویس:

🎭 شخصیت تو: (یه عنوان کوتاه و بامزه — مثل «آرامِ متفکر»)

✨ نقاط قوت:
• (۲-۳ مورد با توضیح کوتاه)

⚠️ نقاط ضعف:
• (۱-۲ مورد — با ملایمت، بدون تیکه)

🚨 حواست به این باش:
(چیزایی که اگه بی‌توجه باشی، بعداً برات مشکل می‌سازه)

🛠️ روی این کار کن:
(۲ بخش از خودت که بهتر شدنشون زندگی‌ت رو قشنگ‌تر می‌کنه)

💡 پیشنهاد امروز:
(یه کار ساده که همین امروز می‌تونه انجام بده)

🌟 جمع‌بندی:
(یه جمله‌ی گرم — اسمش رو استفاده کن)

قوانین نوشتاری:
- لحن خودمونی و دوستاده
- اسم کاربر رو چند بار استفاده کن
- هر بخش با ایموجی جدا
- بین بخش‌ها خط خالی
- جمله‌ها کوتاه و روان
- انگار یه رفیعِ آگاه داری بهش می‌گی

مستقیم متن رو بنویس — بدون توضیح اضافه."""


def build_friendship_prompt(answers_a: list, answers_b: list,
                             profile_a: dict, profile_b: dict,
                             relationship: str = "دوست") -> str:
    qa_a = "\n".join([f"سوال {i+1}: {ans}" for i, ans in enumerate(answers_a)])
    qa_b = "\n".join([f"سوال {i+1}: {ans}" for i, ans in enumerate(answers_b)])

    pa = profile_a.get("name") or "کاربر ۱"
    pb = profile_b.get("name") or "کاربر ۲"
    rel = relationship or "دوست"

    return f"""تو یه روانشناس رابطه‌ی خودمونی هستی.

⚠️ مهم: این دو نفر نسبت «{rel}» دارن — نه لزوماً دوست!
تحلیل رو دقیقاً بر اساس همین نسبت بنویس.

{pa} جواب داد:
{qa_a}

{pb} جواب داد:
{qa_b}

⚠️ قوانین محتوا:
- اگه کلمات رکیک یا نامناسب هست، نادیده‌شان بگیر
- تحلیل رو همیشه تمیز نگه دار

حالا رابطه‌شون رو تحلیل کن با این فرمت:

🤝 تیتر جذاب: (یه عنوان بامزه برای رابطه‌شون)

📊 شخصیت‌ها:
(۲-۳ خط — {pa} چطور آدمیه و {pb} چطور آدمیه)

🟢 نقاط مشترک:
• (۲-۳ مورد)

🔴 تفاوت‌ها:
• (۲-۳ مورد — با طنز ملایم)

⚠️ هشدار رابطه:
(چیزایی که باید حواسشون باشه — بر اساس نسبت «{rel}»)

💡 چطور رابطشون بهتر بشه:
• (۲ پیشنهاد کاربردی — مناسب نسبت «{rel}»)

🎯 پیشنهاد فعالیت مشترک:
(یه فعالیت مناسب نسبت «{rel}»)

💬 جمله‌ی پایانی:
(یه جمله‌ی بامزه و گرم)

قوانین نوشتاری:
- لحن رو بر اساس نسبت تنظیم کن:
  • دوست → خودمونی و بامزه
  • مادر/پدر و فرزند → محترمانه ولی گرم
  • خواهر/برادر → بامزه و صمیمی
  • زن و شوهر → عاشقانه ولی متعادل
  • همکار → حرفه‌ای ولی خودمونی
- اسم‌ها رو استفاده کن
- هر بخش با ایموجی جدا
- بین بخش‌ها خط خالی

مستقیم متن رو بنویس — بدون توضیح اضافه."""


# ================================================================
# Groq API — مستقیم و سریع ⚡
# ================================================================

def call_groq(prompt: str) -> str:
    """ارسال پرامپت به Groq — بدون مرورگر، ۲ ثانیه!"""
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {config.GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": config.GROQ_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "تو یه دستیار فارسی‌زبان هستی که تحلیل‌های روانشناسی با لحن خودمونی می‌نویسی."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 2000,
            },
            timeout=60,
        )

        if response.status_code != 200:
            print(f"[GROQ] خطا {response.status_code}: {response.text[:200]}")
            return "خطا در دریافت تحلیل — دوباره تلاش کن"

        result = response.json()
        text = result["choices"][0]["message"]["content"]
        return text.strip()

    except Exception as e:
        print(f"[GROQ] خطا: {type(e).__name__}: {e}")
        return "خطا در دریافت تحلیل — دوباره تلاش کن"


# ================================================================
# توابع اصلی
# ================================================================

async def analyze_personality(answers: list, user_name: str = "",
                               age: str = "", gender: str = "") -> str:
    prompt = build_personality_prompt(answers, user_name, age, gender)
    return call_groq(prompt)


async def analyze_friendship(answers_a: list, answers_b: list,
                              profile_a: dict, profile_b: dict,
                              relationship: str = "دوست") -> str:
    prompt = build_friendship_prompt(answers_a, answers_b,
                                     profile_a, profile_b, relationship)
    return call_groq(prompt)
