import os
import requests
import json
import time
import random
import yfinance as yf
import feedparser
import pandas as pd
from datetime import datetime, timedelta, timezone

# ==========================================
# 1. ОПРЕДЕЛЕНИЕ ТИПА ВЫПУСКА (УТРО/ВЕЧЕР)
# ==========================================
def get_session_info():
    """Определяем тип выпуска и временной диапазон анализа"""
    msk_tz = timezone(timedelta(hours=3))
    now_msk = datetime.now(msk_tz)
    current_hour = now_msk.hour
    
    if current_hour < 15:  # Утренний выпуск (до 15:00 МСК)
        session_type = "morning"
        session_name = "УТРЕННИЙ"
        period_start = now_msk.replace(hour=21, minute=0, second=0) - timedelta(days=1)
        period_end = now_msk.replace(hour=9, minute=0, second=0)
        period_text = f"с 21:00 {period_start.strftime('%d.%m')} по 09:00 {now_msk.strftime('%d.%m.%Y')} (ночная сессия)"
    else:  # Вечерний выпуск
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
# 2. СБОР РЕАЛЬНЫХ ДАННЫХ (5 ВЕТОК)
# ==========================================

def get_fear_greed_index():
    """Ветка 3 (МАКРО): Индекс страха и жадности"""
    try:
        url = "https://api.alternative.me/fng/?limit=1"
        response = requests.get(url, timeout=10).json()
        value = response['data'][0]['value']
        classification = response['data'][0]['value_classification']
        return int(value), classification
    except Exception as e:
        return None, f"Ошибка: {str(e)[:20]}"

def get_global_data():
    """Ветка 1 (КРИПТА): Доминация BTC и капитализация"""
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
    """Ветка 1 (КРИПТА): Цены и объемы"""
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
        return f"• Крипта: Ошибка ({str(e)[:30]})"

def get_support_resistance():
    """Ветка 1 (КРИПТА): Уровни BTC"""
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
    """Ветки 2 (СЫРЬЁ), 3 (МАКРО) и 5 (IT): Золото, Нефть, S&P 500, NVIDIA, DXY"""
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
    """Форматирует время публикации новости"""
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
    """Ветки 4 (ГЕОПОЛИТИКА) и 5 (IT): Новости"""
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
        "minimax/minimax-m3:free",
        "nvidia/nemotron-3.5-lightning:free",
        "inclusionai/ling-3.0-flash-fin:free"
    ]
    
    fg_value, fg_class = fear_greed
    btc_dom = global_data['btc_dominance']
    total_mcap = global_data['total_market_cap']
    
    if fg_value is None:
        fg_value = 50
        fg_class = "Neutral"
        fg_emoji = ""
        fg_signal = "НЕЙТРАЛЬНО"
    elif fg_value <= 24:
        fg_emoji = "🔴"
        fg_signal = "ПАНИКА"
    elif fg_value <= 49:
        fg_emoji = "🟠"
        fg_signal = "СТРАХ"
    elif fg_value <= 51:
        fg_emoji = "🟡"
        fg_signal = "НЕЙТРАЛЬНО"
    elif fg_value <= 74:
        fg_emoji = "🟢"
        fg_signal = "ЖАДНОСТЬ"
    else:
        fg_emoji = "🔴"
        fg_signal = "ЭКСТРЕМАЛЬНАЯ ЖАДНОСТЬ"
    
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

📊 ИИ АНАЛИТИК: {session_info['name']} ОБЗОР — {session_info['date']}

📈 ПЕРИОД АНАЛИЗА: {session_info['period']}

️ Сначала риски, потом возможности!

 1. КРИПТОРЫНОК
- BTC, ETH, SOL, XRP: цены, объёмы, изменения за период
- Уровни поддержки/сопротивления BTC
- Доминация BTC: {btc_dom:.1f}% — что это значит
- Общая капитализация: ${total_mcap:.0f}B
- Анализ: что происходит и почему

🛢️ 2. СЫРЬЁ
- Золото, Серебро, Нефть Brent: цены и изменения из блока [РЫНКИ]
- Связь с инфляцией и риск-аппетитом
- Анализ: куда движутся "умные деньги"

🌍 3. МАКРО-ФОН
- S&P 500, DXY (индекс доллара): цены и изменения из блока [РЫНКИ]
- Индекс страха/жадности: {fg_value}/100 ({fg_class})
- Анализ: риск-он или риск-офф?

🌐 4. ГЕОПОЛИТИКА
- Новости из блока [НОВОСТИ] (регуляция, законы, санкции)
- СОХРАНЯЙ КЛИКАБЕЛЬНЫЕ ССЫЛКИ [текст](url) — НЕ ПЕРЕПИСЫВАЙ ЗАГОЛОВКИ!
- Временные метки [X ч. назад]
- Влияние на рынки

💻 5. IT И ТЕХНОЛОГИИ
- NVIDIA: цена и изменение из блока [РЫНКИ]
- Новости про ETF, биржи, институционалов
- Анализ: куда движется "умный капитал"

🔗 СВЯЗЬ ВЕТОК:
- Как геополитика/IT влияют на крипту
- Комплексный вывод: что это значит для рынка

🎯 ТОРГОВЫЕ ИДЕИ (3 совета):
1️⃣ [Конкретное действие]: [Пояснение с процентами и уровнями]
2️ [Конкретное действие]: [Пояснение с процентами и уровнями]
3️⃣ [Конкретное действие]: [Пояснение с процентами и уровнями]

⚡ QUICK STATS (ОБЯЗАТЕЛЬНО ВСЕ ПУНКТЫ, НЕ СОКРАЩАЙ!):
Используй цветовую кодировку:
- 🟢 зелёный = рост/бычий сигнал
-  красный = падение/медвежий сигнал
- 🟡 жёлтый = предупреждение/нейтрально
- 🔵 синий = факт/объём

Включи ВСЕ эти метрики:
- 🔵 BTC: [цена] ([изменение]%) — [комментарий]
-  ETH: [цена] ([изменение]%) — [комментарий]
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

⚠️ РИСК-ПРЕДУПРЕЖДЕНИЕ:
"Торговля на финансовых рынках сопряжена с высоким риском потери средств. Вы можете потерять ВЕСЬ депозит. Никогда не инвестируйте больше, чем готовы потерять полностью."

⚖️ ДИСКЛЕЙМЕР (ТОЧНЫЙ ТЕКСТ, НЕ СОКРАЩАТЬ!):
"⚠️ Вся информация носит ИСКЛЮЧИТЕЛЬНО ознакомительный характер и НЕ является индивидуальной инвестиционной рекомендацией. Финансовые рынки сопряжены с высоким риском потери средств (вплоть до 100% депозита). Вы действуете на свой страх и риск (DYOR — Do Your Own Research, проводите собственное исследование). Прошлые результаты не гарантируют будущую прибыль."

ПРАВИЛА СТИЛЯ:
- Тон: профессиональный, но живой (не сухой)
- Сленг с расшифровками в скобках: "лонг сквизнуло (long squeeze — принудительное закрытие позиций)"
- Конкретные цифры и проценты
- БЕЗ ВОДЫ: каждое предложение должно нести информацию
- Объём: 3500-4000 символов (подробно, но без повторов)
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
                return response.json()['choices'][0]['message']['content']
            elif response.status_code == 429:
                continue
        except Exception as e:
            continue
            
    return "Ошибка: ИИ временно недоступен."

# ==========================================
# 4. ФУТЕР ПОСТА
# ==========================================
def get_post_footer(session_info):
    """Генерирует футер поста"""
    msk_tz = timezone(timedelta(hours=3))
    now_msk = datetime.now(msk_tz)
    
    if session_info['type'] == 'morning':
        next_time = "21:00"
        next_type = "вечерний"
        next_date = now_msk.strftime("%d.%m.%Y")
    else:
        next_time = "09:00"
        next_type = "утренний"
        next_date = (now_msk + timedelta(days=1)).strftime("%d.%m.%Y")
    
    footer = f"""
⏰ СЛЕДУЮЩИЙ ВЫПУСК: {next_type} обзор в {next_time} МСК ({next_date})

🔔 ПОЖАРНЫЙ ШПИОН — система экстренных оповещений
Система автоматически мониторит рынки и геополитику. При резких изменениях в канал придёт экстренный сигнал.

👍 Если обзор был полезен — ставь реакцию!
📢 Подписывайся на канал, чтобы не пропустить важные сигналы."""
    
    return footer

# ==========================================
# 5. УМНОЕ РАЗДЕЛЕНИЕ НА ЧАСТИ
# ==========================================
def smart_split_text(text, max_len=4000):
    """Умное разделение текста на части без разрыва логических блоков"""
    paragraphs = text.split('\n\n')
    parts = []
    current_part = ""
    
    for para in paragraphs:
        if len(para) > max_len:
            if current_part:
                parts.append(current_part.strip())
                current_part = ""
            sentences = para.split('. ')
            temp_part = ""
            for sentence in sentences:
                if len(temp_part) + len(sentence) + 2 <= max_len:
                    temp_part += sentence + ". "
                else:
                    if temp_part:
                        parts.append(temp_part.strip())
                    temp_part = sentence + ". "
            if temp_part:
                current_part = temp_part
        elif len(current_part) + len(para) + 2 <= max_len:
            current_part += para + "\n\n"
        else:
            if current_part:
                parts.append(current_part.strip())
            current_part = para + "\n\n"
    
    if current_part:
        parts.append(current_part.strip())
    
    return parts

# ==========================================
# 6. ОТПРАВКА В TELEGRAM
# ==========================================
def send_to_telegram(text, fear_greed=None):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    channel_id = os.environ.get("TELEGRAM_CHANNEL_ID")
    
    if not bot_token or not channel_id:
        print("❌ Ошибка: TELEGRAM_BOT_TOKEN или TELEGRAM_CHANNEL_ID не установлены")
        return
    
    # Используем реальные профессиональные финансовые изображения
    seed = random.randint(1, 1000)
    
    # Коллекция URL с реальными финансовыми графиками (Unsplash)
    image_urls = [
        f"https://images.unsplash.com/photo-1611974789855-9c2a0b0a3b0c?w=1200&h=600&fit=crop&random={seed}",
        f"https://images.unsplash.com/photo-1621506289937-a8e6df2577ab?w=1200&h=600&fit=crop&random={seed}",
        f"https://images.unsplash.com/photo-1639762681485-074b9f78399c?w=1200&h=600&fit=crop&random={seed}",
        f"https://images.unsplash.com/photo-1642104704074-907c0698cbd9?w=1200&h=600&fit=crop&random={seed}",
        f"https://images.unsplash.com/photo-1559526324-4b2ff7614b2f?w=1200&h=600&fit=crop&random={seed}",
        f"https://images.unsplash.com/photo-1518186285589-2f18bd471d64?w=1200&h=600&fit=crop&random={seed}",
    ]
    
    # Выбираем случайное изображение
    image_url = random.choice(image_urls)
    
    caption = "📊 ИИ АНАЛИТИК НА СВЯЗИ\n\nСистема завершила анализ 5 ветвей рынка. Полный разбор ниже 👇"
    
    photo_payload = {
        "chat_id": channel_id,
        "photo": image_url,
        "caption": caption,
        "parse_mode": "Markdown"
    }
    response = requests.post(f"https://api.telegram.org/bot{bot_token}/sendPhoto", json=photo_payload, timeout=15)
    if response.status_code != 200:
        print(f"⚠️ Ошибка отправки картинки: {response.text}")
    time.sleep(2)
    
    # Умное разделение текста на части
    parts = smart_split_text(text, max_len=4000)
    total_parts = len(parts)
    
    print(f"📤 Отправка {total_parts} частей...")
    
    for i, part in enumerate(parts):
        if i > 0:
            time.sleep(3)
        
        # Добавляем индикатор части
        if total_parts > 1:
            header = f" **ЧАСТЬ {i+1}/{total_parts}**\n\n"
            footer_text = f"\n\n_...продолжение следует (часть {i+1}/{total_parts})_" if i < total_parts - 1 else ""
            part_with_indicator = header + part + footer_text
        else:
            part_with_indicator = part
        
        # Обрезаем если всё ещё слишком длинно
        if len(part_with_indicator) > 4090:
            part_with_indicator = part_with_indicator[:4080] + "\n\n_...текст обрезан_"
        
        # Отправляем часть
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
# 7. ГЛАВНЫЙ ЗАПУСК
# ==========================================
def main():
    print("🚀 Запуск ИИ Аналитика v27.3 (5 веток + реальные финансовые графики)...")
    
    print("📡 Определение типа выпуска...")
    session_info = get_session_info()
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
    except Exception as e:
        print(f"❌ Ошибка ИИ-анализа: {e}")
        analysis = "Ошибка генерации анализа."
    
    print("📎 Добавление футера...")
    footer = get_post_footer(session_info)
    full_text = analysis + "\n\n" + footer
    
    print(f"📏 Длина текста: {len(full_text)} символов")
    
    print("📤 Публикация...")
    send_to_telegram(full_text, fear_greed)
    print("✅ Миссия выполнена.")

if __name__ == "__main__":
    main()
