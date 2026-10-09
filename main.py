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
from ai_models_config import get_models_for_task  # Единственное отличие от v31.7: берем модели из конфига

# ==========================================
# 0. НАБЛЮДАЕМОСТЬ
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
        except Exception:
            pass

# ==========================================
# 1. ОПРЕДЕЛЕНИЕ ТИПА ВЫПУСКА (СТРОГИЕ 12 ЧАСОВ)
# ==========================================
def get_session_info():
    msk_tz = timezone(timedelta(hours=3))
    now_msk = datetime.now(msk_tz)
    current_hour = now_msk.hour
    
    if current_hour < 15:
        session_type = "morning"
        session_name = "УТРЕННИЙ"
        period_start = now_msk.replace(hour=21, minute=0, second=0) - timedelta(days=1)
        period_end = now_msk.replace(hour=9, minute=0, second=0)
        period_text = f"с 21:00 {period_start.strftime('%d.%m')} по 09:00 {now_msk.strftime('%d.%m.%Y')} (ночная сессия)"
    else:
        session_type = "evening"
        session_name = "ВЕЧЕРНИЙ"
        period_start = now_msk.replace(hour=9, minute=0, second=0)
        period_end = now_msk.replace(hour=21, minute=0, second=0)
        period_text = f"с 09:00 по 21:00 {now_msk.strftime('%d.%m.%Y')} (дневная сессия)"
    
    return {
        "type": session_type,
        "name": session_name,
        "period": period_text,
        "date": now_msk.strftime("%d.%m.%Y"),
        "time": now_msk.strftime("%H:%M")
    }

# ==========================================
# 2. СБОР ДАННЫХ
# ==========================================
def get_fear_greed_index():
    try:
        url = "https://api.alternative.me/fng/?limit=1"
        response = requests.get(url, timeout=10).json()
        value = response['data'][0]['value']
        classification = response['data'][0]['value_classification']
        return int(value), classification
    except Exception as e:
        send_error_alert(f"Сбой Fear & Greed Index: {str(e)[:100]}")
        return 50, "Neutral"

def get_global_data():
    try:
        url = "https://api.coingecko.com/api/v3/global"
        response = requests.get(url, timeout=10).json()
        data = response['data']
        return {
            'btc_dominance': data.get('market_cap_percentage', {}).get('btc', 0),
            'total_market_cap': data.get('total_market_cap', {}).get('usd', 0) / 1_000_000_000,
            'total_volume': data.get('total_volume', {}).get('usd', 0) / 1_000_000_000
        }
    except Exception as e:
        return {'btc_dominance': 0, 'total_market_cap': 0, 'total_volume': 0}

def get_crypto_data():
    try:
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
    except Exception as e:
        send_error_alert(f"Сбой CoinGecko Prices: {str(e)[:100]}")
        return "• Крипта: Данные временно недоступны"

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
    tickers = {
        "GC=F": "Золото", "SI=F": "Серебро", "BZ=F": "Нефть Brent",
        "^GSPC": "S&P 500", "NVDA": "NVIDIA", "DX-Y.NYB": "Индекс доллара (DXY)"
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
                data.append(f"• {name}: ${info['Close'].iloc[-1]:,.2f} (изменение недоступно)")
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
        feeds = ["http://feeds.reuters.com/reuters/businessNews", "https://cointelegraph.com/rss"]
        headlines = []
        for feed_url in feeds:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:3]:
                title = entry.title
                link = entry.get('link', '')
                if not link or len(title) < 20:
                    continue
                time_ago = format_time_ago(entry.get('published_parsed'))
                title_safe = title.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('`', '\\`')
                time_prefix = f"[{time_ago}] " if time_ago else ""
                headlines.append(f"• {time_prefix}[{title_safe}]({link})")  # Старый, правильный формат ссылки
        return "\n".join(headlines[:5])
    except Exception as e:
        return "• Новости: Ошибка сбора данных"

# ==========================================
# 3. ИИ-АНАЛИЗ (ВОССТАНОВЛЕННЫЙ ИДЕАЛЬНЫЙ ПРОМПТ v31.7)
# ==========================================
def get_ai_analysis(session_info, fear_greed, global_data, crypto, support_resistance, finance, news):
    api_key = os.environ.get("OPENROUTER_API_KEY")
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    # Берем модели из конфига, как мы договорились
    models = get_models_for_task('main')
    
    fg_value, fg_class = fear_greed
    btc_dom = global_data['btc_dominance']
    total_mcap = global_data['total_market_cap']
    
    if fg_value is None:
        fg_value, fg_class, fg_emoji, fg_signal = 50, "Neutral", "😐", "НЕЙТРАЛЬНО"
    elif fg_value <= 24: fg_emoji, fg_signal = "😰", "ПАНИКА"
    elif fg_value <= 49: fg_emoji, fg_signal = "😟", "СТРАХ"
    elif fg_value <= 51: fg_emoji, fg_signal = "😐", "НЕЙТРАЛЬНО"
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
1. Честность: Никогда не утверждай, что новость является единственной причиной движения цены. Используй формулировки: "возможный фактор", "временная корреляция", "на фоне новостей".
2. ВСЕ заголовки разделов должны быть выделены жирным шрифтом с помощью двойных звездочек в начале и в конце. Пример: **🪙 1. КРИПТОРЫНОК**
3. НЕ добавляй звездочки в обычный текст внутри разделов (только для заголовков!).
4. НЕ используй символы ##, >, --- или таблицы.
5. Сохраняй кликабельные ссылки в новостях в формате [текст](url).
6. Пиши подробно, без воды, используй эмодзи для структуры.
7. ВСЕ заголовки новостей должны быть ПЕРЕВЕДЕНЫ на русский язык (обязательно!).
8. НЕ сокращай блоки — пиши каждый раздел полноценно.
9. Обязательно используй переносы строк между абзацами!

СТРУКТУРА ПОСТА (скопируй эти заголовки ровно в таком виде с жирным выделением):

**📊 ИИ АНАЛИТИК: {session_info['name']} ОБЗОР — {session_info['date']}**

**📈 ПЕРИОД АНАЛИЗА:** {session_info['period']}

⚠️ Сначала риски, потом возможности!

**🪙 1. КРИПТОРЫНОК**
- BTC, ETH, SOL, XRP: цены, объёмы, изменения за период
- Уровни поддержки/сопротивления BTC
- Доминация BTC: {btc_dom:.1f}% — что это значит
- Общая капитализация: ${total_mcap:.0f}B
- Анализ: что происходит и почему

**🛢️ 2. СЫРЬЁ**
- Золото, Серебро, Нефть Brent: цены и изменения из блока [РЫНКИ]
- Связь с инфляцией и риск-аппетитом
- Анализ: куда движутся "умные деньги"

**🌍 3. МАКРО-ФОН**
- S&P 500, DXY (индекс доллара): цены и изменения из блока [РЫНКИ]
- Индекс страха/жадности: {fg_value}/100 ({fg_class})
- Анализ: риск-он или риск-офф?

**🌐 4. ГЕОПОЛИТИКА**
- Новости из блока [НОВОСТИ] (регуляция, законы, санкции)
- СОХРАНЯЙ КЛИКАБЕЛЬНЫЕ ССЫЛКИ [текст](url) — НЕ ПЕРЕПИСЫВАЙ ЗАГОЛОВКИ!
- Временные метки [X ч. назад]
- Влияние на рынки

**💻 5. IT И ТЕХНОЛОГИИ**
- NVIDIA: цена и изменение из блока [РЫНКИ]
- Новости про ETF, биржи, институционалов
- Анализ: куда движется "умный капитал"

**🔗 СВЯЗЬ ВЕТОК**
- Как геополитика/IT влияют на крипту
- Комплексный вывод: что это значит для рынка

**🎯 ТОРГОВЫЕ ИДЕИ (3 совета):**
1️⃣ [Конкретное действие]: [Пояснение с процентами и уровнями]
2️⃣ [Конкретное действие]: [Пояснение с процентами и уровнями]
3️⃣ [Конкретное действие]: [Пояснение с процентами и уровнями]

**⚡ QUICK STATS:**
Используй цветовую кодировку: 🟢 рост, 🔴 падение, 🟡 предупреждение, 🔵 факт.
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

**⚖️ ДИСКЛЕЙМЕР:**
"⚠️ Не является индивидуальной инвестиционной рекомендацией. Финансовые рынки сопряжены с риском потери средств. Проводите собственное исследование (DYOR)."

ПРАВИЛА СТИЛЯ:
- Тон: профессиональный, но живой (не сухой)
- Сленг с расшифровками в скобках: "лонг сквизнуло (long squeeze)"
- Конкретные цифры и проценты
- БЕЗ ВОДЫ: каждое предложение должно нести информацию
- Объём: 3500-4000 символов

⛔ КРИТИЧЕСКОЕ ПРАВИЛО ВЫВОДА:
Никогда не выводи в финальный текст служебные инструкции или мета-указания из этого промпта. Отвечай ТОЛЬКО готовым, чистым текстом поста.

ПРИСТУПАЙ!"""
    
    for model in models:
        try:
            payload = {"model": model, "messages": [{"role": "user", "content": prompt}]}
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/volk6691ilya-lgtm/domik-na-obochine",
                "X-Title": "Ember Watch System"
            }
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    content = result['choices'][0]['message']['content']
                    if content and len(content.strip()) > 200:
                        print(f"✅ ИИ-анализ успешно сгенерирован моделью: {model}")
                        return content
        except Exception:
            continue
    
    send_error_alert(f"КРИТИЧЕСКИЙ СБОЙ: Все {len(models)} ИИ-моделей из конфигурации недоступны.")
    return None

# ==========================================
# 4. ФУТЕР ПОСТА (ВОССТАНОВЛЕННЫЙ)
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
Система автоматически мониторит рынки и геополитику 24/7. При резких изменениях (падение/рост >3% за час) в канал придёт экстренный сигнал с графиком, анализом причин и планом действий.

👍 Если обзор был полезен — ставь реакцию!
📢 **Подписывайся на канал**, чтобы не пропустить важные сигналы и торговые идеи!"""

# ==========================================
# 5. УМНОЕ РАЗДЕЛЕНИЕ НА ЧАСТИ
# ==========================================
def smart_split_text(text, max_len=3800):
    sections, current_section = [], []
    for line in text.split('\n'):
        is_section_header = any([
            '🪙 **1.' in line, '🛢️ **2.' in line, '🌍 **3.' in line,
            '🌐 **4.' in line or '🌐 4.' in line, '💻 **5.' in line or '💻 5.' in line,
            '🔗 **' in line, ' **ИИ АНАЛИТИК' in line, '📈 **ПЕРИОД' in line,
        ])
        if is_section_header and current_section:
            sections.append('\n'.join(current_section))
            current_section = [line]
        else:
            current_section.append(line)
    if current_section:
        sections.append('\n'.join(current_section))
    
    parts, current_part, current_length = [], [], 0
    for section in sections:
        if current_length + len(section) + 2 <= max_len:
            current_part.append(section)
            current_length += len(section) + 2
        else:
            if current_part:
                parts.append('\n\n'.join(current_part).strip())
                current_part, current_length = [], 0
            if len(section) + 2 > max_len:
                for para in section.split('\n\n'):
                    if len(para) + 2 <= max_len:
                        if current_length + len(para) + 2 <= max_len:
                            current_part.append(para)
                            current_length += len(para) + 2
                        else:
                            if current_part:
                                parts.append('\n\n'.join(current_part).strip())
                            current_part, current_length = [para], len(para) + 2
                    else:
                        for line in para.split('\n'):
                            if current_length + len(line) + 1 <= max_len:
                                current_part.append(line)
                                current_length += len(line) + 1
                            else:
                                if current_part:
                                    parts.append('\n'.join(current_part).strip())
                                current_part, current_length = [line], len(line) + 1
            else:
                current_part, current_length = [section], len(section) + 2
    if current_part:
        parts.append('\n\n'.join(current_part).strip())
    return parts

# ==========================================
# 6. КОЛЛЕКЦИЯ КАРТИНОК
# ==========================================
COVER_IMAGES = {
    'bullish': ["https://res.cloudinary.com/yln8uskh/image/upload/v1788870775/bullish1.jpg", "https://res.cloudinary.com/yln8uskh/image/upload/v1788870869/bullish2.jpg", "https://res.cloudinary.com/yln8uskh/image/upload/v1788870869/bullish4.jpg", "https://res.cloudinary.com/yln8uskh/image/upload/v1788871107/bullish3.jpg", "https://res.cloudinary.com/yln8uskh/image/upload/v1788871108/bullish5.jpg"],
    'bearish': ["https://res.cloudinary.com/yln8uskh/image/upload/v1788871107/bearish2.jpg", "https://res.cloudinary.com/yln8uskh/image/upload/v1788871107/bearish1.jpg", "https://res.cloudinary.com/yln8uskh/image/upload/v1788871107/bearish3.jpg", "https://res.cloudinary.com/yln8uskh/image/upload/v1788871107/bearish4.jpg", "https://res.cloudinary.com/yln8uskh/image/upload/v1788871108/bearish5.jpg"],
    'neutral': ["https://res.cloudinary.com/yln8uskh/image/upload/v1788871108/neutral1.jpg", "https://res.cloudinary.com/yln8uskh/image/upload/v1788871108/neutral2.jpg", "https://res.cloudinary.com/yln8uskh/image/upload/v1788871108/neutral3.jpg", "https://res.cloudinary.com/yln8uskh/image/upload/v1788871108/neutral4.jpg", "https://res.cloudinary.com/yln8uskh/image/upload/v1788871109/neutral5.jpg"]
}

def get_cover_image(fear_greed):
    fg_value = fear_greed[0] if fear_greed and fear_greed[0] else 50
    mood = 'bearish' if fg_value <= 30 else ('bullish' if fg_value >= 70 else 'neutral')
    image_url = random.choice(COVER_IMAGES.get(mood, [])) if COVER_IMAGES.get(mood) else None
    if not image_url:
        all_images = [img for imgs in COVER_IMAGES.values() for img in imgs]
        image_url = random.choice(all_images) if all_images else None
    if not image_url: return None
    try:
        response = requests.get(image_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        if response.status_code == 200 and len(response.content) > 1000:
            return BytesIO(response.content)
    except Exception:
        pass
    return None

# ==========================================
# 7. ОТПРАВКА В TELEGRAM
# ==========================================
def send_to_telegram(text, fear_greed=None):
    bot_token, channel_id = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHANNEL_ID")
    if not bot_token or not channel_id:
        send_error_alert("КРИТИЧЕСКИЙ СБОЙ: Отсутствуют TELEGRAM_BOT_TOKEN или TELEGRAM_CHANNEL_ID")
        return
    
    image_buffer = get_cover_image(fear_greed)
    if image_buffer:
        try:
            requests.post(f"https://api.telegram.org/bot{bot_token}/sendPhoto", files={
                'photo': ('cover.jpg', image_buffer, 'image/jpeg'),
                'chat_id': (None, channel_id),
                'caption': (None, "💼 ИИ АНАЛИТИК НА СВЯЗИ \n\n Система завершила анализ 5 ветвей рынка. Полный разбор ниже 👇")
            }, timeout=30)
            time.sleep(2)
        except Exception:
            pass
    
    parts = smart_split_text(text, max_len=3800)
    for i, part in enumerate(parts):
        if i > 0: time.sleep(3)
        if len(parts) > 1:
            header = f"📄 **ЧАСТЬ {i+1}/{len(parts)}**\n\n"
            footer_text = f"\n\n_...продолжение следует (часть {i+1}/{len(parts)})_" if i < len(parts) - 1 else ""
            part = header + part + footer_text
        
        if len(part) > 4090: part = part[:4080] + "\n\n_...текст обрезан_"
        
        try:
            requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                "chat_id": channel_id, "text": part, "parse_mode": "Markdown", "disable_web_page_preview": True
            }, timeout=15)
        except Exception:
            pass

# ==========================================
# 8. ГЛАВНЫЙ ЗАПУСК
# ==========================================
def main():
    print("🚀 Запуск ИИ Аналитика v31.7 (Восстановлена стабильная версия)...")
    session_info = get_session_info()
    print(f"   Тип: {session_info['name']} выпуск")
    print(f"   Период: {session_info['period']}")
    
    fear_greed = get_fear_greed_index()
    global_data = get_global_data()
    crypto = get_crypto_data()
    support_resistance = get_support_resistance()
    finance = get_finance_data()
    news = get_news_data()
    
    print("🧠 ИИ-анализ (30-60 секунд)...")
    try:
        analysis = get_ai_analysis(session_info, fear_greed, global_data, crypto, support_resistance, finance, news)
        if not analysis or len(analysis.strip()) < 200:
            fg_value = fear_greed[0] if fear_greed and fear_greed[0] is not None else 50
            fg_class = fear_greed[1] if fear_greed and len(fear_greed) > 1 else "Neutral"
            analysis = f"""⚠️ **Внимание:** Сервисы ИИ-анализа временно перегружены. Свежие данные ниже актуальны.

🪙 **КРИПТОРЫНОК:**
{crypto}

📊 **РЫНКИ И СЫРЬЁ:**
{finance}

🌡️ **ИНДЕКС СТРАХА/ЖАДНОСТИ:** {fg_value}/100 ({fg_class})"""
    except Exception as e:
        print(f"❌ Ошибка ИИ-анализа: {e}")
        fg_value = fear_greed[0] if fear_greed and fear_greed[0] is not None else 50
        fg_class = fear_greed[1] if fear_greed and len(fear_greed) > 1 else "Neutral"
        analysis = f"""⚠️ **Внимание:** Техническая ошибка при генерации анализа. Свежие данные ниже актуальны.

🪙 **КРИПТОРЫНОК:**
{crypto}

📊 **РЫНКИ И СЫРЬЁ:**
{finance}

🌡️ **ИНДЕКС СТРАХА/ЖАДНОСТИ:** {fg_value}/100 ({fg_class})"""
    
    full_text = analysis + "\n\n" + get_post_footer(session_info)
    print(f"📏 Длина текста: {len(full_text)} символов. Публикация...")
    send_to_telegram(full_text, fear_greed)
    print("✅ Миссия выполнена.")

if __name__ == "__main__":
    main()
