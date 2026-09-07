import os
import requests
import time
import yfinance as yf
from datetime import datetime, timedelta, timezone
from io import BytesIO
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import feedparser

# ==========================================
# КОНФИГУРАЦИЯ
# ==========================================
ALERT_THRESHOLD_CRYPTO = 0.12  # % за час для крипты
ALERT_THRESHOLD_STOCKS = 0.09 # % за час для акций/сырья
MINUTES_BETWEEN_ALERTS = 60  # минимум минут между сигналами

# Тикеры для мониторинга
CRYPTO_TICKERS = {
    "BTC-USD": "BTC",
    "ETH-USD": "ETH",
    "SOL-USD": "SOL"
}

STOCK_TICKERS = {
    "^GSPC": "S&P 500",
    "GC=F": "Золото",
    "NVDA": "NVIDIA"
}

# ==========================================
# 1. ПРОВЕРКА ПОСЛЕДНЕГО СИГНАЛА
# ==========================================
def check_last_alert():
    """Проверяет, когда был последний сигнал в канале"""
    try:
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        channel_id = os.environ.get("TELEGRAM_CHANNEL_ID")
        
        url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            updates = response.json().get('result', [])
            
            for update in reversed(updates):
                if 'channel_post' in update:
                    post = update['channel_post']
                    if post.get('chat', {}).get('id') == int(channel_id):
                        if 'ПОЖАРНЫЙ ШПИОН' in post.get('text', ''):
                            post_time = datetime.fromtimestamp(post['date'])
                            minutes_ago = (datetime.now() - post_time).total_seconds() / 60
                            
                            if minutes_ago < MINUTES_BETWEEN_ALERTS:
                                print(f"⏸️ Последний сигнал был {minutes_ago:.0f} минут назад. Пропускаем.")
                                return True
        
        return False
    except Exception as e:
        print(f"⚠️ Ошибка проверки последнего сигнала: {e}")
        return False

# ==========================================
# 2. ПРОВЕРКА РЕЗКИХ ДВИЖЕНИЙ
# ==========================================
def check_price_movements():
    """Проверяет резкие движения цен за последний час"""
    alerts = []
    
    for ticker, name in CRYPTO_TICKERS.items():
        try:
            asset = yf.Ticker(ticker)
            hist = asset.history(period="1d", interval="5m")
            
            if not hist.empty and len(hist) >= 12:
                current_price = hist['Close'].iloc[-1]
                price_1h_ago = hist['Close'].iloc[-12]
                change_percent = ((current_price - price_1h_ago) / price_1h_ago) * 100
                
                if abs(change_percent) >= ALERT_THRESHOLD_CRYPTO:
                    alerts.append({
                        'name': name,
                        'ticker': ticker,
                        'current_price': current_price,
                        'change': change_percent,
                        'type': 'crypto'
                    })
                    print(f"🚨 {name}: {change_percent:+.2f}% за час!")
        except Exception as e:
            print(f"️ Ошибка проверки {name}: {e}")
    
    for ticker, name in STOCK_TICKERS.items():
        try:
            asset = yf.Ticker(ticker)
            hist = asset.history(period="1d", interval="5m")
            
            if not hist.empty and len(hist) >= 12:
                current_price = hist['Close'].iloc[-1]
                price_1h_ago = hist['Close'].iloc[-12]
                change_percent = ((current_price - price_1h_ago) / price_1h_ago) * 100
                
                if abs(change_percent) >= ALERT_THRESHOLD_STOCKS:
                    alerts.append({
                        'name': name,
                        'ticker': ticker,
                        'current_price': current_price,
                        'change': change_percent,
                        'type': 'stock'
                    })
                    print(f"🚨 {name}: {change_percent:+.2f}% за час!")
        except Exception as e:
            print(f"️ Ошибка проверки {name}: {e}")
    
    return alerts

# ==========================================
# 3. СБОР НОВОСТЕЙ (ГЕОПОЛИТИКА + IT + ФИНАНСЫ)
# ==========================================
def get_all_news():
    """Собирает новости из всех источников"""
    news_data = {
        'geopolitics': [],
        'it_tech': [],
        'finance': []
    }
    
    feeds = {
        'geopolitics': [
            "http://feeds.reuters.com/reuters/worldNews",
            "http://feeds.reuters.com/reuters/businessNews"
        ],
        'it_tech': [
            "https://techcrunch.com/feed/",
            "https://www.coindesk.com/arc/outboundfeeds/rss/"
        ],
        'finance': [
            "https://cointelegraph.com/rss",
            "http://feeds.reuters.com/reuters/businessNews"
        ]
    }
    
    for category, feed_urls in feeds.items():
        for feed_url in feed_urls:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:5]:
                    title = entry.title
                    link = entry.get('link', '')
                    summary = entry.get('summary', '')[:200]
                    
                    title_safe = title.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('`', '\\`')
                    
                    if link:
                        news_data[category].append({
                            'title': title_safe,
                            'link': link,
                            'summary': summary
                        })
            except Exception as e:
                print(f"⚠️ Ошибка загрузки {category} из {feed_url}: {e}")
    
    return news_data

# ==========================================
# 4. АНАЛИЗ ПРИЧИН ЧЕРЕЗ ИИ
# ==========================================
def analyze_causes_with_ai(alerts, news_data):
    """ИИ анализирует причины скачков на основе новостей"""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    
    if not api_key:
        print("⚠️ OPENROUTER_API_KEY не найден, используем простой анализ")
        return format_simple_causes(news_data)
    
    alerts_text = ""
    for alert in alerts:
        direction = "рост" if alert['change'] > 0 else "падение"
        alerts_text += f"- {alert['name']}: {alert['change']:+.2f}% ({direction})\n"
    
    news_text = ""
    for category, news_list in news_data.items():
        category_name = {
            'geopolitics': '🌐 ГЕОПОЛИТИКА',
            'it_tech': '💻 IT И ТЕХНОЛОГИИ',
            'finance': '📊 ФИНАНСЫ И КРИПТО'
        }.get(category, category)
        
        news_text += f"\n[{category_name}]:\n"
        for item in news_list[:3]:
            news_text += f"- {item['title']}\n  Ссылка: {item['link']}\n"
    
    prompt = f"""Произошли резкие движения рынка:

{alerts_text}

Последние новости:
{news_text}

ЗАДАЧА:
1. Определи, какие новости могли вызвать эти скачки
2. Для каждой причины укажи:
   - Краткое описание (1-2 предложения)
   - Кликабельную ссылку в формате [текст](url)
3. Если причин несколько — перечисли все
4. Если явной причины нет — так и скажи

ФОРМАТ ОТВЕТА (строго):
🔍 ПРИЧИНЫ СКАЧКА:

1. [Краткое описание] — [ссылка](url)
2. [Краткое описание] — [ссылка](url)

ИЛИ (если причин нет):
🔍 ПРИЧИНЫ СКАЧКА:
Явных новостных триггеров не обнаружено. Возможно, техническая коррекция или крупная сделка.

ОТВЕТЬ ТОЛЬКО В ЭТОМ ФОРМАТЕ, БЕЗ ДОПОЛНИТЕЛЬНЫХ КОММЕНТАРИЕВ."""
    
    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        payload = {
            "model": "minimax/minimax-m3:free",
            "messages": [{"role": "user", "content": prompt}]
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            print(f"⚠️ ИИ недоступен (статус {response.status_code}), используем простой анализ")
            return format_simple_causes(news_data)
    except Exception as e:
        print(f"️ Ошибка ИИ-анализа: {e}")
        return format_simple_causes(news_data)

# ==========================================
# 5. ПРОСТОЙ АНАЛИЗ (БЕЗ ИИ)
# ==========================================
def format_simple_causes(news_data):
    """Форматирует новости без ИИ-анализа"""
    causes_text = "🔍 **ПОСЛЕДНИЕ НОВОСТИ:**\n\n"
    
    for category, news_list in news_data.items():
        category_name = {
            'geopolitics': ' ГЕОПОЛИТИКА',
            'it_tech': '💻 IT И ТЕХНОЛОГИИ',
            'finance': ' ФИНАНСЫ'
        }.get(category, category)
        
        if news_list:
            causes_text += f"{category_name}:\n"
            for item in news_list[:2]:
                causes_text += f"• [{item['title']}]({item['link']})\n"
            causes_text += "\n"
    
    return causes_text

# ==========================================
# 6. ГЕНЕРАЦИЯ ГРАФИКА
# ==========================================
def generate_alert_chart(alerts):
    """Генерирует график для всех алертов"""
    try:
        if not alerts:
            return None
        
        main_alert = max(alerts, key=lambda x: abs(x['change']))
        
        asset = yf.Ticker(main_alert['ticker'])
        hist = asset.history(period="1d", interval="5m")
        
        if hist.empty:
            return None
        
        hist = hist.tail(12)
        
        fig, ax = plt.subplots(figsize=(10, 6), facecolor='#0d1117')
        
        if main_alert['change'] > 0:
            color = '#00ff00'
            title_emoji = "📈"
        else:
            color = '#ff0000'
            title_emoji = "📉"
        
        ax.plot(hist.index, hist['Close'], color=color, linewidth=2.5, label=f"{main_alert['name']} Price")
        ax.fill_between(hist.index, hist['Close'].min(), hist['Close'], alpha=0.3, color=color)
        
        current_price = hist['Close'].iloc[-1]
        ax.axhline(y=current_price, color='white', linestyle='--', alpha=0.5, linewidth=1)
        
        change_emoji = "🔴" if main_alert['change'] < 0 else "🟢"
        ax.set_title(
            f'{title_emoji} ПОЖАРНЫЙ ШПИОН: {main_alert["name"]} {change_emoji} {main_alert["change"]:+.2f}%\n'
            f'💰 Текущая цена: ${current_price:,.2f}',
            color='white',
            fontsize=14,
            fontweight='bold',
            pad=20
        )
        
        ax.set_ylabel('Цена ($)', color='white', fontsize=11)
        ax.legend(loc='upper left', facecolor='#161b22', edgecolor=color, labelcolor='white', fontsize=10)
        ax.grid(True, alpha=0.2, color='white')
        ax.set_facecolor('#161b22')
        
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=15))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, color='white')
        ax.tick_params(colors='white')
        
        plt.tight_layout()
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='#0d1117')
        buf.seek(0)
        plt.close()
        
        return buf
    except Exception as e:
        print(f"⚠️ Ошибка генерации графика: {e}")
        return None

# ==========================================
# 7. ОТПРАВКА СИГНАЛА
# ==========================================
def send_alert(alerts, chart_buffer, causes_text):
    """Отправляет сигнал с анализом причин"""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    channel_id = os.environ.get("TELEGRAM_CHANNEL_ID")
    
    # Формируем список алертов с эмодзи
    alerts_text = ""
    for alert in alerts:
        change_emoji = "🟢" if alert['change'] > 0 else "🔴"
        alerts_text += f"{change_emoji} **{alert['name']}**: {alert['change']:+.2f}% (💰 цена: ${alert['current_price']:,.2f})\n"
    
    # Определяем общее направление
    avg_change = sum(a['change'] for a in alerts) / len(alerts)
    
    # Формируем план действий с эмодзи
    if avg_change < 0:
        action_plan = """
🎯 **ЧТО ДЕЛАТЬ:**
• 🔻 Если в лонге: рассмотрите стоп-лосс ниже текущей цены (-3-5%)
• 🔺 Если в шорте: зафиксируйте часть прибыли
• ⏸️ Если вне рынка: не ловите падающий нож, ждите стабилизации
•  Уменьшите размер позиций до прояснения ситуации
"""
    else:
        action_plan = """
🎯 **ЧТО ДЕЛАТЬ:**
• 🔺 Если в шорте: рассмотрите стоп-лосс выше текущей цены (+3-5%)
• 🔻 Если в лонге: зафиксируйте часть прибыли на сопротивлениях
• ⏸️ Если вне рынка: не входите на хаях, ждите отката
• 🚫 Не поддавайтесь FOMO, даже если рынок растёт
"""
    
    alert_text = f"""
🚨 **ПОЖАРНЫЙ ШПИОН: ЭКСТРЕННЫЙ СИГНАЛ** 🚨

📊 **Обнаружены резкие движения рынка:**

{alerts_text}
📈 **ГРАФИК:** см. выше

{causes_text}
{action_plan}
⚠️ **РИСК-ПРЕДУПРЕЖДЕНИЕ:**
Торговля на финансовых рынках сопряжена с высоким риском потери средств. Вы можете потерять ВЕСЬ депозит. Никогда не инвестируйте больше, чем готовы потерять полностью.

️📜 **ДИСКЛЕЙМЕР:**
⚠️ Вся информация носит ИСКЛЮЧИТЕЛЬНО ознакомительный характер и НЕ является индивидуальной инвестиционной рекомендацией. Финансовые рынки сопряжены с высоким риском потери средств (вплоть до 100% депозита). Вы действуете на свой страх и риск (DYOR — Do Your Own Research, проводите собственное исследование). Прошлые результаты не гарантируют будущую прибыль.
"""
    
    # Отправляем график
    if chart_buffer:
        print("📊 Отправка графика...")
        files = {
            'photo': ('alert_chart.png', chart_buffer, 'image/png'),
            'chat_id': (None, channel_id),
            'caption': (None, "🚨💥 ПОЖАРНЫЙ ШПИОН: Экстренный сигнал"),
            'parse_mode': (None, 'Markdown')
        }
        response = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendPhoto",
            files=files,
            timeout=30
        )
        if response.status_code != 200:
            print(f"⚠️ Ошибка отправки графика: {response.text}")
        time.sleep(2)
    
    # Отправляем текст
    print("📤 Отправка текста сигнала...")
    text_payload = {
        "chat_id": channel_id,
        "text": alert_text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    response = requests.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        json=text_payload,
        timeout=15
    )
    
    if response.status_code == 200:
        print(f"✅ Сигнал отправлен! ({len(alerts)} активов)")
    else:
        print(f"❌ Ошибка отправки: {response.text}")

# ==========================================
# 8. ГЛАВНЫЙ ЗАПУСК
# ==========================================
def main():
    print("🔥 Запуск Пожарного Шпиона...")
    print(f" Мониторинг: {len(CRYPTO_TICKERS)} крипто + {len(STOCK_TICKERS)} акций/сырья")
    print(f"🚨 Порог: {ALERT_THRESHOLD_CRYPTO}% (крипта), {ALERT_THRESHOLD_STOCKS}% (акции)")
    
    if check_last_alert():
        print("✅ Проверка завершена (сигнал не отправлен).")
        return
    
    alerts = check_price_movements()
    
    if alerts:
        print(f"🚨 Обнаружено {len(alerts)} резких движений!")
        
        print("📰 Сбор новостей (геополитика + IT + финансы)...")
        news_data = get_all_news()
        
        print("🧠 ИИ-анализ причин скачка...")
        causes_text = analyze_causes_with_ai(alerts, news_data)
        
        chart_buffer = generate_alert_chart(alerts)
        
        send_alert(alerts, chart_buffer, causes_text)
    else:
        print("✅ Резких движений не обнаружено. Молчим.")
    
    print("✅ Проверка завершена.")

if __name__ == "__main__":
    main()
