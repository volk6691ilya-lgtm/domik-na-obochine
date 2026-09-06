import os
import requests
import time
import yfinance as yf
from datetime import datetime, timedelta, timezone
from io import BytesIO
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# ==========================================
# КОНФИГУРАЦИЯ
# ==========================================
ALERT_THRESHOLD_CRYPTO = 3.0  # % за час для крипты
ALERT_THRESHOLD_STOCKS = 2.0  # % за час для акций/сырья
CHECK_INTERVAL = 15  # минут между проверками
MAX_ALERTS_PER_HOUR = 1  # максимум сигналов в час

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
# 1. ПРОВЕРКА РЕЗКИХ ДВИЖЕНИЙ
# ==========================================
def check_price_movements():
    """Проверяет резкие движения цен за последний час"""
    alerts = []
    
    # Проверяем крипту
    for ticker, name in CRYPTO_TICKERS.items():
        try:
            asset = yf.Ticker(ticker)
            # Берём данные за последние 2 часа с 5-минутным интервалом
            hist = asset.history(period="2h", interval="5m")
            
            if not hist.empty and len(hist) >= 12:  # минимум 12 свечей (1 час)
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
            hist = asset.history(period="2h", interval="5m")
            
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
            print(f"⚠️ Ошибка проверки {name}: {e}")
    
    return alerts

# ==========================================
# 2. ГЕНЕРАЦИЯ ГРАФИКА (1 ЧАС)
# ==========================================
def generate_alert_chart(alert):
    """Генерирует график за последний час для экстренного сигнала"""
    try:
        asset = yf.Ticker(alert['ticker'])
        hist = asset.history(period="2h", interval="5m")
        
        if hist.empty:
            return None
        
        # Берём последний час
        hist = hist.tail(12)
        
        fig, ax = plt.subplots(figsize=(10, 6), facecolor='#0d1117')
        
        # Определяем цвет в зависимости от направления
        if alert['change'] > 0:
            color = '#00ff00'  # зелёный для роста
            title_emoji = "📈"
        else:
            color = '#ff0000'  # красный для падения
            title_emoji = "📉"
        
        # Рисуем график
        ax.plot(hist.index, hist['Close'], color=color, linewidth=2.5, label=f"{alert['name']} Price")
        ax.fill_between(hist.index, hist['Close'].min(), hist['Close'], alpha=0.3, color=color)
        
        # Добавляем текущую цену
        current_price = hist['Close'].iloc[-1]
        ax.axhline(y=current_price, color='white', linestyle='--', alpha=0.5, linewidth=1)
        
        # Заголовок
        change_emoji = "🔴" if alert['change'] < 0 else "🟢"
        ax.set_title(
            f'{title_emoji} ПОЖАРНЫЙ ШПИОН: {alert["name"]} {change_emoji} {alert["change"]:+.2f}%\n'
            f'Текущая цена: ${current_price:,.2f}',
            color='white',
            fontsize=14,
            fontweight='bold',
            pad=20
        )
        
        # Форматирование
        ax.set_ylabel('Цена ($)', color='white', fontsize=11)
        ax.legend(loc='upper left', facecolor='#161b22', edgecolor=color, labelcolor='white', fontsize=10)
        ax.grid(True, alpha=0.2, color='white')
        ax.set_facecolor('#161b22')
        
        # Формат времени
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=15))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, color='white')
        ax.tick_params(colors='white')
        
        plt.tight_layout()
        
        # Сохраняем в буфер
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='#0d1117')
        buf.seek(0)
        plt.close()
        
        return buf
    except Exception as e:
        print(f"❌ Ошибка генерации графика: {e}")
        return None

# ==========================================
# 3. ПОЛУЧЕНИЕ НОВОСТЕЙ ДЛЯ АНАЛИЗА
# ==========================================
def get_recent_news():
    """Получает последние новости для анализа причины скачка"""
    try:
        import feedparser
        feeds = [
            "http://feeds.reuters.com/reuters/businessNews",
            "https://cointelegraph.com/rss"
        ]
        headlines = []
        for feed_url in feeds:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:2]:  # только 2 последние новости
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
# 4. ОТПРАВКА ЭКСТРЕННОГО СИГНАЛА
# ==========================================
def send_alert(alert, chart_buffer):
    """Отправляет экстренный сигнал в Telegram"""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    channel_id = os.environ.get("TELEGRAM_CHANNEL_ID")
    
    # Формируем текст сигнала
    change_emoji = "🔴" if alert['change'] < 0 else "🟢"
    direction = "ПАДЕНИЕ" if alert['change'] < 0 else "РОСТ"
    
    # Получаем новости для контекста
    news = get_recent_news()
    
    # Формируем план действий
    if alert['change'] < 0:
        action_plan = f"""
 ЧТО ДЕЛАТЬ:
- Если в лонге: рассмотрите стоп-лосс ниже ${alert['current_price'] * 0.97:,.0f} (-3%)
- Если в шорте: тейк-профит на ${alert['current_price'] * 0.95:,.0f} (-5%)
- Если вне рынка: не ловите падающий нож, ждите стабилизации
"""
    else:
        action_plan = f"""
🎯 ЧТО ДЕЛАТЬ:
- Если в шорте: рассмотрите стоп-лосс выше ${alert['current_price'] * 1.03:,.0f} (+3%)
- Если в лонге: тейк-профит на ${alert['current_price'] * 1.05:,.0f} (+5%)
- Если вне рынка: не входите на хаях, ждите отката к ${alert['current_price'] * 0.98:,.0f}
"""
    
    alert_text = f"""
{change_emoji} ПОЖАРНЫЙ ШПИОН: ЭКСТРЕННЫЙ СИГНАЛ

{alert['name']}: {alert['change']:+.2f}% за последний час
Текущая цена: ${alert['current_price']:,.2f}

📊 ГРАФИК: см. выше

 ВОЗМОЖНАЯ ПРИЧИНА:
{news}

{action_plan}
⚠️ РИСК-ПРЕДУПРЕЖДЕНИЕ:
Торговля сопряжена с высоким риском потери средств. Вы можете потерять ВЕСЬ депозит. Никогда не инвестируйте больше, чем готовы потерять полностью.

️ ДИСКЛЕЙМЕР:
Вся информация носит ИСКЛЮЧИТЕЛЬНО ознакомительный характер и НЕ является индивидуальной инвестиционной рекомендацией. Финансовые рынки сопряжены с высоким риском потери средств (вплоть до 100% депозита). Вы действуете на свой страх и риск (DYOR). Прошлые результаты не гарантируют будущую прибыль.
"""
    
    # Отправляем график
    if chart_buffer:
        print("📊 Отправка графика...")
        files = {
            'photo': ('alert_chart.png', chart_buffer, 'image/png'),
            'chat_id': (None, channel_id),
            'caption': (None, f"{change_emoji} ПОЖАРНЫЙ ШПИОН: {alert['name']} {alert['change']:+.2f}%"),
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
        print(f"✅ Экстренный сигнал отправлен! {alert['name']}: {alert['change']:+.2f}%")
    else:
        print(f"❌ Ошибка отправки сигнала: {response.text}")

# ==========================================
# 5. ГЛАВНЫЙ ЦИКЛ МОНИТОРИНГА
# ==========================================
def main():
    print(" Запуск Пожарного Шпиона...")
    print(f" Мониторинг: {len(CRYPTO_TICKERS)} крипто + {len(STOCK_TICKERS)} акций/сырья")
    print(f"⏰ Интервал проверки: {CHECK_INTERVAL} минут")
    print(f"🚨 Порог сигнала: {ALERT_THRESHOLD_CRYPTO}% (крипта), {ALERT_THRESHOLD_STOCKS}% (акции)")
    
    alerts_sent = 0
    last_alert_time = None
    
    while True:
        try:
            print(f"\n🔍 Проверка рынков... ({datetime.now().strftime('%H:%M:%S')})")
            
            # Проверяем, не превышен ли лимит сигналов в час
            if last_alert_time:
                time_since_last = (datetime.now() - last_alert_time).total_seconds() / 3600
                if time_since_last < 1 and alerts_sent >= MAX_ALERTS_PER_HOUR:
                    print(f"️ Лимит сигналов достигнут ({MAX_ALERTS_PER_HOUR}/час). Ждём...")
                    time.sleep(CHECK_INTERVAL * 60)
                    continue
            
            # Проверяем движения
            alerts = check_price_movements()
            
            if alerts:
                print(f"🚨 Обнаружено {len(alerts)} резких движений!")
                
                for alert in alerts:
                    # Генерируем график
                    chart_buffer = generate_alert_chart(alert)
                    
                    # Отправляем сигнал
                    send_alert(alert, chart_buffer)
                    
                    alerts_sent += 1
                    last_alert_time = datetime.now()
                    
                    # Пауза между сигналами
                    time.sleep(5)
            else:
                print("✅ Резких движений не обнаружено")
            
            # Ждём до следующей проверки
            print(f"💤 Следующая проверка через {CHECK_INTERVAL} минут...")
            time.sleep(CHECK_INTERVAL * 60)
            
        except KeyboardInterrupt:
            print("\n🛑 Мониторинг остановлен пользователем")
            break
        except Exception as e:
            print(f"❌ Ошибка в главном цикле: {e}")
            time.sleep(CHECK_INTERVAL * 60)

if __name__ == "__main__":
    main()
