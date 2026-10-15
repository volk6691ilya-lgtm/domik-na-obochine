import pandas as pd
import mplfinance as mpf
import numpy as np
import logging
import os
import warnings

warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib.font_manager')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_anti_bot_price(price: float, symbol: str) -> float:
    """
    Гарантирует, что 4-й знак после запятой НИКОГДА не будет равен 0.
    Добавляет детерминированный микро-сдвиг (0.0001 - 0.0009) на основе названия монеты,
    чтобы уровни не выглядели как "круглые" числа для ботов-хантеров.
    """
    base_price = round(float(price), 4)
    # Проверяем последнюю цифру (4-й знак после запятой)
    last_digit = int(round(base_price * 10000)) % 10
    
    if last_digit == 0:
        # Генерируем сдвиг от 1 до 9 на основе суммы ASCII-кодов символов тикера
        jitter = 0.0001 * ((sum(ord(c) for c in symbol) % 9) + 1)
        base_price = round(base_price + jitter, 4)
        
        # Двойная проверка на случай математического переноса (крайне редко)
        if int(round(base_price * 10000)) % 10 == 0:
            base_price = round(base_price + 0.0001, 4)
            
    return base_price

class ChartVisualizer:
    """
    Модуль для генерации профессиональных графиков с разметкой уровней.
    Использует библиотеку mplfinance (бесплатно, без API ключей).
    """

    def __init__(self, output_dir="charts"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def generate_signal_chart(self, df, symbol, ta_data, filename="signal_chart.png"):
        try:
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)

            # Поддержка и новых ключей (sl, tp, entry), и старых для совместимости
            sl_level = ta_data.get("sl") or ta_data.get("support_level (SL)")
            tp_level = ta_data.get("tp") or ta_data.get("resistance_level (TP)")
            entry_level = ta_data.get("entry", ta_data.get("price", "N/A"))

            # ✅ ИСПОЛЬЗУЕМ УРОВНИ ФИБОНАЧЧИ ИЗ TA_DATA (ШАГ 4)
            fib_levels = ta_data.get('fib_levels', {})
            
            # Определяем направление
            is_long = "Бычий" in ta_data.get('trend', '')
            
            # Рассчитываем TP1, TP2, TP3 на основе Фибоначчи
            tp1 = None
            tp2 = None
            tp3 = None
            
            if entry_level != "N/A" and fib_levels:
                entry_float = float(entry_level)
                
                if is_long:
                    tp1 = fib_levels.get('0.618', round(entry_float + (float(tp_level) - entry_float) * 0.4, 4))
                    tp2 = fib_levels.get('1.0', round(entry_float + (float(tp_level) - entry_float) * 0.7, 4))
                    tp3 = fib_levels.get('1.618', float(tp_level))
                else:
                    tp1 = fib_levels.get('0.618', round(entry_float - (entry_float - float(tp_level)) * 0.4, 4))
                    tp2 = fib_levels.get('0.382', round(entry_float - (entry_float - float(tp_level)) * 0.7, 4))
                    tp3 = fib_levels.get('0.0', float(tp_level))
            elif entry_level != "N/A" and tp_level:
                # Фоллбэк на старую логику, если Фибоначчи нет
                entry_float = float(entry_level)
                tp_float = float(tp_level)
                
                if is_long:
                    tp1 = round(entry_float + (tp_float - entry_float) * 0.4, 4)
                    tp2 = round(entry_float + (tp_float - entry_float) * 0.7, 4)
                    tp3 = tp_float
                else:
                    tp1 = round(entry_float - (entry_float - tp_float) * 0.4, 4)
                    tp2 = round(entry_float - (entry_float - tp_float) * 0.7, 4)
                    tp3 = tp_float

            # 🛡️ ПРИМЕНЯЕМ ЗАЩИТУ ОТ КРУГЛЫХ ЧИСЕЛ (Anti-Bot Price)
            entry_fmt = get_anti_bot_price(float(entry_level), symbol) if entry_level != "N/A" else 0.0
            sl_fmt = get_anti_bot_price(float(sl_level), symbol) if sl_level else 0.0
            tp1_fmt = get_anti_bot_price(float(tp1), symbol) if tp1 is not None else 0.0
            tp2_fmt = get_anti_bot_price(float(tp2), symbol) if tp2 is not None else 0.0
            tp3_fmt = get_anti_bot_price(float(tp3), symbol) if tp3 is not None else 0.0

            hlines = []
            hlines_colors = []
            hlines_styles = []

            # 1. Стоп-лосс (Зеленый) — пунктир
            if sl_level:
                hlines.append(sl_fmt)
                hlines_colors.append('lime')
                hlines_styles.append('--')

            # 2. Точка входа (Синий) — сплошная
            if entry_level and entry_level != "N/A":
                hlines.append(entry_fmt)
                hlines_colors.append('dodgerblue')
                hlines_styles.append('-')

            # 3. TP1 (Оранжевый) — точки
            if tp1 is not None:
                hlines.append(tp1_fmt)
                hlines_colors.append('orange')
                hlines_styles.append(':')

            # 4. TP2 (Оранжево-красный) — точки
            if tp2 is not None:
                hlines.append(tp2_fmt)
                hlines_colors.append('orangered')
                hlines_styles.append(':')

            # 5. TP3 (Красный) — пунктир
            if tp3 is not None:
                hlines.append(tp3_fmt)
                hlines_colors.append('red')
                hlines_styles.append('--')

            # 6. BOLLINGER BANDS (Шаг 5: Визуализация)
            if 'boll_upper' in ta_data and 'boll_middle' in ta_data and 'boll_lower' in ta_data:
                hlines.append(float(ta_data['boll_upper']))
                hlines_colors.append('gray')
                hlines_styles.append('-.')
                hlines.append(float(ta_data['boll_middle']))
                hlines_colors.append('gray')
                hlines_styles.append('--')
                hlines.append(float(ta_data['boll_lower']))
                hlines_colors.append('gray')
                hlines_styles.append('-.')

            # Настройки стиля графика (похож на TradingView)
            mc = mpf.make_marketcolors(up='g', down='r', edge='i', wick='i', volume='in', inherit=True)
            s = mpf.make_mpf_style(marketcolors=mc, base_mpf_style='charles')

            # Обновленный заголовок с форматированием .4f (всегда 4 знака после запятой)
            title = f"{symbol} | Entry: ${entry_fmt:.4f} | SL: ${sl_fmt:.4f} | TP1: ${tp1_fmt:.4f} | TP2: ${tp2_fmt:.4f} | TP3: ${tp3_fmt:.4f}"
            filepath = os.path.join(self.output_dir, filename)

            # ГЕНЕРАЦИЯ ГРАФИКА
            mpf.plot(
                df,
                type='candle',
                style=s,
                title=title,
                ylabel='Price (USDT)',
                volume=True,
                ylabel_lower='Volume',
                hlines=dict(hlines=hlines, colors=hlines_colors, linestyle=hlines_styles),
                savefig=filepath,
                figratio=(10, 6),
                figscale=1.2
            )

            logging.info(f"График успешно сохранен: {filepath}")
            return filepath

        except Exception as e:
            logging.error(f"Ошибка при генерации графика: {e}")
            return None

# Блок для локального тестирования
if __name__ == "__main__":
    print("\n--- Тест Chart Visualizer (с Anti-Bot Price и Bollinger Bands) ---")

    np.random.seed(42)
    dates = pd.date_range(end='2026-10-14', periods=50, freq='1h')
    closes = np.cumsum(np.random.randn(50)) + 100
    opens = closes + np.random.randn(50) * 0.5
    highs = np.maximum(opens, closes) + np.random.rand(50) * 1.0
    lows = np.minimum(opens, closes) - np.random.rand(50) * 1.0
    volumes = np.random.randint(1000, 5000, 50)

    df = pd.DataFrame({
        'open': opens, 'high': highs, 'low': lows, 'close': closes, 'volume': volumes
    }, index=dates)

    # Тестовые данные с "круглыми" числами, чтобы проверить работу функции
    mock_ta_data = {
        "price": 98.0000,
        "entry": 98.0000,
        "sl": 95.0000,
        "tp": 105.0000,
        "trend": "Бычий 🟢 (Цена > EMA50)",
        "estimated_R:R": "1 : 2.5",
        "fib_levels": {
            '0.0': 95.0000,
            '0.618': 102.3700,
            '1.0': 105.0000,
            '1.618': 109.5800
        },
        "boll_upper": 103.5000,
        "boll_middle": 98.5000,
        "boll_lower": 93.5000
    }

    visualizer = ChartVisualizer()
    filepath = visualizer.generate_signal_chart(df, "TESTUSDT", mock_ta_data, "test_chart.png")

    if filepath:
        print(f"\n✅ УСПЕХ! График сохранен по пути: {os.path.abspath(filepath)}")
        print("👉 Проверь заголовок графика: числа больше не заканчиваются на .0000!")
        print("💡 Защита от ботов-хантеров активна.")
    else:
        print("\n❌ Ошибка при создании графика.")

    print("\n--- Тест завершен ---\n")
