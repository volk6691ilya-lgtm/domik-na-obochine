import os
import requests
import json
import time
import random
import yfinance as yf
import feedparser
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta, timezone
from io import BytesIO

# Настройка стиля графиков (темная тема)
plt.style.use('dark_background')

# ==========================================
# 1. ОПРЕДЕЛЕНИЕ ТИПА ВЫПУСКА
# ==========================================
def get_session_info():
    msk_tz = timezone(timedelta(hours=3))
    now_msk = datetime.now(msk_tz)
    current_hour = now_msk.hour
    
    if current_hour < 15:
        session_type = "morning"
        session_name = "УТРЕННИЙ"
        period_start = now_msk.replace(hour=21, minute=0, second=0) - timedelta(days=1)
        period_end = now_msk.replace(hour=9, minute=0, second=0)
        period_text = f"с 21:00 {period_start.strftime('%d.%m')} по 09:00 {now_msk.strftime('%d.%m.%Y')} (ночная сессия)"
    else:
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
# 2. СБОР ДАННЫХ
# ==========================================
def get_fear_greed_index():
    try:
        url = "https://api.alternative.me/fng/?limit=1"
        response = requests.get(url, timeout=10).json()
        return int(response['data'][0]['value']), response['data'][0]['value_classification']
    except:
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
    except:
        return {'btc_dominance': 0, 'total_market_cap': 0, 'total_volume': 0}

def get_crypto_data():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana,ripple,toncoin&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true"
        response = requests.get(url, timeout=10).json()
        data = []
        names = {"bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL", "ripple": "XRP", "toncoin": "TON"}
        for key, name in names.items():
            if key in response:
                price = response[key]['usd']
                change = response[key]['usd_24h_change']
                vol = response[key].get('usd_24h_vol', 0) / 1_000_000_000
                data.append(f"• {name}: ${price:,.2f} ({change:+.2f}%) | Объем: ${vol:.2f}B")
        return "\n".join(data)
    except Exception as e:
        return f"• Крипта: Ошибка ({str(e)[:30]})"

def get_support_resistance():
    try:
        btc = yf.Ticker("BTC-USD")
        hist = btc.history(period="7d")
        if not hist.empty:
            return f"BTC: Поддержка ${hist['Low'].min():,.0f} | Сопротивление ${hist['High'].max():,.0f} | Текущая ${hist['Close'].iloc[-1]:,.0f}"
        return "BTC: Недоступно"
    except Exception as e:
        return f"BTC: Ошибка ({str(e)[:30]})"

def get_finance_data():
    try:
        tickers = {"GC=F": "Золото", "SI=F": "Серебро", "BZ=F": "Нефть Brent", "^GSPC": "S&P 500", "NVDA": "NVIDIA", "DX-Y.NYB": "DXY"}
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
        hours = (now - pub_dt).total_seconds() / 3600
        return hours
    except:
        return None

def format_time_ago(hours):
    if hours is None: return ""
    if hours < 1: return "только что"
    if hours < 24: return f"{int(hours)} ч. назад"
    return f"{int(hours // 24)} дн. назад"

def get_news_data():
    try:
        feeds = ["http://feeds.reuters.com/reuters/businessNews", "https://cointelegraph.com/rss"]
        headlines = []
        for feed_url in feeds:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                hours_ago = get_hours_ago(entry.get('published_parsed'))
                if hours_ago is None or hours_ago > 12:
                    continue
                title = entry.title.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('`', '\\`')
                link = entry.get('link', '')
                time_label = format_time_ago(hours_ago)
                time_prefix = f"[{time_label}] " if time_label else ""
                if link:
                    headlines.append(f"• {time_prefix}{title} — [источник]({link})")
                else:
                    headlines.append(f"• {time_prefix}{title}")
                if len(headlines) >= 5: break
            if len(headlines) >= 5: break
        return "\n".join(headlines) if headlines else "• Новостей за 12 часов нет — фон спокойный"
    except Exception as e:
        return f"• Новости: Ошибка ({str(e)[:30]})"

# ==========================================
# 3. ГЕНЕРАЦИЯ МУЛЬТИ-ГРАФИКА (3 ПАНЕЛИ)
# ==========================================
def generate_composite_chart():
    """Генерирует профессиональный 3-панельный график"""
    try:
        fig, axes = plt.subplots(3, 1, figsize=(10, 14), facecolor='#0d1117')
        fig.suptitle('🔥 ПОЖАРНЫЙ ШПИОН: РЫНОЧНЫЙ ДАШБОРД (7 ДНЕЙ)', fontsize=16, fontweight='bold', color='white', y=0.98)
        
        # --- ПАНЕЛЬ 1: BTC с уровнями ---
        ax1 = axes[0]
        btc = yf.Ticker("BTC-USD").history(period="7d")
        if not btc.empty:
            ax1.plot(btc.index, btc['Close'], color='#F7931A', linewidth=2, label='BTC Price')
            support, resistance = btc['Low'].min(), btc['High'].max()
            ax1.axhline(support, color='#00ff00', linestyle='--', alpha=0.7, label=f'Поддержка ${support:,.0f}')
            ax1.axhline(resistance, color='#ff0000', linestyle='--', alpha=0.7, label=f'Сопротивление ${resistance:,.0f}')
            ax1.set_title('1. BTC/USD: Ключевые уровни', color='white', fontsize=12, loc='left')
            ax1.legend(loc='upper left', fontsize=9)
            ax1.grid(True, alpha=0.2)
            ax1.tick_params(colors='white')

        # --- ПАНЕЛЬ 2: Крипто-гонка (Нормализованная) ---
        ax2 = axes[1]
        cryptos = {"BTC-USD": "BTC", "ETH-USD": "ETH", "SOL-USD": "SOL"}
        for ticker, label in cryptos.items():
            df = yf.Ticker(ticker).history(period="7d")
            if not df.empty:
                normalized = (df['Close'] / df['Close'].iloc[0]) * 100
                ax2.plot(normalized.index, normalized, label=label, linewidth=2)
        ax2.set_title('2. Крипто-гонка: Относительная сила (старт = 100%)', color='white', fontsize=12, loc='left')
        ax2.legend(loc='upper left', fontsize=9)
        ax2.grid(True, alpha=0.2)
        ax2.tick_params(colors='white')

        # --- ПАНЕЛЬ 3: Макро-фон ---
        ax3 = axes[2]
        macros = {"^GSPC": "S&P 500", "GC=F": "Золото", "DX-Y.NYB": "DXY"}
        for ticker, label in macros.items():
            df = yf.Ticker(ticker).history(period="7d")
            if not df.empty:
                normalized = (df['Close'] / df['Close'].iloc[0]) * 100
                ax3.plot(normalized.index, normalized, label=label, linewidth=2)
        ax3.set_title('3. Макро-фон: Традиционные рынки (старт = 100%)', color='white', fontsize=12, loc='left')
        ax3.legend(loc='upper left', fontsize=9)
        ax3.grid(True, alpha=0.2)
        ax3.tick_params(colors='white')

        # Форматирование осей X для всех
        for ax in axes:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
            ax.xaxis.set_major_locator(mdates.DayLocator())
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, color='white')
            ax.set_facecolor('#161b22')

        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='#0d1117')
        buf.seek(0)
        plt.close()
        return buf
    except Exception as e:
        print(f" Ошибка генерации графика: {e}")
        return None

# ==========================================
# 4. ИИ-АНАЛИЗ
# ==========================================
def get_ai_analysis(session_info, fear_greed, global_data, crypto, support_resistance, finance, news):
    api_key = os.environ.get("OPENROUTER_API_KEY")
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    models = ["minimax/minimax-m3:free", "nvidia/nemotron-3.5-lightning:free", "inclusionai/ling-3.0-flash-fin:free"]
    fg_value, fg_class = fear_greed
    btc_dom = global_data['btc_dominance']
    total_mcap = global_data['total_market_cap']
    
    fg_emoji = "🟢" if 51 <= fg_value <= 74 else ("🔴" if fg_value > 74 else "🟡")
    fg_signal = "ЖАДНОСТЬ — осторожно с FOMO" if 51 <= fg_value <= 74 else ("ЭКСТРЕМАЛЬНАЯ ЖАДНОСТЬ" if fg_value > 74 else "НЕЙТРАЛЬНО/СТРАХ")
    
    prompt = f"""Ты — «Пожарный Шпион». Создай ПРОФЕССИОНАЛЬНЫЙ обзор рынка.
КОНТЕКСТ: {session_info['name']} выпуск, {session_info['date']}, Период: {session_info['period']}
ДАННЫЕ:
[ИНДЕКС]: {fg_value}/100 ({fg_class}) → {fg_emoji} {fg_signal}
[ДОМИНАЦИЯ BTC]: {btc_dom:.1f}% | [КАПИТАЛИЗАЦИЯ]: ${total_mcap:.0f}B
[КРИПТА]: {crypto}
[УРОВНИ BTC]: {support_resistance}
[ТРАДИЦИОННЫЕ РЫНКИ]: {finance}
[НОВОСТИ 12Ч]: {news}

СТРУКТУРА:
🔥 ПОЖАРНЫЙ ШПИОН: {session_info['name']} ОБЗОР — {session_info['date']}
📊 ПЕРИОД АНАЛИЗА: {session_info['period']}
⚠️ Сначала риски, потом возможности!
🌍 РЫНОЧНЫЙ СРЕЗ: (индекс, расшифровка 0-100, движения BTC/ETH)
🎯 УРОВНИ BTC: (поддержка, сопротивление, текущая, вывод)
🐋 ДЕЙСТВИЯ КИТОВ: (переток капитала, институционалы)
📰 ГЛАВНЫЕ НОВОСТИ: (2-3 новости с сохранением формата [время] текст — [источник](url), влияние на рынок)
⚠️ РИСК-ПРЕДУПРЕЖДЕНИЕ: "Торговля сопряжена с высоким риском потери средств. Вы можете потерять ВЕСЬ депозит."
🎯 ТОРГОВЫЕ ИДЕИ (3 совета): 1️⃣... 2️⃣... 3️⃣... (с конкретными % и уровнями)
⚡ QUICK STATS: (с эмодзи 🟢🔴🟡🔵, включи доминацию BTC и индекс страха)
⚖️ ДИСКЛЕЙМЕР: "⚠️ Информация ознакомительная, не является ИИР. Рынки сопряжены с риском потери до 100% депозита. DYOR."

ПРАВИЛА: Жирный шрифт для цифр/активов. Умеренные эмодзи. Сленг с расшифровкой в скобках. Тон: профессиональный, осторожный. БЕЗ "---" между блоками. Разбивай на абзацы (\n\n).
"""
    for model in models:
        try:
            response = requests.post(url, json={"model": model, "messages": [{"role": "user", "content": prompt}]}, 
                                     headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "HTTP-Referer": "https://github.com/volk6691ilya-lgtm/ember-watch", "X-Title": "Ember Watch System"}, timeout=60)
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
        except:
            continue
    return "Ошибка генерации анализа. Попробуйте позже."

# ==========================================
# 5. ОТПРАВКА В TELEGRAM
# ==========================================
def send_to_telegram(text):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    channel_id = os.environ.get("TELEGRAM_CHANNEL_ID")
    
    # 1. Генерируем и отправляем ПРОФЕССИОНАЛЬНЫЙ ГРАФИК вместо AI-картинки
    chart_buf = generate_composite_chart()
    if chart_buf:
        photo_payload = {"chat_id": channel_id, "photo": chart_buf, "caption": "🔥 ПОЖАРНЫЙ ШПИОН НА СВЯЗИ\n\nСистема завершила анализ 8 ветвей рынка. Полный разбор ниже 👇", "parse_mode": "Markdown"}
        requests.post(f"https://api.telegram.org/bot{bot_token}/sendPhoto", files={"photo": chart_buf}, data={"chat_id": channel_id, "caption": photo_payload["caption"], "parse_mode": photo_payload["parse_mode"]}, timeout=15)
        time.sleep(2)
    
    # 2. Умная нарезка текста
    max_len = 4000
    paragraphs = text.split('\n\n')
    parts, current_part = [], ""
    for para in paragraphs:
        if len(para) > max_len:
            if current_part: parts.append(current_part.strip()); current_part = ""
            for sentence in para.split('. '):
                if len(current_part) + len(sentence) + 2 <= max_len: current_part += sentence + ". "
                else:
                    if current_part: parts.append(current_part.strip())
                    current_part = sentence + ". "
            if current_part: parts.append(current_part.strip()); current_part = ""
        elif len(current_part) + len(para) + 2 <= max_len:
            current_part += para + "\n\n"
        else:
            if current_part: parts.append(current_part.strip())
            current_part = para + "\n\n"
    if current_part: parts.append(current_part.strip())
    
    # 3. Отправка частей
    for i, part in enumerate(parts):
        if i > 0: time.sleep(3)
        header = f"📄 **ЧАСТЬ {i+1}/{len(parts)}**\n\n" if len(parts) > 1 else ""
        footer = f"\n\n_...продолжение следует (часть {i+1}/{len(parts)})_" if len(parts) > 1 and i < len(parts) - 1 else ""
        part_text = header + part + footer
        
        if len(part_text) > 4090: part_text = part_text[:4080] + "\n\n_...текст обрезан_"
        
        response = requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", 
                                 json={"chat_id": channel_id, "text": part_text, "parse_mode": "Markdown", "disable_web_page_preview": True}, timeout=15)
        print(f"{'✅' if response.status_code == 200 else '❌'} Часть {i+1}/{len(parts)}")

# ==========================================
# 6. ГЛАВНЫЙ ЗАПУСК
# ==========================================
def main():
    print("🔥 Запуск Пожарного Шпиона v26.0 (Мульти-график)...")
    session_info = get_session_info()
    print(f"   {session_info['name']} выпуск, Период: {session_info['period']}")
    
    print("📡 Сбор данных...")
    fear_greed = get_fear_greed_index()
    global_data = get_global_data()
    crypto = get_crypto_data()
    support_resistance = get_support_resistance()
    finance = get_finance_data()
    news = get_news_data()
    
    print("🧠 ИИ-анализ...")
    analysis = get_ai_analysis(session_info, fear_greed, global_data, crypto, support_resistance, finance, news)
    
    msk_tz = timezone(timedelta(hours=3))
    now_msk = datetime.now(msk_tz)
    next_time = "21:00" if session_info['type'] == 'morning' else "09:00"
    next_date = now_msk.strftime("%d.%m.%Y") if session_info['type'] == 'morning' else (now_msk + timedelta(days=1)).strftime("%d.%m.%Y")
    next_type = "вечерний" if session_info['type'] == 'morning' else "утренний"
    
    footer = f"\n\n⏰ СЛЕДУЮЩИЙ ВЫПУСК: {next_type} обзор в {next_time} МСК ({next_date})\n\n🔔 ПОЖАРНЫЙ ШПИОН — система экстренных оповещений\nСистема автоматически мониторит рынки и геополитику. При резких изменениях в канал придёт экстренный сигнал.\n\n👍 Если обзор был полезен — ставь реакцию!\n📢 Подписывайся на канал, чтобы не пропустить важные сигналы."
    
    print("📤 Публикация...")
    send_to_telegram(analysis + footer)
    print("✅ Миссия выполнена.")

if __name__ == "__main__":
    main()
