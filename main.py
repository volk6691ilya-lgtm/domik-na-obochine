import os
import requests
import json
import time
import random
import yfinance as yf
import feedparser
from datetime import datetime

# ==========================================
# 1. СБОР ДАННЫХ (5 ВЕТВЕЙ)
# ==========================================
def get_crypto_data():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana,ripple,toncoin&vs_currencies=usd&include_24hr_change=true"
        response = requests.get(url, timeout=10).json()
        data = []
        names = {"bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL", "ripple": "XRP", "toncoin": "TON"}
        for key, name in names.items():
            if key in response:
                price = response[key]['usd']
                change = response[key]['usd_24h_change']
                data.append(f"• {name}: ${price:,.2f} ({change:+.2f}%)")
        return "\n".join(data)
    except Exception as e:
        return f"• Крипта: Ошибка сбора данных ({str(e)[:30]})"

def get_finance_data():
    try:
        tickers = {"GC=F": "Золото", "SI=F": "Серебро", "BZ=F": "Нефть Brent", "^GSPC": "S&P 500", "NVDA": "NVIDIA"}
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
        return f"• Рынки: Ошибка сбора данных ({str(e)[:30]})"

def get_news_data():
    try:
        feeds = [
            "http://feeds.reuters.com/reuters/businessNews",
            "https://cointelegraph.com/rss"
        ]
        headlines = []
        for feed_url in feeds:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:2]: # Берем по 2 новости из каждого источника
                headlines.append(f"• {entry.title}")
        return "\n".join(headlines[:4]) # Максимум 4 заголовка
    except Exception as e:
        return "• Новости: Ошибка сбора данных"
# ==========================================
# 2. ИИ-АНАЛИЗ (OPENROUTER)
# ==========================================
def get_ai_analysis(crypto, finance, news):
    api_key = os.environ.get("OPENROUTER_API_KEY")
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    # Умный массив бесплатных моделей для переключения при перегрузке
    models = [
        "minimax/minimax-m3:free",
        "nvidia/nemotron-3.5-lightning:free",
        "inclusionai/ling-3.0-flash-fin:free"
    ]
    
        prompt = f"""Ты — «Пожарный Шпион», элитный автономный ИИ-аналитик с харизмой. Твоя задача: создать СОЧНЫЙ, СТРУКТУРИРОВАННЫЙ и ЦЕПЛЯЮЩИЙ обзор рынка для Telegram-канала.
    
            СЕГОДНЯШНЯЯ ДАТА: {datetime.now().strftime("%d.%m.%Y")}

            ВХОДНЫЕ ДАННЫЕ:
            [КРИПТА]: {crypto}
            [ТРАДИЦИОННЫЕ РЫНКИ И СЫРЬЕ]: {finance}
            [ГЕОПОЛИТИКА И НОВОСТИ]: {news}

            📋 СТРОГАЯ СТРУКТУРА ОТВЕТА (следуй ей ПО ПУНКТАМ):

            1. 🔥 ЗАГОЛОВОК: "ПОЖАРНЫЙ ШПИОН: ОБЗОР РЫНКА 🔥" + дата

            2.  ГЛОБАЛЬНЫЙ СРЕЗ (2-3 предложения):
               - Общее настроение рынка (быки/медведи, страх/жадность)
               - Выдели **ИНДЕКС СТРАХА/ЖАДНОСТИ** отдельной строкой с эмодзи 🌡️
               - Ключевые движения BTC и ETH

            3. 🐋 ДЕЙСТВИЯ КИТОВ (3-4 предложения):
               - Куда перетекает капитал (из чего во что)
               - Что делают институционалы
               - Скрытые сигналы из ончейн-данных

            4. 📰 ГЛАВНЫЕ НОВОСТИ (ОБЯЗАТЕЛЬНО!):
               - Перечисли 2-3 ключевые новости из блока [ГЕОПОЛИТИКА И НОВОСТИ]
               - Объясни их влияние на рынок (1 предложение на новость)
               - Если новостей нет — напиши " Новостной фон: Спокойный, без геополитических шоков"

            5. 🛡️ ТОРГОВАЯ ЭКСПЕРТИЗА (риск-менеджмент):
               - 3 конкретных совета с нумерацией 1️2️⃣3️
               - Формат: "[Действие]: [Пояснение]"
               - Пример: "1️⃣ Стоп-лоссы: Обязательно ставь защиту на 2-3% ниже входа..."

            6. ⚖️ ДИСКЛЕЙМЕР (ОБЯЗАТЕЛЬНО В КОНЦЕ):
               "️ **ЮРИДИЧЕСКИЙ ДИСКЛЕЙМЕР:** Вся информация носит исключительно ознакомительный характер и НЕ является индивидуальной инвестиционной рекомендацией. Финансовые рынки сопряжены с высоким риском потери средств. Вы действуете на свой страх и риск (DYOR — Do Your Own Research)."

                🎨 ПРАВИЛА ОФОРМЛЕНИЯ:
            - Используй **жирный шрифт** для ключевых цифр ($79,667) и активов (BTC, ETH, Золото)
            - Эмодзи: умеренно, только для структуры (📊🐋🛡️⚖️)
            - Сленг: используй ("ликвидации", "памп", "альты", "стэйблы"), но РАСШИФРОВЫВАЙ в скобках для новичков
            - Тон: УВЕРЕННЫЙ, СРОЧНЫЙ, но БЕЗОПАСТНЫЙ (не создавай панику)
            - Объем: 2500-3500 символов (чтобы влезло в 1 сообщение Telegram)

            ПРИСТУПАЙ К АНАЛИЗУ!"""
    
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
            continue # Пробуем следующую модель
            
    return "❌ Ошибка: ИИ-аналитик временно недоступен из-за высокой нагрузки. Попробуйте позже."

# ==========================================
# 3. ОТПРАВКА В TELEGRAM
# ==========================================
def send_to_telegram(text):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    channel_id = os.environ.get("TELEGRAM_CHANNEL_ID")
    
    # 1. Генерируем уникальную обложку со сбросом кэша
    seed = random.randint(1, 99999)
    image_url = f"https://image.pollinations.ai/prompt/cyberpunk%20financial%20market%20data%20dark%20neon%20glowing%20charts?width=1200&height=600&nologo=true&seed={seed}"
    
    # 2. Отправляем фото с коротким тизером (до 1024 символов)
    caption = "🔥 *ПОЖАРНЫЙ ШПИОН НА СВЯЗИ*\n\n_Система завершила анализ 5 ветвей рынка. Полный разбор ниже 👇_"
    
    photo_payload = {
        "chat_id": channel_id,
        "photo": image_url,
        "caption": caption,
        "parse_mode": "Markdown"
    }
    requests.post(f"https://api.telegram.org/bot{bot_token}/sendPhoto", json=photo_payload, timeout=15)
    time.sleep(2) # Пауза для защиты от Flood Wait
    
    # 3. Отправляем основной лонгрид
    text_payload = {
        "chat_id": channel_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    response = requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json=text_payload, timeout=15)
    
    if response.status_code == 200:
        print("✅ Пост успешно отправлен в Telegram!")
    else:
        print(f"❌ Ошибка Telegram: {response.text}")

# ==========================================
# 4. ГЛАВНЫЙ ЗАПУСК
# ==========================================
def main():
    print("🔥 Запуск Пожарного Шпиона v21.0...")
    print("📡 Сбор данных по 5 ветвям...")
    
    crypto = get_crypto_data()
    finance = get_finance_data()
    news = get_news_data()
    
    print("🧠 Запрос ИИ-анализа...")
    analysis = get_ai_analysis(crypto, finance, news)
    
    print("📤 Публикация в Telegram...")
    send_to_telegram(analysis)
    print("✅ Миссия выполнена.")

if __name__ == "__main__":
    main()
