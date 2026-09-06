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
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

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
# 2. СБОР РЕАЛЬНЫХ ДАННЫХ
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
    """Новости из RSS с временными метками и ссылками"""
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
# 3. ГЕНЕРАЦИЯ ДАШБОРДА (12 ЧАСОВ)
# ==========================================
def generate_composite_chart(session_info):
    """Генерирует профессиональный 3-панельный график за 12 часов"""
    try:
        msk_tz = timezone(timedelta(hours=3))
        now = datetime.now(msk_tz)
        
        if session_info['type'] == 'morning':
            end_time = now.replace(hour=9, minute=0, second=0)
            start_time = end_time - timedelta(hours=12)
            period_label = "12 ЧАСОВ (ночная сессия)"
        else:
            end_time = now.replace(hour=21, minute=0, second=0)
            start_time = end_time - timedelta(hours=12)
            period_label = "12 ЧАСОВ (дневная сессия)"
        
        fig, axes = plt.subplots(3, 1, figsize=(10, 14), facecolor='#0d1117')
        fig.suptitle(f'🔥 ПОЖАРНЫЙ ШПИОН: РЫНОЧНЫЙ ДАШБОРД ({period_label})\n{start_time.strftime("%d.%m %H:%M")} - {end_time.strftime("%d.%m %H:%M")} МСК', 
                     fontsize=14, fontweight='bold', color='white', y=0.98)
        
        # ПАНЕЛЬ 1: BTC с уровнями
        ax1 = axes[0]
        try:
            btc = yf.Ticker("BTC-USD")
            btc_hist = btc.history(start=start_time, end=end_time, interval="15m")
            
            if not btc_hist.empty:
                ax1.plot(btc_hist.index, btc_hist['Close'], color='#F7931A', linewidth=2, label='BTC Price')
                btc_7d = btc.history(period="7d")
                support = btc_7d['Low'].min()
                resistance = btc_7d['High'].max()
                ax1.axhline(support, color='#00ff00', linestyle='--', alpha=0.7, label=f'Поддержка ${support:,.0f}')
                ax1.axhline(resistance, color='#ff0000', linestyle='--', alpha=0.7, label=f'Сопротивление ${resistance:,.0f}')
                ax1.set_title('1. BTC/USD: Ключевые уровни (15-мин)', color='white', fontsize=12, loc='left')
                ax1.legend(loc='upper left', fontsize=9)
                ax1.grid(True, alpha=0.2)
                ax1.tick_params(colors='white')
                ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m\n%H:%M'))
                ax1.xaxis.set_major_locator(mdates.HourLocator(interval=3))
            else:
                ax1.text(0.5, 0.5, 'Нет данных BTC', ha='center', va='center', color='white', fontsize=14)
                ax1.set_title('1. BTC/USD: Ключевые уровни', color='white', fontsize=12, loc='left')
        except Exception as e:
            ax1.text(0.5, 0.5, f'Ошибка: {str(e)[:50]}', ha='center', va='center', color='white', fontsize=12)
            ax1.set_title('1. BTC/USD: Ключевые уровни', color='white', fontsize=12, loc='left')

        # ПАНЕЛЬ 2: Крипто-гонка
        ax2 = axes[1]
        try:
            cryptos = {"BTC-USD": "BTC", "ETH-USD": "ETH", "SOL-USD": "SOL"}
            for ticker, label in cryptos.items():
                asset = yf.Ticker(ticker)
                df = asset.history(start=start_time, end=end_time, interval="15m")
                if not df.empty:
                    normalized = (df['Close'] / df['Close'].iloc[0]) * 100
                    ax2.plot(normalized.index, normalized, label=label, linewidth=2)
            
            ax2.set_title('2. Крипто-гонка: Относительная сила (старт = 100%)', color='white', fontsize=12, loc='left')
            ax2.legend(loc='upper left', fontsize=9)
            ax2.grid(True, alpha=0.2)
            ax2.tick_params(colors='white')
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m\n%H:%M'))
            ax2.xaxis.set_major_locator(mdates.HourLocator(interval=3))
        except Exception as e:
            ax2.text(0.5, 0.5, f'Ошибка: {str(e)[:50]}', ha='center', va='center', color='white', fontsize=12)
            ax2.set_title('2. Крипто-гонка: Относительная сила', color='white', fontsize=12, loc='left')

        # ПАНЕЛЬ 3: Макро-фон
        ax3 = axes[2]
        try:
            macros = {"^GSPC": "S&P 500", "GC=F": "Золото", "DX-Y.NYB": "DXY"}
            for ticker, label in macros.items():
                asset = yf.Ticker(ticker)
                df = asset.history(start=start_time, end=end_time, interval="15m")
                if not df.empty:
                    normalized = (df['Close'] / df['Close'].iloc[0]) * 100
                    ax3.plot(normalized.index, normalized, label=label, linewidth=2)
            
            ax3.set_title('3. Макро-фон: Традиционные рынки (старт = 100%)', color='white', fontsize=12, loc='left')
            ax3.legend(loc='upper left', fontsize=9)
            ax3.grid(True, alpha=0.2)
            ax3.tick_params(colors='white')
            ax3.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m\n%H:%M'))
            ax3.xaxis.set_major_locator(mdates.HourLocator(interval=3))
        except Exception as e:
            ax3.text(0.5, 0.5, f'Ошибка: {str(e)[:50]}', ha='center', va='center', color='white', fontsize=12)
            ax3.set_title('3. Макро-фон: Традиционные рынки', color='white', fontsize=12, loc='left')

        for ax in axes:
            ax.set_facecolor('#161b22')
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, color='white')

        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='#0d1117')
        buf.seek(0)
        plt.close()
        print("✅ Дашборд сгенерирован")
        return buf
    except Exception as e:
        print(f"❌ Ошибка генерации графика: {e}")
        return None

# ==========================================
# 4. ИИ-АНАЛИЗ
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
    
    prompt = f"""Ты — «Пожарный Шпион», элитный автономный ИИ-аналитик. Создай ПРОФЕССИОНАЛЬНЫЙ обзор рынка.

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

СТРУКТУРА:

🔥 ПОЖАРНЫЙ ШПИОН: {session_info['name']} ОБЗОР — {session_info['date']}

📊 ПЕРИОД АНАЛИЗА: {session_info['period']}

⚠️ Сначала риски, потом возможности!

🌍 РЫНОЧНЫЙ СРЕЗ:
- {fg_emoji} Индекс страха/жадности: {fg_value}/100 ({fg_class})
- Расшифровка: 0-24=Extreme Fear, 25-49=Fear, 50=Neutral, 51-74=Greed, 75-100=Extreme Greed

 УРОВНИ BTC:
- Поддержка: [из данных]
- Сопротивление: [из данных]
- Текущая цена: [из данных]

🐋 ДЕЙСТВИЯ КИТОВ:
- Анализ движений капитала

📰 ГЛАВНЫЕ НОВОСТИ:
- 2-3 новости с временными метками

⚠️ РИСК-ПРЕДУПРЕЖДЕНИЕ:
"Торговля сопряжена с риском потери ВСЕГО депозита."

 ТОРГОВЫЕ ИДЕИ (3 совета):
1️⃣ [Действие]: [Пояснение]
2️⃣ [Действие]: [Пояснение]
3️⃣ [Действие]: [Пояснение]

 QUICK STATS:
- Используй цветовую кодировку: 🟢🟡🔵

⚖️ ДИСКЛЕЙМЕР:
"⚠️ Информация носит ознакомительный характер. Риск потери до 100% депозита. DYOR."

ПРАВИЛА:
- Жирный шрифт для цифр и активов
- Сленг с расшифровками
- Объем: до 4000 символов
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
# 5. ФУТЕР ПОСТА
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

 ПОЖАРНЫЙ ШПИОН — система экстренных оповещений
Система автоматически мониторит рынки и геополитику. При резких изменениях в канал придёт экстренный сигнал.

👍 Если обзор был полезен — ставь реакцию!
 Подписывайся на канал, чтобы не пропустить важные сигналы."""
    
    return footer

# ==========================================
# 6. ОТПРАВКА В TELEGRAM
# ==========================================
def send_to_telegram(text, chart_buffer=None):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    channel_id = os.environ.get("TELEGRAM_CHANNEL_ID")
    
    # Отправляем дашборд
    if chart_buffer:
        print("📊 Отправка дашборда...")
        try:
            files = {
                'photo': ('dashboard.png', chart_buffer, 'image/png'),
                'chat_id': (None, channel_id),
                'caption': (None, "🔥 ПОЖАРНЫЙ ШПИОН: РЫНОЧНЫЙ ДАШБОРД (12 ЧАСОВ)\n\nГрафики подтверждают анализ ниже "),
                'parse_mode': (None, 'Markdown')
            }
            response = requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendPhoto",
                files=files,
                timeout=30
            )
            if response.status_code == 200:
                print("✅ Дашборд отправлен!")
            else:
                print(f"⚠️ Ошибка отправки дашборда: {response.text}")
        except Exception as e:
            print(f"⚠️ Ошибка при отправке дашборда: {e}")
        time.sleep(2)
    
    # Отправляем текст (умная нарезка)
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
            part_with_indicator = part_with_indicator[:4080] + "\n\n_...текст обрезан_"
        
        text_payload = {
            "chat_id": channel_id,
            "text": part_with_indicator,
            "parse_mode": "Markdown"
        }
        response = requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json=text_payload, timeout=15)
        
        if response.status_code == 200:
            print(f"✅ Часть {i+1}/{total_parts} отправлена! (длина: {len(part_with_indicator)})")
        else:
            print(f"❌ Ошибка части {i+1}: {response.text}")

# ==========================================
# 7. ГЛАВНЫЙ ЗАПУСК
# ==========================================
def main():
    print(" Запуск Пожарного Шпиона v24.0 с дашбордом...")
    
    print("📡 Определение типа выпуска...")
    session_info = get_session_info()
    print(f"   Тип: {session_info['name']} выпуск")
    print(f"   Период: {session_info['period']}")
    
    print(" Сбор данных...")
    fear_greed = get_fear_greed_index()
    global_data = get_global_data()
    crypto = get_crypto_data()
    support_resistance = get_support_resistance()
    finance = get_finance_data()
    news = get_news_data()
    
    print(" Генерация дашборда за 12 часов...")
    chart_buffer = generate_composite_chart(session_info)
    
    print("🧠 ИИ-анализ (30-60 секунд)...")
    try:
        analysis = get_ai_analysis(session_info, fear_greed, global_data, crypto, support_resistance, finance, news)
    except Exception as e:
        print(f" Ошибка ИИ-анализа: {e}")
        analysis = "Ошибка генерации анализа."
    
    print("📎 Добавление футера...")
    footer = get_post_footer(session_info)
    full_text = analysis + "\n\n" + footer
    
    print(f"📏 Длина текста: {len(full_text)} символов")
    
    print("📤 Публикация...")
    send_to_telegram(full_text, chart_buffer)
    print("✅ Миссия выполнена.")

if __name__ == "__main__":
    main()
