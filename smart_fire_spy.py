import os
import requests
import json
import logging
from datetime import datetime, timedelta
import yfinance as yf
import feedparser

from ai_models_config import get_models_for_task

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

LAST_SIGNALS_FILE = "last_signals.json"
ALERT_THRESHOLD_PERCENT = 3.0  # Триггер: падение цены на X% от точки входа или максимума

def get_last_signal():
    """Читает последний отправленный торговый сигнал"""
    try:
        if os.path.exists(LAST_SIGNALS_FILE):
            with open(LAST_SIGNALS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                signals = data.get("signals", [])
                if signals:
                    return signals[-1] # Берем самый свежий
    except Exception as e:
        logging.error(f"Ошибка чтения last_signals.json: {e}")
    return None

def check_price_drop(symbol: str) -> tuple:
    """Проверяет, не упала ли цена монеты критически"""
    try:
        yf_symbol = symbol.replace('USDT', '-USD')
        asset = yf.Ticker(yf_symbol)
        hist = asset.history(period="1d", interval="15m")
        
        if not hist.empty:
            current_price = float(hist['Close'].iloc[-1])
            high_price = float(hist['High'].max())
            
            # Считаем просадку от локального максимума за день
            drop_from_high = ((current_price - high_price) / high_price) * 100
            if drop_from_high <= -ALERT_THRESHOLD_PERCENT:
                return True, current_price, f"Цена упала на {abs(drop_from_high):.2f}% от дневного максимума (${high_price:.2f})"
                
    except Exception as e:
        logging.warning(f"Не удалось проверить цену для {symbol}: {e}")
    return False, 0.0, ""

def get_coin_news(coin_name: str):
    """Ищет новости по конкретной монете или общие рыночные новости"""
    feeds = [
        "https://cointelegraph.com/rss",
        "http://feeds.reuters.com/reuters/businessNews"
    ]
    news_items = []
    search_term = coin_name.replace('USDT', '').lower()
    
    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:
                title = entry.title.lower()
                # Простая фильтрация по имени монеты
                if search_term in title or len(news_items) < 3:
                    link = entry.get('link', '')
                    summary = entry.get('summary', '')[:150]
                    if link:
                        news_items.append(f"• [{entry.title}]({link})\n  _{summary}_")
        except Exception as e:
            logging.warning(f"Ошибка загрузки новостей: {e}")
            
    return "\n".join(news_items[:4]) if news_items else "Срочных новостей по активу не найдено."

def analyze_threat_with_ai(symbol: str, price_info: str, news: str) -> str:
    """ИИ анализирует, есть ли реальная угроза для позиции"""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return None
        
    # Берем только выделенные модели для пожарного бота
    models = get_models_for_task('smart_fire_spy')
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    prompt = f"""Ты — опытный риск-менеджер криптовалютного рынка.
Текущая ситуация:
- Актив: {symbol}
- Движение цены: {price_info}
- Последние новости: 
{news}

ЗАДАЧА:
Оцени, есть ли реальная угроза для трейдеров, находящихся в позиции по этому активу. 
Если угроза есть (негативные новости, пробой поддержки, общий обвал рынка), напиши краткое экстренное предупреждение и план действий.
Если это просто шум или нормальная коррекция, верни строго строку: NO_THREAT

ФОРМАТ ОТВЕТА (если есть угроза):
🚨 **ВНИМАНИЕ: УГРОЗА ДЛЯ ПОЗИЦИИ {symbol}**

📉 **Причина:** [Кратко, 1-2 предложения]
📰 **Новостной фон:** [Суть новости или отсутствие негатива]

🎯 **ПЛАН ДЕЙСТВИЙ:**
• Если в лонге: [конкретный совет, например, подтянуть стоп или зафиксировать]
• Если в шорте: [конкретный совет]
• Общий совет: [например, снизить риск или выйти]

Если угрозы нет, ответь строго: NO_THREAT
"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/volk6691ilya-lgtm/domik-na-obochine",
        "X-Title": "Smart Fire Spy"
    }
    
    for model in models:
        try:
            payload = {"model": model, "messages": [{"role": "user", "content": prompt}]}
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    content = result['choices'][0]['message']['content'].strip()
                    if "NO_THREAT" not in content and len(content) > 50:
                        return content
        except Exception:
            continue
    return None

def send_smart_alert(text: str):
    """Отправляет экстренное сообщение в Telegram"""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    channel_id = os.environ.get("TELEGRAM_CHANNEL_ID")
    if not bot_token or not channel_id:
        logging.error("Отсутствуют токены Telegram")
        return
        
    payload = {
        "chat_id": channel_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        response = requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json=payload, timeout=15)
        if response.status_code == 200:
            logging.info("✅ Экстренный сигнал отправлен!")
        else:
            logging.error(f"❌ Ошибка отправки: {response.text}")
    except Exception as e:
        logging.error(f"❌ Сбой отправки: {e}")

def main():
    logging.info("🔥 Запуск Умного Пожарного Бота v1.0...")
    
    last_signal = get_last_signal()
    if not last_signal:
        logging.info("ℹ️ Нет активных торговых сигналов за последние 24 часа. Выход.")
        return
        
    symbol = last_signal["symbol"]
    direction = last_signal["direction"]
    logging.info(f"🎯 Мониторинг последнего сигнала: {symbol} ({direction})")
    
    is_drop, current_price, drop_reason = check_price_drop(symbol)
    
    if is_drop:
        logging.warning(f"⚠️ Обнаружено критическое движение: {drop_reason}")
        news = get_coin_news(symbol)
        logging.info("🧠 Анализ угрозы через выделенные ИИ-модели...")
        threat_analysis = analyze_threat_with_ai(symbol, drop_reason, news)
        
        if threat_analysis:
            logging.info("🚨 Угроза подтверждена ИИ! Отправка алерта...")
            send_smart_alert(threat_analysis)
        else:
            logging.info("✅ ИИ решил, что это нормальный рыночный шум. Алерт не отправлен.")
    else:
        logging.info("✅ Цена в пределах нормы. Молчим.")
        
    logging.info("✅ Проверка завершена.")

if __name__ == "__main__":
    main()
