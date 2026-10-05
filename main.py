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
from ai_models_config import get_models_for_task

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
            pass  # Не ломаем основной поток, если алерт не отправился

# ==========================================
# 1. ОПРЕДЕЛЕНИЕ ТИПА ВЫПУСКА (ЖЕСТКАЯ ЛОГИКА 12 ЧАСОВ)
# ==========================================
def get_session_info():
    """
    Гарантирует строгий 12-часовой период анализа:
    - Утренний запуск (00:00 - 14:59 МСК): анализирует с 21:00 вчерашнего дня до сейчас.
    - Вечерний запуск (15:00 - 23:59 МСК): анализирует с 09:00 сегодняшнего дня до сейчас.
    """
    msk_tz = timezone(timedelta(hours=3))
    now_msk = datetime.now(msk_tz)
    current_hour = now_msk.hour
    
    if current_hour < 15:
        session_type = "morning"
        session_name = "УТРЕННИЙ"
        # Старт в 21:00 предыдущего дня
        period_start = now_msk.replace(hour=21, minute=0, second=0) - timedelta(days=1)
        period_text = f"с {period_start.strftime('%H:%M %d.%m')} по {now_msk.strftime('%H:%M %d.%m.%Y')} (ночная сессия)"
    else:
        session_type = "evening"
        session_name = "ВЕЧЕРНИЙ"
        # Старт в 09:00 текущего дня
        period_start = now_msk.replace(hour=9, minute=0, second=0)
        period_text = f"с {period_start.strftime('%H:%M %d.%m')} по {now_msk.strftime('%H:%M %d.%m.%Y')} (дневная сессия)"
    
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
    """Крипта с объемами торгов + автоматический фоллбэк на Binance"""
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana,ripple,toncoin&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true&include_market_cap=true"
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            print(f"⚠️ CoinGecko вернул статус {response.status_code}, переключаюсь на Binance...")
            send_error_alert(f"CoinGecko недоступен (статус {response.status_code}), использую Binance API")
            return _get_crypto_from_binance()
        
        data = response.json()
        if not data or 'bitcoin' not in data:
            print("⚠️ CoinGecko вернул некорректный ответ, переключаюсь на Binance...")
            send_error_alert("CoinGecko вернул пустой ответ, использую Binance API")
            return _get_crypto_from_binance()
        
        result = []
        names = {"bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL", "ripple": "XRP", "toncoin": "TON"}
        for key, name in names.items():
            if key in data: 
                price = data[key]['usd']
                change = data[key]['usd_24h_change']
                volume = data[key].get('usd_24h_vol', 0)
                vol_billion = volume / 1_000_000_000
                result.append(f"• {name}: ${price:,.2f} ({change:+.2f}%) | Объем: ${vol_billion:.2f}B")
        
        print("✅ Данные крипты получены через CoinGecko")
        return "\n".join(result)
        
    except Exception as e:
        print(f"⚠️ CoinGecko полностью недоступен ({str(e)[:50]}), переключаюсь на Binance...")
        send_error_alert(f"CoinGecko упал: {str(e)[:100]}. Переключаюсь на Binance.")
        return _get_crypto_from_binance()

def _get_crypto_from_binance():
    """Резервный источник: Binance публичный API"""
    try:
        url = 'https://api.binance.com/api/v3/ticker/24hr?symbols=["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","TONUSDT"]'
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ Binance API тоже вернул ошибку (статус {response.status_code})")
            send_error_alert(f"ОБА источника крипты недоступны: CoinGecko и Binance (статус {response.status_code})")
            return "• Крипта: Данные временно недоступны (оба API упали)"
        
        data = response.json()
        if not isinstance(data, list):
            return "• Крипта: Данные временно недоступны"
        
        result = []
        symbol_map = {"BTCUSDT": "BTC", "ETHUSDT": "ETH", "SOLUSDT": "SOL", "XRPUSDT": "XRP", "TONUSDT": "TON"}
        
        for item in data: 
            symbol = item.get('symbol', '')
            if symbol in symbol_map:
                name = symbol_map[symbol]
                price = float(item.get('lastPrice', 0))
                change = float(item.get('priceChangePercent', 0))
                volume = float(item.get('quoteVolume', 0))
                vol_billion = volume / 1_000_000_000
                result.append(f"• {name}: ${price:,.2f} ({change:+.2f}%) | Объем: ${vol_billion:.2f}B")
        
        if result:
            print("✅ Данные крипты успешно получены через Binance API (резерв)")
            return "\n".join(result)
        else:
            return "• Крипта: Данные временно недоступны"
            
    except Exception as e:
        print(f"❌ Binance API тоже упал: {str(e)[:50]}")
        send_error_alert(f"Binance API упал: {str(e)[:100]}")
        return "• Крипта: Данные временно недоступны (оба API упали)"

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
            return f"{hours // 24} дн. назад"
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
                
                # Берем краткую выжимку (summary) или первые 100 символов заголовка, если summary нет
                summary = entry.get('summary', '')
                short_summary = summary[:120] + '...' if len(summary) > 120 else (title[:100] + '...' if len(title) > 100 else title)
                
                if not link or len(short_summary) < 20:
                    continue
                    
                time_ago = format_time_ago(entry.get('published_parsed'))
                # Экранируем спецсимволы для Telegram Markdown
                summary_safe = short_summary.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('`', '\\`')
                time_prefix = f"[{time_ago}] " if time_ago else ""
                
                # Формат: • [2 ч. назад] Краткая суть новости... [источник](ссылка)
                headlines.append(f"• {time_prefix}{summary_safe} [источник]({link})")
                
        return "\n".join(headlines[:5])
    except Exception as e:
        return "• Новости: Ошибка сбора данных"

# ==========================================
# 3. ИИ-АНАЛИЗ
# ==========================================
def get_ai_analysis(session_info, fear_greed, global_data, crypto, support_resistance, finance, news):
    api_key = os.environ.get("OPENROUTER_API_KEY")
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    models = get_models_for_task('main')
    
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
2. ВСЕ заголовки разделов должны быть выделены жирным шрифтом с помощью двойных звездочек. Пример: **🪙 1. КРИПТОРЫНОК**
3. НЕ добавляй звездочки в обычный текст внутри разделов (только для заголовков!).
4. НЕ используй символы ##, >, --- или таблицы.
5. Сохраняй кликабельные ссылки в новостях в формате [текст](url).
6. Пиши подробно, без воды, используй эмодзи для структуры.
7. ВСЕ заголовки новостей должны быть ПЕРЕВЕДЕНЫ на русский язык.
8. НЕ сокращай блоки — пиши каждый раздел полноценно.
9. Обязательно используй переносы строк между абзацами!

СТРУКТУРА ПОСТА (скопируй эти заголовки ровно в таком виде):

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
(Включи ВСЕ перечисленные ниже метрики, не сокращай этот список):
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
Никогда не выводи в финальный текст служебные инструкции, фразы в скобках типа "(ОБЯЗАТЕЛЬНО ВСЕ ПУНКТЫ, НЕ СОКРАЩАЙ!)" или любые мета-указания из этого промпта. Отвечай ТОЛЬКО готовым, чистым текстом поста для публикации.

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
                        print(f"✅ ИИ-анализ успешно сгенерирован моделью: {model}")
                        return content
        except Exception:
            continue
    
    send_error_alert(f"КРИТИЧЕСКИЙ СБОЙ: Все {len(models)} ИИ-моделей из конфигурации недоступны.")
    return None

# ==========================================
# 4. ФУТЕР ПОСТА
# ==========================================
def get_post_footer(session_info):
    # Жесткая логика: Утро -> следующий вечером сегодня. Вечер -> следующий утром завтра.
    if session_info['type'] == 'morning':
        next_text = "сегодня вечером в 21:00 МСК"
    else:
        next_text = "завтра утром в 09:00 МСК"
    
    return f"""
🔔 **СЛЕДУЮЩИЙ ВЫПУСК:** {next_text}

🔔🚨 **ПОЖАРНЫЙ ШПИОН** — система экстренных оповещений
Система автоматически мониторит рынки и геополитику 24/7. При резких изменениях (падение/рост >3% за час) в канал придёт экстренный сигнал с графиком, анализом причин и планом действий.

👍 Если обзор был полезен — ставь реакцию!
📢 **Подписывайся на канал**, чтобы не пропустить важные сигналы и торговые идеи!"""

# ==========================================
# 5. УМНОЕ РАЗДЕЛЕНИЕ НА ЧАСТИ
# ==========================================
def smart_split_text(text, max_len=3800):
    sections = []
    current_section = []
    
    for line in text.split('\n'):
        is_section_header = any([
            '🪙 **1.' in line,
            '🛢️ **2.' in line,
            '🌍 **3.' in line,
            '🌐 **4.' in line or '🌐 4.' in line,
            '💻 **5.' in line or '💻 5.' in line,
            '🔗 **' in line,
            ' **ИИ АНАЛИТИК' in line,
            '📈 **ПЕРИОД' in line,
        ])
        
        if is_section_header and current_section:
            sections.append('\n'.join(current_section))
            current_section = [line]
        else:
            current_section.append(line)
    
    if current_section:
        sections.append('\n'.join(current_section))
    
    parts = []
    current_part = []
    current_length = 0
    
    for section in sections:
        section_length = len(section) + 2
        
        if current_length + section_length <= max_len:
            current_part.append(section)
            current_length += section_length
        else:
            if current_part:
                parts.append('\n\n'.join(current_part).strip())
                current_part = []
                current_length = 0
            
            if section_length > max_len:
                paragraphs = section.split('\n\n')
                for para in paragraphs:
                    para_length = len(para) + 2
                    if para_length <= max_len:
                        if current_length + para_length <= max_len:
                            current_part.append(para)
                            current_length += para_length
                        else:
                            if current_part:
                                parts.append('\n\n'.join(current_part).strip())
                                current_part = [para]
                                current_length = para_length + 2
                            else:
                                current_part = [para]
                                current_length = para_length
                    else:
                        lines = para.split('\n')
                        temp_para = []
                        temp_length = 0
                        for line in lines:
                            line_length = len(line) + 1
                            if temp_length + line_length <= max_len:
                                temp_para.append(line)
                                temp_length += line_length
                            else:
                                if temp_para:
                                    parts.append('\n'.join(temp_para).strip())
                                temp_para = [line]
                                temp_length = line_length
                        if temp_para:
                            current_part.append('\n'.join(temp_para))
                            current_length = sum(len(p) for p in current_part) + len(current_part) * 2
            else:
                current_part = [section]
                current_length = section_length
    
    if current_part:
        parts.append('\n\n'.join(current_part).strip())
    
    return parts

# ==========================================
# 6. КОЛЛЕКЦИЯ КАРТИНОК
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
        all_images = []
        for images in COVER_IMAGES.values():
            all_images.extend(images)
        image_url = random.choice(all_images) if all_images else None
    
    if not image_url:
        print("⚠️ Нет картинок в коллекции!")
        return None
    
    try:
        print(f"🎨 Скачивание картинки (настроение: {mood})...")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"
        }
        response = requests.get(image_url, headers=headers, timeout=30)
        if response.status_code == 200 and len(response.content) > 1000:
            print(f"✅ Картинка скачана успешно (размер: {len(response.content)} байт)")
            return BytesIO(response.content)
        else:
            print(f"⚠️ Ошибка скачивания: статус {response.status_code}")
            return None
    except Exception as e:
        print(f"⚠️ Критическая ошибка при скачивании: {e}")
        return None

# ==========================================
# 7. ОТПРАВКА В TELEGRAM
# ==========================================
def send_to_telegram(text, fear_greed=None):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    channel_id = os.environ.get("TELEGRAM_CHANNEL_ID")
    
    if not bot_token or not channel_id:
        send_error_alert("КРИТИЧЕСКИЙ СБОЙ: Отсутствуют TELEGRAM_BOT_TOKEN или TELEGRAM_CHANNEL_ID")
        return
    
    print("🖼️ Выбор картинки из коллекции...")
    image_buffer = get_cover_image(fear_greed)
    
    if image_buffer:
        print("📤 Отправка картинки...")
        caption = "💼 ИИ АНАЛИТИК НА СВЯЗИ \n\n Система завершила анализ 5 ветвей рынка. Полный разбор ниже 👇"
        
        files = {
            'photo': ('cover.jpg', image_buffer, 'image/jpeg'),
            'chat_id': (None, channel_id),
            'caption': (None, caption)
        }
        
        response = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendPhoto",
            files=files,
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ Картинка успешно отправлена в Telegram!")
        else:
            print(f"❌ Ошибка отправки картинки: {response.text}")
        time.sleep(2)
    else:
        print("⚠️ Картинка не получена, отправляем только текст...")
    
    parts = smart_split_text(text, max_len=3800)
    total_parts = len(parts)
    print(f"📤 Отправка {total_parts} частей текста...")
    
    for i, part in enumerate(parts):
        if i > 0:
            time.sleep(3)
        
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
        
        response = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json=text_payload,
            timeout=15
        )
        
        if response.status_code == 200:
            print(f"✅ Часть {i+1}/{total_parts} отправлена! (длина: {len(part_with_indicator)})")
        else:
            print(f"❌ Ошибка части {i+1}: {response.text}")

# ==========================================
# 8. ГЛАВНЫЙ ЗАПУСК
# ==========================================
def main():
    print("🚀 Запуск ИИ Аналитика v34.0 (Строгий 12-часовой цикл)...")
    
    print("📡 Определение типа выпуска...")
    session_info = get_session_info()  # Используем строгую логику без JSON-кэша
    print(f"   Тип: {session_info['name']} выпуск")
    print(f"   Период: {session_info['period']}")
    
    print("📡 Сбор данных (5 веток)...")
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
            print("⚠️ ИИ вернул пустой или слишком короткий ответ. Используем резервный текст.")
            fg_value = fear_greed[0] if fear_greed and fear_greed[0] is not None else 50
            fg_class = fear_greed[1] if fear_greed and len(fear_greed) > 1 else "Neutral"
            analysis = f"""⚠️ **Внимание:** Сервисы ИИ-анализа временно перегружены. Система не смогла сгенерировать подробный обзор, но свежие данные ниже абсолютно актуальны.

🪙 **КРИПТОРЫНОК:**
{crypto}

📊 **РЫНКИ И СЫРЬЁ:**
{finance}

🌡️ **ИНДЕКС СТРАХА/ЖАДНОСТИ:** {fg_value}/100 ({fg_class})

🔍 Полный анализ с торговыми идеями будет в следующем выпуске."""
    except Exception as e:
        print(f"❌ Ошибка ИИ-анализа: {e}")
        fg_value = fear_greed[0] if fear_greed and fear_greed[0] is not None else 50
        fg_class = fear_greed[1] if fear_greed and len(fear_greed) > 1 else "Neutral"
        analysis = f"""⚠️ **Внимание:** Произошла техническая ошибка при генерации анализа. Свежие данные ниже актуальны.

🪙 **КРИПТОРЫНОК:**
{crypto}

📊 **РЫНКИ И СЫРЬЁ:**
{finance}

🌡️ **ИНДЕКС СТРАХА/ЖАДНОСТИ:** {fg_value}/100 ({fg_class})"""
    
    print("📎 Добавление футера...")
    footer = get_post_footer(session_info)
    full_text = analysis + "\n\n" + footer
    print(f"📏 Длина текста: {len(full_text)} символов")
    
    print("📤 Публикация...")
    send_to_telegram(full_text, fear_greed)
    
    print("✅ Миссия выполнена.")

if __name__ == "__main__":
    main()
