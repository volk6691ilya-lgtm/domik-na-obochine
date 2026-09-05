import os
import requests
import json
import time
import random
import yfinance as yf
import feedparser
import pandas as pd
from datetime import datetime, timedelta

# ==========================================
# 1. СБОР РЕАЛЬНЫХ ДАННЫХ (7 ВЕТВЕЙ)
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
                market_cap = response[key].get('usd_market_cap', 0)
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
            resistance = high
            support = low
            return f"BTC: Поддержка ${support:,.0f} | Сопротивление ${resistance:,.0f} | Текущая ${close:,.0f}"
        return "BTC: Недоступно"
    except Exception as e:
        return f"BTC: Ошибка ({str(e)[:30]})"

def get_finance_data():
    """Традиционные рынки и сырье"""
    try:
        tickers = {"GC=F": "Золото", "SI=F": "Серебро", "BZ=F": "Нефть Brent", "^GSPC": "S&P 500", "NVDA": "NVIDIA", "^DXY": "Индекс доллара (DXY)"}
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

def get_news_data():
    """Новости из RSS"""
    try:
        feeds = [
            "http://feeds.reuters.com/reuters/businessNews",
            "https://cointelegraph.com/rss"
        ]
        headlines = []
        for feed_url in feeds:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:3]:
                headlines.append(f"• {entry.title}")
        return "\n".join(headlines[:5])
    except Exception as e:
        return "• Новости: Ошибка сбора данных"
# ==========================================
# 2. ИИ-АНАЛИЗ (OPENROUTER) С УЛУЧШЕННЫМ ПРОМПТОМ
# ==========================================
def get_ai_analysis(fear_greed, crypto, support_resistance, finance, news):
    api_key = os.environ.get("OPENROUTER_API_KEY")
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    models = [
        "minimax/minimax-m3:free",
        "nvidia/nemotron-3.5-lightning:free",
        "inclusionai/ling-3.0-flash-fin:free"
    ]
    
    today = datetime.now().strftime("%d.%m.%Y")
    fg_value, fg_class = fear_greed
    
    prompt = f"""Ты — «Пожарный Шпион», элитный автономный ИИ-аналитик. Создай ПРОФЕССИОНАЛЬНЫЙ обзор рынка для Telegram-канала.

ТЕКУЩАЯ ДАТА: {today} (используй ИМЕННО эту дату!)

РЕАЛЬНЫЕ ДАННЫЕ:
[ИНДЕКС СТРАХА/ЖАДНОСТИ]: {fg_value}/100 ({fg_class})
[КРИПТА С ОБЪЕМАМИ]: {crypto}
[УРОВНИ BTC]: {support_resistance}
[ТРАДИЦИОННЫЕ РЫНКИ]: {finance}
[НОВОСТИ]: {news}

СТРОГАЯ СТРУКТУРА (НЕ ПРОПУСКАЙ НИ ОДИН БЛОК):

🔥 ПОЖАРНЫЙ ШПИОН: ОБЗОР РЫНКА — {today}

⚠️ ВАЖНО: Сначала риски, потом возможности!

 РЫНОЧНЫЙ СРЕЗ:
- Индекс страха/жадности: {fg_value}/100 ({fg_class})
- Расшифровка: 0-24 = Extreme Fear, 25-49 = Fear, 50 = Neutral, 51-74 = Greed, 75-100 = Extreme Greed
- Ключевые движения BTC и ETH с объемами

🎯 УРОВНИ BTC:
- Поддержка: [из данных]
- Сопротивление: [из данных]
- Текущая цена: [из данных]
- Вывод: близко к поддержке/сопротивлению/между ними

🐋 ДЕЙСТВИЯ КИТОВ:
- Куда перетекает капитал
- Ончейн-сигналы (если есть в данных)
- Институциональная активность

📰 ГЛАВНЫЕ НОВОСТИ:
- 2-3 новости из блока [НОВОСТИ]
- Влияние на рынок (1 предложение)
- Если новостей нет: "📰 Новостной фон: Спокойный"

️ РИСК-МЕНЕДЖМЕНТ (ОБЯЗАТЕЛЬНО ПЕРЕД СОВЕТАМИ!):
️ Предупреждение: "Торговля на финансовых рынках сопряжена с высоким риском потери средств. Вы можете потерять ВЕСЬ депозит. Никогда не инвестируйте больше, чем готовы потерять полностью."

 ТОРГОВЫЕ ИДЕИ (3 совета):
1️⃣ [Конкретное действие]: [Пояснение с процентами]
2️⃣ [Конкретное действие]: [Пояснение с процентами]
3️⃣ [Конкретное действие]: [Пояснение с процентами]

⚡ QUICK STATS:
- 3-4 коротких факта с эмодзи

⚖️ ДИСКЛЕЙМЕР:
"⚠️ Вся информация носит ИСКЛЮЧИТЕЛЬНО ознакомительный характер и НЕ является индивидуальной инвестиционной рекомендацией. Финансовые рынки сопряжены с высоким риском потери средств (вплоть до 100% депозита). Вы действуете на свой страх и риск (DYOR — Do Your Own Research). Прошлые результаты не гарантируют будущую прибыль."

ПРАВИЛА:
- **Жирный шрифт** для цифр ($79,667) и активов (BTC, ETH)
- Эмодзи: умеренно, только для структуры
- Сленг с расшифровками в скобках
- Тон: ПРОФЕССИОНАЛЬНЫЙ, ОСТОРОЖНЫЙ, БЕЗ ПАНИКИ
- Объем: 2500-3500 символов
- НЕ используй "---" между блоками

ПРИСТУПАЙ!"""
    
    for model in models:
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
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        elif response.status_code == 429:
            continue
            
    return "Ошибка: ИИ временно недоступен. Попробуйте позже."

# ==========================================
# 3. ОТПРАВКА В TELEGRAM
# ==========================================
def send_to_telegram(text):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    channel_id = os.environ.get("TELEGRAM_CHANNEL_ID")
    
    seed = random.randint(1, 99999)
    image_url = f"https://image.pollinations.ai/prompt/cyberpunk%20financial%20market%20data%20dark%20neon%20glowing%20charts?width=1200&height=600&nologo=true&seed={seed}"
    
    caption = "🔥 ПОЖАРНЫЙ ШПИОН НА СВЯЗИ\n\nСистема завершила анализ 7 ветвей рынка. Полный разбор ниже 👇"
    
    photo_payload = {
        "chat_id": channel_id,
        "photo": image_url,
        "caption": caption,
        "parse_mode": "Markdown"
    }
    requests.post(f"https://api.telegram.org/bot{bot_token}/sendPhoto", json=photo_payload, timeout=15)
    time.sleep(2)
    
    text_payload = {
        "chat_id": channel_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    response = requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json=text_payload, timeout=15)
    
    if response.status_code == 200:
        print("✅ Пост успешно отправлен!")
    else:
        print(f"❌ Ошибка Telegram: {response.text}")

# ==========================================
# 4. ГЛАВНЫЙ ЗАПУСК
# ==========================================
def main():
    print(" Запуск Пожарного Шпиона v22.0 PROFESSIONAL...")
    
    print("📡 Сбор данных...")
    fear_greed = get_fear_greed_index()
    crypto = get_crypto_data()
    support_resistance = get_support_resistance()
    finance = get_finance_data()
    news = get_news_data()
    
    print("🧠 ИИ-анализ...")
    analysis = get_ai_analysis(fear_greed, crypto, support_resistance, finance, news)
    
    print("📤 Публикация...")
    send_to_telegram(analysis)
    print("✅ Миссия выполнена.")

if __name__ == "__main__":
    main()
