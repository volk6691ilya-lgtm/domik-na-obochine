import os
import requests
import json
import time
import random
import re
import yfinance as yf
import feedparser
import pandas as pd
from datetime import datetime, timedelta, timezone
from io import BytesIO

# ==========================================
# 0. УТИЛИТЫ (КЭШ, ОШИБКИ, РОТАЦИЯ)
# ==========================================
def send_error_alert(message):
    """Отправляет уведомление об ошибке в системный канал"""
    error_channel = os.environ.get("TELEGRAM_ERROR_CHANNEL_ID")
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if error_channel and bot_token:
        try:
            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                "chat_id": error_channel,
                "text": f"⚠️ **СИСТЕМНАЯ ОШИБКА:**\n`{message}`",
                "parse_mode": "Markdown"
            }, timeout=10)
        except:
            pass

def get_cached_data(key, fetch_func, ttl=3600):
    """Кэширует данные в файл, чтобы не дёргать API лишний раз"""
    cache_file = "api_cache.json"
    now = time.time()
    try:
        if os.path.exists(cache_file):
            with open(cache_file, "r") as f:
                cache = json.load(f)
            if key in cache and (now - cache[key]['time']) < ttl:
                return cache[key]['data']
    except:
        cache = {}
    
    data = fetch_func()
    cache[key] = {'time': now, 'data': data}
    with open(cache_file, "w") as f:
        json.dump(cache, f)
    return data

def get_shuffled_models():
    """Перемешивает резервные модели, но оставляет лучшую первой"""
    models = [
        "inclusionai/ling-3.0-flash-fin:free",  # 🏆 Всегда первая
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
    # Перемешиваем всё кроме первой (индекс 0)
    backup_models = models[1:]
    random.shuffle(backup_models)
    return [models[0]] + backup_models

# ==========================================
# 1. ОПРЕДЕЛЕНИЕ ТИПА ВЫПУСКА
# ==========================================
def get_session_info():
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
# 2. СБОР ДАННЫХ (С КЭШИРОВАНИЕМ)
# ==========================================
def get_fear_greed_index():
    def fetch():
        url = "https://api.alternative.me/fng/?limit=1"
        response = requests.get(url, timeout=10).json()
        value = response['data'][0]['value']
        classification = response['data'][0]['value_classification']
        return int(value), classification
    try:
        return get_cached_data("fng", fetch, ttl=3600)
    except Exception as e:
        send_error_alert(f"FearGreed API: {e}")
        return 50, "Neutral"

def get_global_data():
    def fetch():
        url = "https://api.coingecko.com/api/v3/global"
        response = requests.get(url, timeout=10).json()
        data = response['data']
        return {
            'btc_dominance': data.get('market_cap_percentage', {}).get('btc', 0),
            'total_market_cap': data.get('total_market_cap', {}).get('usd', 0) / 1_000_000_000,
            'total_volume': data.get('total_volume', {}).get('usd', 0) / 1_000_000_000
        }
    try:
        return get_cached_data("global", fetch, ttl=3600)
    except Exception as e:
        send_error_alert(f"CoinGecko Global: {e}")
        return {'btc_dominance': 0, 'total_market_cap': 0, 'total_volume': 0}

def get_crypto_data():
    def fetch():
        # ИСПРАВЛЕНО: убраны лишние пробелы в URL и ключах
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana,ripple,toncoin&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true&include_market_cap=true"
        response = requests.get(url, timeout=10).json()
        data = []
        names = {"bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL", "ripple": "XRP", "toncoin": "TON"}
        for key, name in names.items():
            if key in response:
                price = response[key]['usd']
                change = response[key]['usd_24h_change']
                volume = response[key].get('usd_24h_vol', 0)
                vol_billion = volume / 1_000_000_000
                data.append(f"• {name}: ${price:,.2f} ({change:+.2f}%) | Объем: ${vol_billion:.2f}B")
        return "\n".join(data)
    try:
        return get_cached_data("crypto", fetch, ttl=1800)
    except Exception as e:
        send_error_alert(f"CoinGecko Prices: {e}")
        return "• Крипта: Ошибка API"

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
        send_error_alert(f"Yahoo Finance BTC: {e}")
        return f"BTC: Ошибка ({str(e)[:30]})"

def get_finance_data():
    # ИСПРАВЛЕНО: убраны лишние пробелы в ключах словаря
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
        if hours < 1: return "только что"
        elif hours < 24: return f"{hours} ч. назад"
        else: return f"{hours // 24} дн. назад"
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
        send_error_alert(f"RSS News: {e}")
        return "• Новости: Ошибка сбора данных"

# ==========================================
# 3. ИИ-АНАЛИЗ
# ==========================================
def get_ai_analysis(session_info, fear_greed, global_data, crypto, support_resistance, finance, news):
    api_key = os.environ.get("OPENROUTER_API_KEY")
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    # Получаем перемешанный список моделей
    models = get_shuffled_models()
    
    fg_value, fg_class = fear_greed
    btc_dom = global_data['btc_dominance']
    total_mcap = global_data['total_market_cap']
    
    if fg_value is None:
        fg_value, fg_class, fg_emoji, fg_signal = 50, "Neutral", "😐", "НЕЙТРАЛЬНО"
    elif fg_value <= 24: fg_emoji, fg_signal = "😰", "ПАНИКА"
    elif fg_value <= 49: fg_emoji, fg_signal = "😟", "СТРАХ"
    elif fg_value <= 51: fg_emoji, fg_signal = "", "НЕЙТРАЛЬНО"
    elif fg_value <= 74: fg_emoji, fg_signal = "😊", "ЖАДНОСТЬ"
    else: fg_emoji, fg_signal = "🤑", "ЭКСТРЕМАЛЬНАЯ ЖАДНОСТЬ"
    
    prompt = f"""Ты — профессиональный ИИ-аналитик финансовых рынков. Создай ОБЪЕКТИВНЫЙ обзор рынка для Telegram-канала.

КОНТЕКСТ:
- Тип: {session_info['name']} выпуск
- Дата: {session_info['date']}
- ПЕРИОД АНАЛИЗА: {session_info['period']}

ДАННЫЕ:
[ИНДЕКС СТРАХА/ЖАДНОСТИ]: {fg_value}/100 ({fg_class}) → {fg_emoji} {fg_signal}
[ДОМИНАЦИЯ BTC]: {btc_dom:.1f}%
[КАПИТАЛИЗАЦИЯ]: ${total_mcap:.0f}B
[КРИПТА]: {crypto}
[УРОВНИ BTC]: {support_resistance}
[РЫНКИ]: {finance}
[НОВОСТИ]: {news}

⚠️ КРИТИЧЕСКИ ВАЖНЫЕ ПРАВИЛА ФОРМАТИРОВАНИЯ:
1. НЕ используй символы ## (заголовки Markdown)
2. НЕ используй символ > (цитаты)
3. НЕ используй --- (разделители)
4. НЕ используй таблицы с |
5. Используй ТОЛЬКО: обычный текст, **жирный шрифт**, эмодзи для структуры
6. Сохраняй КЛИКАБЕЛЬНЫЕ ССЫЛКИ в новостях в формате [текст](url) — НЕ УДАЛЯЙ ИХ!
7. НЕ сокращай блоки — пиши каждый раздел полноценно

СТРУКТУРА ПОСТА (ВСЕ БЛОКИ ОБЯЗАТЕЛЬНЫ):

 **ИИ АНАЛИТИК: {session_info['name']} ОБЗОР** — {session_info['date']}

📈 **ПЕРИОД АНАЛИЗА:** {session_info['period']}

⚠️ Сначала риски, потом возможности!

🪙 **1. КРИПТОРЫНОК**
- BTC, ETH, SOL, XRP: цены, объёмы, изменения за период
- Уровни поддержки/сопротивления BTC
- Доминация BTC: {btc_dom:.1f}% — что это значит
- Общая капитализация: ${total_mcap:.0f}B
- Анализ: что происходит и почему

🛢️ **2. СЫРЬЁ**
- Золото, Серебро, Нефть Brent: цены и изменения из блока [РЫНКИ]
- Связь с инфляцией и риск-аппетитом
- Анализ: куда движутся "умные деньги"

🌍 **3. МАКРО-ФОН**
- S&P 500, DXY (индекс доллара): цены и изменения из блока [РЫНКИ]
- Индекс страха/жадности: {fg_value}/100 ({fg_class})
- Анализ: риск-он или риск-офф?

 **4. ГЕОПОЛИТИКА**
- Новости из блока [НОВОСТИ] (регуляция, законы, санкции)
- СОХРАНЯЙ КЛИКАБЕЛЬНЫЕ ССЫЛКИ [текст](url) — НЕ ПЕРЕПИСЫВАЙ ЗАГОЛОВКИ!
- Временные метки [X ч. назад]
- Влияние на рынки

💻 **5. IT И ТЕХНОЛОГИИ**
- NVIDIA: цена и изменение из блока [РЫНКИ]
- Новости про ETF, биржи, институционалов
- Анализ: куда движется "умный капитал"

🔗 **СВЯЗЬ ВЕТОК:**
- Как геополитика/IT влияют на крипту
- Комплексный вывод: что это значит для рынка

🎯 **ТОРГОВЫЕ ИДЕИ (3 совета):**
1️⃣ [Конкретное действие]: [Пояснение с процентами и уровнями]
2️⃣ [Конкретное действие]: [Пояснение с процентами и уровнями]
3️⃣ [Конкретное действие]: [Пояснение с процентами и уровнями]

⚡ **QUICK STATS (ОБЯЗАТЕЛЬНО ВСЕ ПУНКТЫ, НЕ СОКРАЩАЙ!):**
Используй цветовую кодировку:
- 🟢 зелёный = рост/бычий сигнал
- 🔴 красный = падение/медвежий сигнал
- 🟡 жёлтый = предупреждение/нейтрально
- 🔵 синий = факт/объём

Включи ВСЕ эти метрики:
- 🔵 BTC: [цена] ([изменение]%) — [комментарий]
- 🟢 ETH: [цена] ([изменение]%) — [комментарий]
- 🔵 SOL: [цена] ([изменение]%) — [комментарий]
- 🔵 XRP: [цена] ([изменение]%) — [комментарий]
- 🟡 Индекс страха/жадности: {fg_value}/100 — [комментарий]
- 🔵 Доминация BTC: {btc_dom:.1f}% — [комментарий]
- 🔵 Общая капитализация: ${total_mcap:.0f}B — [комментарий]
- [цвет] S&P 500: [из данных] — [комментарий]
- [цвет] Золото: [из данных] — [комментарий]
- [цвет] Нефть Brent: [из данных] — [комментарий]
- [цвет] NVIDIA: [из данных] — [комментарий]
- [цвет] DXY: [из данных] — [комментарий]

⚠️ **РИСК-ПРЕДУПРЕЖДЕНИЕ:**
"Торговля на финансовых рынках сопряжена с высоким риском потери средств. Вы можете потерять ВЕСЬ депозит. Никогда не инвестируйте больше, чем готовы потерять полностью."

⚖️ **ДИСКЛЕЙМЕР (ТОЧНЫЙ ТЕКСТ, НЕ СОКРАЩАТЬ!):**
"⚠️ Вся информация носит ИСКЛЮЧИТЕЛЬНО ознакомительный характер и НЕ является индивидуальной инвестиционной рекомендацией. Финансовые рынки сопряжены с высоким риском потери средств (вплоть до 100% депозита). Вы действуете на свой страх и риск (DYOR — Do Your Own Research, проводите собственное исследование). Прошлые результаты не гарантируют будущую прибыль."

ПРАВИЛА СТИЛЯ:
- Тон: профессиональный, но живой (не сухой)
- Сленг с расшифровками в скобках: "лонг сквизнуло (long squeeze — принудительное закрытие позиций)"
- Конкретные цифры и проценты
- БЕЗ ВОДЫ: каждое предложение должно нести информацию
- Объём: 3500-4000 символов (подробно, но без повторов)
- Используй эмодзи: 📊📉💹💰💵🎯🌐🛑⚠️🔍🔔
- НЕ добавляй информацию о следующем выпуске — система добавит автоматически

ПРИСТУПАЙ!"""
    
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
            elif response.status_code == 429:
                continue # Rate limit, пробуем следующую
        except Exception as e:
            continue
            
    send_error_alert("Все ИИ-модели OpenRouter недоступны или вернули пустой ответ.")
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
🔔 **СЛЕДУЮЩИЙ ВЫПУСК:** {next_type} обзор в {next_time} МСК ({next_date})

🔔🚨 **ПОЖАРНЫЙ ШПИОН** — система экстренных оповещений
Система автоматически мониторит рынки и геополитику. При резких изменениях в канал придёт экстренный сигнал.

👍 Если обзор был полезен — ставь реакцию!
📢 Подписывайся на канал, чтобы не пропустить важные сигналы."""

# ==========================================
# 5. УМНОЕ РАЗДЕЛЕНИЕ НА ЧАСТИ (ИСПРАВЛЕНО)
# ==========================================
def smart_split_text(text, max_len=3800):
    """Разбивает текст по логическим разделам, не разрывая их"""
    # Ищем заголовки разделов
    headers_pattern = r'(?=(?:🪙 1\.|🛢️ 2\.|🌍 3\.|🌐 4\.|💻 5\.|🔗|🎯||⚠️|⚖️))'
    sections = re.split(headers_pattern, text)
    
    parts = []
    current_part = ""
    
    for section in sections:
        if not section.strip():
            continue
            
        if len(current_part) + len(section) <= max_len:
            current_part += section
        else:
            if current_part:
                parts.append(current_part.strip())
            
            # Если один раздел слишком длинный, режем его по абзацам
            if len(section) > max_len:
                paragraphs = section.split('\n\n')
                for para in paragraphs:
                    if len(para) > max_len:
                        sentences = re.split(r'(?<=\.) ', para)
                        temp = ""
                        for sent in sentences:
                            if len(temp) + len(sent) <= max_len:
                                temp += sent
                            else:
                                if temp: parts.append(temp.strip())
                                temp = sent
                        current_part = temp
                    elif len(current_part) + len(para) <= max_len:
                        current_part += para + "\n\n"
                    else:
                        parts.append(current_part.strip())
                        current_part = para + "\n\n"
            else:
                current_part = section
    
    if current_part.strip():
        parts.append(current_part.strip())
        
    return parts

# ==========================================
# 6. КОЛЛЕКЦИЯ КАРТИНОК
# ==========================================
# ЗАМЕНИ ССЫЛКИ НИЖЕ НА СВОИ ИЗ РЕПОЗИТОРИЯ (raw.githubusercontent.com/...)
COVER_IMAGES = {
    'bullish': [
        "https://github.com/volk6691ilya-lgtm/ember-watch/blob/main/images/bullish1.jpeg?raw=true",
        "https://github.com/volk6691ilya-lgtm/ember-watch/blob/main/images/bullish2.jpeg?raw=true",
        "https://github.com/volk6691ilya-lgtm/ember-watch/blob/main/images/bullish3.jpeg?raw=true",
        "https://github.com/volk6691ilya-lgtm/ember-watch/blob/main/images/bullish4.jpeg?raw=true",
        "https://github.com/volk6691ilya-lgtm/ember-watch/blob/main/images/bullish5.jpeg?raw=true",
    ],
    'bearish': [
        "https://github.com/volk6691ilya-lgtm/ember-watch/blob/main/images/bearish1.jpeg?raw=true",
        "https://github.com/volk6691ilya-lgtm/ember-watch/blob/main/images/bearish2.jpeg?raw=true",
        "https://github.com/volk6691ilya-lgtm/ember-watch/blob/main/images/bearish3.jpeg?raw=true",
        "https://github.com/volk6691ilya-lgtm/ember-watch/blob/main/images/bearish4.jpeg?raw=true",
        "https://github.com/volk6691ilya-lgtm/ember-watch/blob/main/images/bearish5.jpeg?raw=true",
    ],
    'neutral': [
        "https://github.com/volk6691ilya-lgtm/ember-watch/blob/main/images/neutral1.jpeg?raw=true",
        "https://github.com/volk6691ilya-lgtm/ember-watch/blob/main/images/neutral2.jpeg?raw=true",
        "https://github.com/volk6691ilya-lgtm/ember-watch/blob/main/images/neutral3.jpeg?raw=true",
        "https://github.com/volk6691ilya-lgtm/ember-watch/blob/main/images/neutral4.jpeg?raw=true",
        "https://github.com/volk6691ilya-lgtm/ember-watch/blob/main/images/neutral5.jpeg?raw=true",
    ]
}

def get_cover_image(fear_greed):
    fg_value = fear_greed[0] if fear_greed and fear_greed[0] else 50
    mood = 'bearish' if fg_value <= 30 else ('bullish' if fg_value >= 70 else 'neutral')
    
    image_url = random.choice(COVER_IMAGES.get(mood, [])) if COVER_IMAGES.get(mood) else None
    if not image_url:
        all_images = [img for imgs in COVER_IMAGES.values() for img in imgs]
        image_url = random.choice(all_images) if all_images else None
    
    if not image_url:
        send_error_alert("Нет доступных ссылок на картинки в COVER_IMAGES.")
        return None
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"
        }
        response = requests.get(image_url, headers=headers, timeout=30)
        if response.status_code == 200 and len(response.content) > 1000:
            return BytesIO(response.content)
        else:
            send_error_alert(f"Ошибка скачивания картинки: статус {response.status_code}")
            return None
    except Exception as e:
        send_error_alert(f"Критическая ошибка при скачивании картинки: {e}")
        return None

# ==========================================
# 7. ОТПРАВКА В TELEGRAM
# ==========================================
def send_to_telegram(text, fear_greed=None):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    channel_id = os.environ.get("TELEGRAM_CHANNEL_ID")
    
    if not bot_token or not channel_id:
        send_error_alert("TELEGRAM_BOT_TOKEN или TELEGRAM_CHANNEL_ID не установлены!")
        return
    
    image_buffer = get_cover_image(fear_greed)
    caption = " **ИИ АНАЛИТИК НА СВЯЗИ**\n\nСистема завершила анализ 5 ветвей рынка. Полный разбор ниже 👇"
    
    if image_buffer:
        files = {
            'photo': ('cover.jpg', image_buffer, 'image/jpeg'),
            'chat_id': (None, channel_id),
            'caption': (None, caption),
            'parse_mode': (None, 'Markdown')
        }
        response = requests.post(f"https://api.telegram.org/bot{bot_token}/sendPhoto", files=files, timeout=30)
        if response.status_code != 200:
            send_error_alert(f"Ошибка отправки картинки: {response.text}")
        time.sleep(2)
    
    parts = smart_split_text(text, max_len=3800)
    total_parts = len(parts)
    
    for i, part in enumerate(parts):
        if i > 0: time.sleep(3)
        
        if total_parts > 1:
            header = f"📄 **ЧАСТЬ {i+1}/{total_parts}**\n\n"
            footer_text = f"\n\n_...продолжение следует (часть {i+1}/{total_parts})_" if i < total_parts - 1 else ""
            part_with_indicator = header + part + footer_text
        else:
            part_with_indicator = part
        
        if len(part_with_indicator) > 4090:
            part_with_indicator = part_with_indicator[:4080] + "\n\n_...текст обрезан_"
        
        text_payload = {
            "chat_id": channel_id,
            "text": part_with_indicator,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        
        response = requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json=text_payload, timeout=15)
        if response.status_code != 200:
            send_error_alert(f"Ошибка отправки части {i+1}: {response.text}")

# ==========================================
# 8. ГЛАВНЫЙ ЗАПУСК
# ==========================================
def main():
    print("🚀 Запуск ИИ Аналитика v31.0 (Ротация моделей + Кэш + Умное разбиение)...")
    
    session_info = get_session_info()
    print(f"   Тип: {session_info['name']} выпуск | Период: {session_info['period']}")
    
    print("📡 Сбор данных (5 веток)...")
    fear_greed = get_fear_greed_index()
    global_data = get_global_data()
    crypto = get_crypto_data()
    support_resistance = get_support_resistance()
    finance = get_finance_data()
    news = get_news_data()
    
    print("🧠 ИИ-анализ (30-60 секунд)...")
    analysis = get_ai_analysis(session_info, fear_greed, global_data, crypto, support_resistance, finance, news)
    
    if not analysis:
        print("⚠️ ИИ не ответил. Используем резервный текст.")
        fg_value = fear_greed[0] if fear_greed and fear_greed[0] is not None else 50
        fg_class = fear_greed[1] if fear_greed and len(fear_greed) > 1 else "Neutral"
        analysis = f"""⚠️ **Внимание:** Сервисы ИИ-анализа временно перегружены. Свежие данные ниже актуальны.

🪙 **КРИПТОРЫНОК:**
{crypto}

📊 **РЫНКИ И СЫРЬЁ:**
{finance}

🌡️ **ИНДЕКС СТРАХА/ЖАДНОСТИ:** {fg_value}/100 ({fg_class})

🔍 Полный анализ с торговыми идеями будет в следующем выпуске."""
    
    print("📎 Добавление футера...")
    full_text = analysis + "\n\n" + get_post_footer(session_info)
    print(f"📏 Длина текста: {len(full_text)} символов")
    
    print("📤 Публикация...")
    send_to_telegram(full_text, fear_greed)
    print("✅ Миссия выполнена.")

if __name__ == "__main__":
    main()
