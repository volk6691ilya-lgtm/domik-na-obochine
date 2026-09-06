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
ALERT_THRESHOLD_CRYPTO = 3.0  # % за час для крипты
ALERT_THRESHOLD_STOCKS = 2.0  # % за час для акций/сырья
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
        
        # Получаем последние сообщения из канала
        url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            updates = response.json().get('result', [])
            
            # Ищем последнее сообщение от бота в канале
            for update in reversed(updates):
                if 'channel_post' in update:
                    post = update['channel_post']
                    if post.get('chat', {}).get('id') == int(channel_id):
                        # Проверяем, был ли это сигнал Пожарного Шпиона
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
    
    # Проверяем крипту
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
            print(f"⚠️ Ошибка проверки {name}: {e}")
    
    # Проверяем акции/сырьё
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
# 3. ГЕНЕРАЦИЯ ГРАФИКА
# ==========================================
def generate_alert_chart(alerts):
    """Генерирует график для всех алертов"""
    try:
        if not alerts:
            return None
        
        # Берём первый алерт для графика (самый сильный)
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
            f'Текущая цена: ${current_price:,.2f}',
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
        print(f" Ошибка генерации графика: {e}")
        return None

# ==========================================
# 4. ПОЛУЧЕНИЕ НОВОСТЕЙ
# ==========================================
def get_recent_news():
    """Получает последние новости"""
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
                
                title_safe = title.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('`', '\\`')
                
                if link:
                    headlines.append(f"[{title_safe}]({link})")
                else:
                    headlines.append(title_safe)
        
        return "\n".join(headlines[:3])
    except Exception as e:
        return "Новости недоступны"

# ==========================================
# 5. ОТПРАВКА СИГНАЛА
# ==========================================
def send_alert(alerts, chart_buffer):
    """Отправляет объединённый сигнал"""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    channel_id = os.environ.get("TELEGRAM_CHANNEL_ID")
    
    # Формируем список алертов
    alerts_text = ""
    for alert in alerts:
        change_emoji = "" if alert['change'] < 0 else "🟢"
        alerts_text += f"{change_emoji} {alert['name']}: {alert['change']:+.2f}% (цена: ${alert['current_price']:,.2f})\n"
    
    # Определяем общее направление
    avg_change = sum(a['change'] for a in alerts) / len(alerts)
    direction = "ПАДЕНИЕ" if avg_change < 0 else "РОСТ"
    
    # Получаем новости
    news = get_recent_news()
    
    # Формируем план действий
    if avg_change < 0:
        action_plan = """
🎯 ЧТО ДЕЛАТЬ:
- Если в лонге: рассмотрите стоп-лосс ниже текущей цены (-3-5%)
- Если в шорте: зафиксируйте часть прибыли
- Если вне рынка: не ловите падающий нож, ждите стабилизации
- Уменьшите размер позиций до прояснения ситуации
"""
    else:
        action_plan = """
🎯 ЧТО ДЕЛАТЬ:
- Если в шорте: рассмотрите стоп-лосс выше текущей цены (+3-5%)
- Если в лонге: зафиксируйте часть прибыли на сопротивлениях
- Если вне рынка: не входите на хаях, ждите отката
- Не поддавайтесь FOMO, даже если рынок растёт
"""
    
    alert_text = f"""
 ПОЖАРНЫЙ ШПИОН: ЭКСТРЕННЫЙ СИГНАЛ

Обнаружены резкие движения рынка:

{alerts_text}
📊 ГРАФИК: см. выше

🔍 ВОЗМОЖНЫЕ ПРИЧИНЫ:
{news}

{action_plan}
⚠️ РИСК-ПРЕДУПРЕЖДЕНИЕ:
Торговля на финансовых рынках сопряжена с высоким риском потери средств. Вы можете потерять ВЕСЬ депозит. Никогда не инвестируйте больше, чем готовы потерять полностью.

️ ДИСКЛЕЙМЕР:
⚠️ Вся информация носит ИСКЛЮЧИТЕЛЬНО ознакомительный характер и НЕ является индивидуальной инвестиционной рекомендацией. Финансовые рынки сопряжены с высоким риском потери средств (вплоть до 100% депозита). Вы действуете на свой страх и риск (DYOR — Do Your Own Research, проводите собственное исследование). Прошлые результаты не гарантируют будущую прибыль.
"""
    
    # Отправляем график
    if chart_buffer:
        print("📊 Отправка графика...")
        files = {
            'photo': ('alert_chart.png', chart_buffer, 'image/png'),
            'chat_id': (None, channel_id),
            'caption': (None, "🚨 ПОЖАРНЫЙ ШПИОН: Экстренный сигнал"),
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
        "parse_mode": "Markdown"
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
# 6. ГЛАВНЫЙ ЗАПУСК
# ==========================================
def main():
    print("🚨 Запуск Пожарного Шпиона...")
    print(f"📡 Мониторинг: {len(CRYPTO_TICKERS)} крипто + {len(STOCK_TICKERS)} акций/сырья")
    print(f"🚨 Порог: {ALERT_THRESHOLD_CRYPTO}% (крипта), {ALERT_THRESHOLD_STOCKS}% (акции)")
    print(f"️ Минимум между сигналами: {MINUTES_BETWEEN_ALERTS} минут")
    
    # Проверяем, не было ли недавнего сигнала
    if check_last_alert():
        print("✅ Проверка завершена (сигнал не отправлен).")
        return
    
    # Проверяем движения
    alerts = check_price_movements()
    
    if alerts:
        print(f"🚨 Обнаружено {len(alerts)} резких движений!")
        
        # Генерируем один график для всех
        chart_buffer = generate_alert_chart(alerts)
        
        # Отправляем объединённый сигнал
        send_alert(alerts, chart_buffer)
    else:
        print("✅ Резких движений не обнаружено. Молчим.")
    
    print("✅ Проверка завершена.")

if __name__ == "__main__":
    main()
