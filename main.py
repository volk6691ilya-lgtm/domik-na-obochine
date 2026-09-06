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
# 2. СБОР РЕАЛЬНЫХ ДАННЫХ (8 ВЕТВЕЙ)
# ==========================================

def get_fear_greed_index():
    """Получаем РЕАЛЬНЫЙ индекс страха и жадности"""
    try:
        url = "https://api.alternative.me/fng/?limit=1"
        response = requests.get(url, timeout=10).json()
        value = response['data'][0]['value']
        classification = response['data'][0]['value_classification']
        return int(value), classification
    except Exception as e:
        return None, f"Ошибка: {str(e)[:20]}"

def get_global_data():
    """Получаем доминацию BTC и общую капитализацию"""
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
    """Крипта с объемами торгов"""
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
    """Расчет уровней поддержки/сопротивления за последние 7 дней"""
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
    """Традиционные рынки и сырье"""
    try:
        tickers = {"GC=F": "Золото", "SI=F": "Серебро", "BZ=F": "Нефть Brent", "^GSPC": "S&P 500", "NVDA": "NVIDIA", "DX-Y.NYB": "Индекс доллара (DXY)"}
        data = []
        for ticker, name in tickers.items():
            asset = yf.Ticker(ticker)
            info = asset.history(period="1d")
            if not info.empty:
                price = info['Close'].iloc[-1]
                change = ((price - info['Open'].iloc[-1]) / info['Open'].iloc[-1]) * 100
                data.append(f"• {name}: ${price:,.2f} ({change:+.2f}%)")
        return "\n".join(data)
    except Exception as e:
        return f"• Рынки: Ошибка ({str(e)[:30]})"

def get_hours_ago(published_time):
    """Возвращает количество часов с момента публикации новости"""
    try:
        msk_tz = timezone(timedelta(hours=3))
        now = datetime.now(msk_tz)
        
        if hasattr(published_time, 'tm_year'):
            pub_dt = datetime(*published_time[:6], tzinfo=msk_tz)
        elif isinstance(published_time, datetime):
            pub_dt = published_time
        else:
            return None
        
        if pub_dt.tzinfo is None:
            pub_dt = pub_dt.replace(tzinfo=timezone.utc).astimezone(msk_tz)
        
        diff = now - pub_dt
        hours = diff.total_seconds() / 3600
        return hours
    except:
        return None

def format_time_ago(hours):
    """Форматирует количество часов в читаемый вид"""
    if hours is None:
        return ""
    if hours < 1:
        return "только что"
    elif hours < 24:
        h = int(hours)
        return f"{h} ч. назад"
    else:
        days = int(hours // 24)
        return f"{days} дн. назад"

def get_news_data():
    """Новости из RSS: только за последние 12 часов, со встроенными ссылками"""
    try:
        feeds = [
            "http://feeds.reuters.com/reuters/businessNews",
            "https://cointelegraph.com/rss"
        ]
        headlines = []
        
        for feed_url in feeds:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                # Проверяем возраст новости — только до 12 часов
                hours_ago = get_hours_ago(entry.get('published_parsed'))
                if hours_ago is None or hours_ago > 12:
                    continue  # Пропускаем старые новости
                
                title = entry.title
                link = entry.get('link', '')
                time_label = format_time_ago(hours_ago)
                
                # Экранируем спецсимволы Markdown в заголовке
                title_safe = title.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('`', '\\`')
                
                # Формат: ссылка встроена в текст, время в начале
                time_prefix = f"[{time_label}] " if time_label else ""
                
                if link:
                    # Ссылка встроена в текст новости
                    headlines.append(f"• {time_prefix}{title_safe} — [источник]({link})")
                else:
                    headlines.append(f"• {time_prefix}{title_safe}")
                
                # Берём максимум 5 свежих новостей
                if len(headlines) >= 5:
                    break
            if len(headlines) >= 5:
                break
        
        if not headlines:
            return "• Новостей за последние 12 часов не обнаружено — фон спокойный"
        
        return "\n".join(headlines)
    except Exception as e:
        return f"• Новости: Ошибка сбора данных ({str(e)[:30]})"

# ==========================================
# 3. ИИ-АНАЛИЗ (OPENROUTER) С УЧЕТОМ СЕССИИ
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
    
    if fg_value <= 24:
        fg_emoji = "🔴"
        fg_signal = "ПАНИКА — возможны покупки на дне"
    elif fg_value <= 49:
        fg_emoji = "🟠"
        fg_signal = "СТРАХ — рынок осторожничает"
    elif fg_value <= 51:
        fg_emoji = "🟡"
        fg_signal = "НЕЙТРАЛЬНО — неопределенность"
    elif fg_value <= 74:
        fg_emoji = ""
        fg_signal = "ЖАДНОСТЬ — осторожно с FOMO"
    else:
        fg_emoji = "🔴"
        fg_signal = "ЭКСТРЕМАЛЬНАЯ ЖАДНОСТЬ — высокая вероятность коррекции"
    
    prompt = f"""Ты — «Пожарный Шпион», элитный автономный ИИ-аналитик. Создай ПРОФЕССИОНАЛЬНЫЙ обзор рынка для Telegram-канала.

КОНТЕКСТ ВЫПУСКА:
- Тип: {session_info['name']} выпуск
- Дата: {session_info['date']}
- Время публикации: {session_info['time']} МСК
- АНАЛИЗИРУЕМЫЙ ПЕРИОД: {session_info['period']}
- ВАЖНО: Все выводы делай ИМЕННО за этот период!

РЕАЛЬНЫЕ ДАННЫЕ:
[ИНДЕКС СТРАХА/ЖАДНОСТИ]: {fg_value}/100 ({fg_class}) → {fg_emoji} {fg_signal}
[ДОМИНАЦИЯ BTC]: {btc_dom:.1f}%
[ОБЩАЯ КАПИТАЛИЗАЦИЯ]: ${total_mcap:.0f}B
[КРИПТА С ОБЪЕМАМИ]: {crypto}
[УРОВНИ BTC]: {support_resistance}
[ТРАДИЦИОННЫЕ РЫНКИ]: {finance}
[НОВОСТИ ЗА 12 ЧАСОВ]: {news}

СТРОГАЯ СТРУКТУРА (НЕ ПРОПУСКАЙ НИ ОДИН БЛОК):

🔥 ПОЖАРНЫЙ ШПИОН: {session_info['name']} ОБЗОР — {session_info['date']}

📊 ПЕРИОД АНАЛИЗА: {session_info['period']}

⚠️ Сначала риски, потом возможности!

🌍 РЫНОЧНЫЙ СРЕЗ:
- {fg_emoji} Индекс страха/жадности: {fg_value}/100 ({fg_class})
- Расшифровка: 0-24=Extreme Fear, 25-49=Fear, 50=Neutral, 51-74=Greed, 75-100=Extreme Greed
- Ключевые движения BTC и ETH за АНАЛИЗИРУЕМЫЙ ПЕРИОД

🎯 УРОВНИ BTC:
- Поддержка: [из данных]
- Сопротивление: [из данных]
- Текущая цена: [из данных]
- Вывод: близко к поддержке/сопротивлению/между ними

🐋 ДЕЙСТВИЯ КИТОВ:
- Куда перетекает капитал за этот период
- Институциональная активность

📰 ГЛАВНЫЕ НОВОСТИ:
- 2-3 новости из блока [НОВОСТИ ЗА 12 ЧАСОВ]
- СОХРАНЯЙ КЛИКАБЕЛЬНЫЕ ССЫЛКИ В ФОРМАТЕ [источник](url) — НЕ УДАЛЯЙ ИХ!
- Сохрани временные метки [X ч. назад] из исходных данных
- Влияние на рынок (1 предложение)

⚠️ РИСК-ПРЕДУПРЕЖДЕНИЕ:
"Торговля на финансовых рынках сопряжена с высоким риском потери средств. Вы можете потерять ВЕСЬ депозит."

🎯 ТОРГОВЫЕ ИДЕИ (3 совета):
1️⃣ [Конкретное действие]: [Пояснение с процентами]
2️⃣ [Конкретное действие]: [Пояснение с процентами]
3️ [Конкретное действие]: [Пояснение с процентами]

⚡ QUICK STATS (с ЦВЕТОВОЙ КОДИРОВКОЙ):
Используй эмодзи-цвета для сигналов:
- 🟢 зеленый = бычий сигнал / рост
- 🔴 красный = медвежий сигнал / падение / риск
- 🟡 желтый = нейтрально / предупреждение / внимание
- 🔵 синий = факт / объем / нейтральная статистика

Формат каждого пункта: "[цвет] [Актив/метрика]: [значение] — [короткий вывод]"

ОБЯЗАТЕЛЬНО включи в Quick Stats:
- Доминацию BTC с комментарием
- Индекс страха/жадности с цветовой кодировкой
- Все активы из входных данных (крипта, сырьё, индексы)

⚖️ ДИСКЛЕЙМЕР:
"⚠️ Вся информация носит ИСКЛЮЧИТЕЛЬНО ознакомительный характер и НЕ является индивидуальной инвестиционной рекомендацией. Финансовые рынки сопряжены с высоким риском потери средств (вплоть до 100% депозита). Вы действуете на свой страх и риск (DYOR). Прошлые результаты не гарантируют будущую прибыль."

ВАЖНО: НЕ добавляй в конец информацию о следующем выпуске или призывы подписаться — это добавит система автоматически после твоего текста.

ПРАВИЛА:
- **Жирный шрифт** для цифр ($79,667) и активов (BTC, ETH)
- Эмодзи: умеренно, только для структуры и цветовой кодировки
- Сленг с расшифровками в скобках
- Тон: ПРОФЕССИОНАЛЬНЫЙ, ОСТОРОЖНЫЙ
- ОБЪЕМ: Пиши ПОДРОБНО, но БЕЗ ВОДЫ. Система автоматически разобьет на части.
- НЕ используй "---" между блоками
- Разбивай текст на абзацы (двойной перенос строки между блоками)

ПРИСТУПАЙ!"""
    
    for model in models:
        print(f"   Пробуем модель: {model}")
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
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            if response.status_code == 200:
                print(f"   ✅ Модель {model} ответила успешно!")
                return response.json()['choices'][0]['message']['content']
            elif response.status_code == 429:
                print(f"   ⚠️ Модель {model} перегружена (429). Пробуем следующую...")
                continue
            else:
                print(f"   ❌ Модель {model} вернула ошибку {response.status_code}")
        except Exception as e:
            print(f"   ❌ Ошибка при запросе к {model}: {e}")
            continue
            
    return "Ошибка: ИИ временно недоступен. Попробуйте позже."

# ==========================================
# 4. ФУТЕР ПОСТА (СЛЕДУЮЩИЙ ВЫПУСК + ПОЖАРНЫЙ ШПИОН)
# ==========================================
def get_post_footer(session_info):
    """Генерирует информационный футер поста"""
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

 ПОЖАРНЫЙ ШПИОН — система экстренных оповещений
Система автоматически мониторит рынки и геополитику. При резких изменениях, которые могут повлиять на ваши позиции, в канал придёт экстренный сигнал.

👍 Если обзор был полезен — ставь реакцию!
📢 Подписывайся на канал, чтобы не пропустить важные сигналы."""
    
    return footer

# ==========================================
# 5. УМНАЯ ОТПРАВКА В TELEGRAM С НАРЕЗКОЙ
# ==========================================
def send_to_telegram(text):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    channel_id = os.environ.get("TELEGRAM_CHANNEL_ID")
    
    # 1. Отправляем обложку
    seed = random.randint(1, 99999)
    image_url = f"https://image.pollinations.ai/prompt/cyberpunk%20financial%20market%20data%20dark%20neon%20glowing%20charts?width=1200&height=600&nologo=true&seed={seed}"
    
    caption = "🔥 ПОЖАРНЫЙ ШПИОН НА СВЯЗИ\n\nСистема завершила анализ 8 ветвей рынка. Полный разбор ниже 👇"
    
    photo_payload = {
        "chat_id": channel_id,
        "photo": image_url,
        "caption": caption,
        "parse_mode": "Markdown"
    }
    requests.post(f"https://api.telegram.org/bot{bot_token}/sendPhoto", json=photo_payload, timeout=15)
    time.sleep(2)
    
    # 2. УМНАЯ НАРЕЗКА
    max_len = 4000
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
    
    # 3. Отправляем каждую часть
    total_parts = len(parts)
    
    for i, part in enumerate(parts):
        if i > 0:
            time.sleep(3)
        
        if total_parts > 1:
            header = f"📄 **ЧАСТЬ {i+1}/{total_parts}**\n\n"
            footer = f"\n\n_...продолжение следует (часть {i+1}/{total_parts})_" if i < total_parts - 1 else ""
            part_with_indicator = header + part + footer
        else:
            part_with_indicator = part
        
        if len(part_with_indicator) > 4090:
            part_with_indicator = part_with_indicator[:4080] + "\n\n_...текст обрезан из-за ограничения длины_"
        
        text_payload = {
            "chat_id": channel_id,
            "text": part_with_indicator,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True  # ОТКЛЮЧАЕМ РАЗВОРАЧИВАНИЕ ССЫЛОК В КАРТОЧКИ
        }
        response = requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json=text_payload, timeout=15)
        
        if response.status_code == 200:
            print(f"✅ Часть {i+1}/{total_parts} отправлена! (длина: {len(part_with_indicator)})")
        else:
            print(f"❌ Ошибка части {i+1}: {response.text}")

# ==========================================
# 6. ГЛАВНЫЙ ЗАПУСК
# ==========================================
def main():
    print(" Запуск Пожарного Шпиона v24.1...")
    
    print(" Определение типа выпуска...")
    session_info = get_session_info()
    print(f"   Тип: {session_info['name']} выпуск")
    print(f"   Период: {session_info['period']}")
    
    print("📡 Сбор данных...")
    fear_greed = get_fear_greed_index()
    global_data = get_global_data()
    crypto = get_crypto_data()
    support_resistance = get_support_resistance()
    finance = get_finance_data()
    news = get_news_data()
    
    print("🧠 ИИ-анализ (это может занять 30-60 секунд)...")
    try:
        analysis = get_ai_analysis(session_info, fear_greed, global_data, crypto, support_resistance, finance, news)
    except Exception as e:
        print(f"❌ Ошибка ИИ-анализа: {e}")
        analysis = "Ошибка генерации анализа. Попробуйте позже."
    
    print("📎 Добавление футера...")
    footer = get_post_footer(session_info)
    full_text = analysis + "\n\n" + footer
    
    print(f"📏 Длина текста: {len(full_text)} символов")
    
    print("📤 Публикация...")
    send_to_telegram(full_text)
    print("✅ Миссия выполнена.")

if __name__ == "__main__":
    main()
