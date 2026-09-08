import os
import requests
import json
import time
import random
import yfinance as yf
import feedparser
import pandas as pd
from datetime import datetime, timedelta, timezone
from io import BytesIO

# ==========================================
# 1. ОПРЕДЕЛЕНИЕ ТИПА ВЫПУСКА (УТРО/ВЕЧЕР)
# ==========================================
def get_session_info():
    """Определяем тип выпуска и временной диапазон анализа"""
    msk_tz = timezone(timedelta(hours=3))
    now_msk = datetime.now(msk_tz)
    current_hour = now_msk.hour
    
    if current_hour < 15:
        session_type = "morning"
        session_name = "УТРЕННИЙ"
        period_start = now_msk.replace(hour=21, minute=0, second=0) - timedelta(days=1)
        period_text = f"с 21:00 {period_start.strftime('%d.%m')} по 09:00 {now_msk.strftime('%d.%m.%Y')} (ночная сессия)"
    else:
        session_type = "evening"
        session_name = "ВЕЧЕРНИЙ"
        period_start = now_msk.replace(hour=9, minute=0, second=0)
        period_text = f"с 09:00 по 21:00 {now_msk.strftime('%d.%m.%Y')} (дневная сессия)"
    
    return {
        "type": session_type,
        "name": session_name,
        "period": period_text,
        "date": now_msk.strftime("%d.%m.%Y"),
        "time": now_msk.strftime("%H:%M")
    }

# ==========================================
# 2. СБОР РЕАЛЬНЫХ ДАННЫХ (5 ВЕТОК)
# ==========================================
def get_fear_greed_index():
    try:
        url = "https://api.alternative.me/fng/?limit=1"
        response = requests.get(url, timeout=10).json()
        value = response['data'][0]['value']
        classification = response['data'][0]['value_classification']
        return int(value), classification
    except Exception as e:
        return None, f"Ошибка: {str(e)[:20]}"

def get_global_data():
    try:
        url = "https://api.coingecko.com/api/v3/global"
        response = requests.get(url, timeout=10).json()
        data = response['data']
        btc_dominance = data.get('market_cap_percentage', {}).get('btc', 0)
        total_market_cap = data.get('total_market_cap', {}).get('usd', 0)
        total_volume = data.get('total_volume', {}).get('usd', 0)
        return {
            'btc_dominance': btc_dominance,
            'total_market_cap': total_market_cap / 1_000_000_000,
            'total_volume': total_volume / 1_000_000_000
        }
    except Exception as e:
        return {'btc_dominance': 0, 'total_market_cap': 0, 'total_volume': 0}

def get_crypto_data():
    try:
        # ИСПРАВЛЕНО: убраны пробелы в URL
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana,ripple,toncoin&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true&include_market_cap=true"
        response = requests.get(url, timeout=10).json()
        data = []
        # ИСПРАВЛЕНО: убраны пробелы в ключах
        names = {"bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL", "ripple": "XRP", "toncoin": "TON"}
        for key, name in names.items():
            if key in response:
                price = response[key]['usd']
                change = response[key]['usd_24h_change']
                volume = response[key].get('usd_24h_vol', 0)
                vol_billion = volume / 1_000_000_000
                data.append(f"• {name}: ${price:,.2f} ({change:+.2f}%) | Объем: ${vol_billion:.2f}B")
        return "\n".join(data)
    except Exception as e:
        return f"• Крипта: Ошибка ({str(e)[:30]})"

def get_support_resistance():
    try:
        btc = yf.Ticker("BTC-USD")
        hist = btc.history(period="7d")
        if not hist.empty:
            high = hist['High'].max()
            low = hist['Low'].min()
            close = hist['Close'].iloc[-1]
            return f"BTC: Поддержка ${low:,.0f} | Сопротивление ${high:,.0f} | Текущая ${close:,.0f}"
        return "BTC: Недоступно"
    except Exception as e:
        return f"BTC: Ошибка ({str(e)[:30]})"

def get_finance_data():
    # ИСПРАВЛЕНО: убраны пробелы в ключах
    tickers = {
        "GC=F": "Золото",
        "SI=F": "Серебро",
        "BZ=F": "Нефть Brent",
        "^GSPC": "S&P 500",
        "NVDA": "NVIDIA",
        "DX-Y.NYB": "Индекс доллара (DXY)"
    }
    data = []
    for ticker, name in tickers.items():
        try:
            asset = yf.Ticker(ticker)
            info = asset.history(period="5d")
            if not info.empty and len(info) >= 2:
                price = info['Close'].iloc[-1]
                prev_price = info['Close'].iloc[-2]
                change = ((price - prev_price) / prev_price) * 100
                data.append(f"• {name}: ${price:,.2f} ({change:+.2f}%)")
            elif not info.empty:
                price = info['Close'].iloc[-1]
                data.append(f"• {name}: ${price:,.2f} (изменение недоступно)")
            else:
                data.append(f"• {name}: данных нет")
        except Exception as e:
            data.append(f"• {name}: данных нет")
    return "\n".join(data)

def format_time_ago(published_time):
    try:
        msk_tz = timezone(timedelta(hours=3))
        now = datetime.now(msk_tz)
        if hasattr(published_time, 'tm_year'):
            pub_dt = datetime(*published_time[:6], tzinfo=msk_tz)
        elif isinstance(published_time, datetime):
            pub_dt = published_time
        else:
            return ""
        if pub_dt.tzinfo is None:
            pub_dt = pub_dt.replace(tzinfo=timezone.utc).astimezone(msk_tz)
        diff = now - pub_dt
        hours = int(diff.total_seconds() / 3600)
        if hours < 1:
            return "только что"
        elif hours < 24:
            return f"{hours} ч. назад"
        else:
            days = hours // 24
            return f"{days} дн. назад"
    except:
        return ""

def get_news_data():
    try:
        feeds = [
            "http://feeds.reuters.com/reuters/businessNews",
            "https://cointelegraph.com/rss"
        ]
        headlines = []
        for feed_url in feeds:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:3]:
                title = entry.title
                link = entry.get('link', '')
                time_ago = format_time_ago(entry.get('published_parsed'))
                title_safe = title.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('`', '\\`')
                time_prefix = f"[{time_ago}] " if time_ago else ""
                if link:
                    headlines.append(f"• {time_prefix}[{title_safe}]({link})")
                else:
                    headlines.append(f"• {time_prefix}{title_safe}")
        return "\n".join(headlines[:5])
    except Exception as e:
        return "• Новости: Ошибка сбора данных"

# ==========================================
# 3. ИИ-АНАЛИЗ (5 ВЕТОК)
# ==========================================
def get_ai_analysis(session_info, fear_greed, global_data, crypto, support_resistance, finance, news):
    api_key = os.environ.get("OPENROUTER_API_KEY")
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    models = [
        "inclusionai/ling-3.0-flash-fin:free",
        "nvidia/nemotron-3-super-120b-a12b:free",
        "google/gemma-4-31b-it:free",
        "google/gemma-4-26b-a4b-it:free",
        "nvidia/nemotron-3.5-lightning:free",
        "cohere/north-mini-code:free",
        "inclusionai/ling-3.0-flash-sante:free",
        "dots-studio/dots-3-note-preview:free",
        "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
        "nvidia/nemotron-3.5-content-safety:free",
        "liquid/lfm-2.5-2.6b:free",
    ]
    
    fg_value, fg_class = fear_greed
    btc_dom = global_data['btc_dominance']
    total_mcap = global_data['total_market_cap']
    
    if fg_value is None:
        fg_value, fg_class, fg_emoji, fg_signal = 50, "Neutral", "😐", "НЕЙТРАЛЬНО"
    elif fg_value <= 24:
        fg_emoji, fg_signal = "😰", "ПАНИКА"
    elif fg_value <= 49:
        fg_emoji, fg_signal = "😟", "СТРАХ"
    elif fg_value <= 51:
        fg_emoji, fg_signal = "😐", "НЕЙТРАЛЬНО"
    elif fg_value <= 74:
        fg_emoji, fg_signal = "😊", "ЖАДНОСТЬ"
    else:
        fg_emoji, fg_signal = "🤑", "ЭКСТРЕМАЛЬНАЯ ЖАДНОСТЬ"
    
    prompt = f"""Ты — профессиональный ИИ-аналитик финансовых рынков.

КОНТЕКСТ:
- Тип: {session_info['name']} выпуск
- Дата: {session_info['date']}
- ПЕРИОД: {session_info['period']}

ДАННЫЕ:
[ИНДЕКС]: {fg_value}/100 ({fg_class}) → {fg_emoji} {fg_signal}
[DOM BTC]: {btc_dom:.1f}%
[MCAP]: ${total_mcap:.0f}B
[КРИПТА]: {crypto}
[УРОВНИ]: {support_resistance}
[РЫНКИ]: {finance}
[НОВОСТИ]: {news}

ПРАВИЛА:
1. НЕ используй ##, >, ---, таблицы
2. Используй **жирный**, эмодзи
3. Сохраняй ссылки [текст](url)
4. Пиши подробно

СТРУКТУРА:

 **ИИ АНАЛИТИК: {session_info['name']} ОБЗОР** — {session_info['date']}

📈 **ПЕРИОД:** {session_info['period']}

️ Сначала риски!

🪙 **1. КРИПТОРЫНОК**
- BTC, ETH, SOL, XRP: цены, объёмы
- Уровни BTC
- Доминация: {btc_dom:.1f}%
- Капитализация: ${total_mcap:.0f}B
- Анализ

🛢️ **2. СЫРЬЁ**
- Золото, Серебро, Нефть
- Анализ

🌍 **3. МАКРО-ФОН**
- S&P 500, DXY
- Индекс: {fg_value}/100
- Риск-он/офф?

🌐 **4. ГЕОПОЛИТИКА**
- Новости
- Влияние

 **5. IT И ТЕХНОЛОГИИ**
- NVIDIA
- Анализ

 **СВЯЗЬ ВЕТОК:**
- Комплексный вывод

🎯 **ТОРГОВЫЕ ИДЕИ (3 совета):**
1️⃣ [Действие]: [Пояснение]
2️⃣ [Действие]: [Пояснение]
3️⃣ [Действие]: [Пояснение]

⚡ **QUICK STATS:**
- 🔵 BTC: [цена] ([изменение]%)
- 🟢 ETH: [цена] ([изменение]%)
-  SOL: [цена] ([изменение]%)
- 🔵 XRP: [цена] ([изменение]%)
- 🟡 Индекс: {fg_value}/100
-  Dom BTC: {btc_dom:.1f}%
- 🔵 MCAP: ${total_mcap:.0f}B
- S&P 500: [данные]
- Золото: [данные]
- Нефть: [данные]
- NVIDIA: [данные]
- DXY: [данные]

⚠️ **РИСК:**
"Торговля сопряжена с риском. Вы можете потерять ВЕСЬ депозит."

⚖️ **ДИСКЛЕЙМЕР:**
"⚠️ Информация НЕ является рекомендацией. DYOR."

Объём: 3500-4000 символов. ПРИСТУПАЙ!"""
    
    for model in models:
        try:
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}]
            }
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/volk6691ilya-lgtm/ember-watch",
                "X-Title": "Ember Watch System"
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    content = result['choices'][0]['message']['content']
                    if content and len(content.strip()) > 200:
                        return content
        except:
            continue
    
    return None

# ==========================================
# 4. ФУТЕР ПОСТА
# ==========================================
def get_post_footer(session_info):
    msk_tz = timezone(timedelta(hours=3))
    now_msk = datetime.now(msk_tz)
    
    if session_info['type'] == 'morning':
        next_time, next_type = "21:00", "вечерний"
        next_date = now_msk.strftime("%d.%m.%Y")
    else:
        next_time, next_type = "09:00", "утренний"
        next_date = (now_msk + timedelta(days=1)).strftime("%d.%m.%Y")
    
    return f"""
🔔 **СЛЕДУЮЩИЙ ВЫПУСК:** {next_type} в {next_time} МСК ({next_date})

🔔 **ПОЖАРНЫЙ ШПИОН** — экстренные сигналы

👍 Ставь реакцию если полезно!"""

# ==========================================
# 5. УМНОЕ РАЗДЕЛЕНИЕ НА ЧАСТИ (УЛУЧШЕНО)
# ==========================================
def smart_split_text(text, max_len=3800):
    """Разбивает текст по разделам, не разрывая их"""
    # Находим все заголовки разделов
    sections = []
    current_section = ""
    
    for line in text.split('\n'):
        # Проверяем, начинается ли строка с заголовка раздела
        if any(marker in line for marker in ['🪙 **1.', '️ **2.', '🌍 **3.', '🌐 **4.', '💻 **5.', '🔗 **', ' **', '⚡ **', '⚠️ **', '⚖️ **']):
            # Сохраняем предыдущий раздел
            if current_section.strip():
                sections.append(current_section.strip())
            current_section = line + '\n'
        else:
            current_section += line + '\n'
    
    # Добавляем последний раздел
    if current_section.strip():
        sections.append(current_section.strip())
    
    # Теперь собираем части, не разрывая разделы
    parts = []
    current_part = ""
    
    for section in sections:
        if len(current_part) + len(section) + 2 <= max_len:
            current_part += section + "\n\n"
        else:
            if current_part.strip():
                parts.append(current_part.strip())
            current_part = section + "\n\n"
    
    if current_part.strip():
        parts.append(current_part.strip())
    
    return parts

# ==========================================
# 6. КОЛЛЕКЦИЯ КАРТИНОК (ОЧИЩЕНО ОТ ПРОБЕЛОВ)
# ==========================================
COVER_IMAGES = {
    'bullish': [
        "https://res.cloudinary.com/yln8uskh/image/upload/v1788870775/bullish1.jpg",
        "https://res.cloudinary.com/yln8uskh/image/upload/v1788870869/bullish2.jpg",
        "https://res.cloudinary.com/yln8uskh/image/upload/v1788870869/bullish4.jpg",
        "https://res.cloudinary.com/yln8uskh/image/upload/v1788871107/bullish3.jpg",
        "https://res.cloudinary.com/yln8uskh/image/upload/v1788871108/bullish5.jpg",
    ],
    'bearish': [
        "https://res.cloudinary.com/yln8uskh/image/upload/v1788871107/bearish2.jpg",
        "https://res.cloudinary.com/yln8uskh/image/upload/v1788871107/bearish1.jpg",
        "https://res.cloudinary.com/yln8uskh/image/upload/v1788871107/bearish3.jpg",
        "https://res.cloudinary.com/yln8uskh/image/upload/v1788871107/bearish4.jpg",
        "https://res.cloudinary.com/yln8uskh/image/upload/v1788871108/bearish5.jpg",
    ],
    'neutral': [
        "https://res.cloudinary.com/yln8uskh/image/upload/v1788871108/neutral1.jpg",
        "https://res.cloudinary.com/yln8uskh/image/upload/v1788871108/neutral2.jpg",
        "https://res.cloudinary.com/yln8uskh/image/upload/v1788871108/neutral3.jpg",
        "https://res.cloudinary.com/yln8uskh/image/upload/v1788871108/neutral4.jpg",
        "https://res.cloudinary.com/yln8uskh/image/upload/v1788871109/neutral5.jpg",
    ]
}

def get_cover_image(fear_greed):
    fg_value = fear_greed[0] if fear_greed and fear_greed[0] else 50
    mood = 'bearish' if fg_value <= 30 else ('bullish' if fg_value >= 70 else 'neutral')
    
    image_url = random.choice(COVER_IMAGES.get(mood, [])) if COVER_IMAGES.get(mood) else None
    if not image_url:
        return None
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(image_url, headers=headers, timeout=30)
        if response.status_code == 200 and len(response.content) > 1000:
            return BytesIO(response.content)
        return None
    except:
        return None

# ==========================================
# 7. ОТПРАВКА В TELEGRAM
# ==========================================
def send_to_telegram(text, fear_greed=None):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    channel_id = os.environ.get("TELEGRAM_CHANNEL_ID")
    
    if not bot_token or not channel_id:
        print("❌ Ошибка: токены не установлены")
        return
    
    image_buffer = get_cover_image(fear_greed)
    caption = "💼 **ИИ АНАЛИТИК НА СВЯЗИ**\n\nСистема завершила анализ 5 ветвей рынка 👇"
    
    if image_buffer:
        files = {
            'photo': ('cover.jpg', image_buffer, 'image/jpeg'),
            'chat_id': (None, channel_id),
            'caption': (None, caption)
        }
        response = requests.post(f"https://api.telegram.org/bot{bot_token}/sendPhoto", files=files, timeout=30)
        if response.status_code != 200:
            print(f"⚠️ Ошибка картинки: {response.text}")
        time.sleep(2)
    
    parts = smart_split_text(text, max_len=3800)
    total = len(parts)
    
    for i, part in enumerate(parts):
        if i > 0:
            time.sleep(3)
        
        if total > 1:
            header = f"📄 **ЧАСТЬ {i+1}/{total}**\n\n"
            footer = f"\n\n_...продолжение (часть {i+1}/{total})_" if i < total - 1 else ""
            text_part = header + part + footer
        else:
            text_part = part
        
        if len(text_part) > 4090:
            text_part = text_part[:4080] + "\n\n_...обрезано_"
        
        response = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={
                "chat_id": channel_id,
                "text": text_part,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            },
            timeout=15
        )
        
        if response.status_code == 200:
            print(f"✅ Часть {i+1}/{total} отправлена")
        else:
            print(f"❌ Ошибка: {response.text}")

# ==========================================
# 8. ГЛАВНЫЙ ЗАПУСК
# ==========================================
def main():
    print("🚀 Запуск ИИ Аналитика v31.3 (Умное разбиение + исправлены пробелы)...")
    
    session_info = get_session_info()
    print(f"   Тип: {session_info['name']} | {session_info['period']}")
    
    print("📡 Сбор данных...")
    fear_greed = get_fear_greed_index()
    global_data = get_global_data()
    crypto = get_crypto_data()
    support = get_support_resistance()
    finance = get_finance_data()
    news = get_news_data()
    
    print("🧠 ИИ-анализ...")
    analysis = get_ai_analysis(session_info, fear_greed, global_data, crypto, support, finance, news)
    
    if not analysis:
        print("⚠️ ИИ не ответил, используем резерв")
        fg_value = fear_greed[0] if fear_greed and fear_greed[0] else 50
        fg_class = fear_greed[1] if fear_greed and len(fear_greed) > 1 else "Neutral"
        analysis = f"""⚠️ **ИИ временно недоступен**. Свежие данные:

 **КРИПТОРЫНОК:**
{crypto}

📊 **РЫНКИ:**
{finance}

🌡️ **ИНДЕКС:** {fg_value}/100 ({fg_class})"""
    
    full_text = analysis + "\n\n" + get_post_footer(session_info)
    print(f"📏 Длина: {len(full_text)} символов")
    
    print("📤 Публикация...")
    send_to_telegram(full_text, fear_greed)
    print("✅ Готово!")

if __name__ == "__main__":
    main()
