import pandas as pd
import mplfinance as mpf
import numpy as np
import logging
import os
import warnings
import ta  # Добавлен импорт для расчета кривых Боллинджера

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

            # ✅ ИСПОЛЬЗУЕМ УРОВНИ ФИБОНАЧЧИ ИЗ TA_DATA С ПРОВЕРКОЙ ЛОГИКИ
            fib_levels = ta_data.get('fib_levels', {})
            
            # Определяем направление
            is_long = "Бычий" in ta_data.get('trend', '')
            
            # Рассчитываем TP1, TP2, TP3 на основе Фибоначчи
            tp1 = None
            tp2 = None
            tp3 = None
            
            if entry_level != "N/A" and fib_levels:
                entry_float = float(entry_level)
                tp_float = float(tp_level) if tp_level else entry_float
                
                if is_long:
                    tp1 = fib_levels.get('0.618', round(entry_float + (tp_float - entry_float) * 0.4, 4))
                    tp2 = fib_levels.get('1.0', round(entry_float + (tp_float - entry_float) * 0.7, 4))
                    tp3 = fib_levels.get('1.618', tp_float)
                    
                    # 🔧 ПРОВЕРКА: для лонга TP должны быть СТРОГО ВЫШЕ входа
                    if tp1 <= entry_float: tp1 = round(entry_float + (tp_float - entry_float) * 0.4, 4)
                    if tp2 <= entry_float: tp2 = round(entry_float + (tp_float - entry_float) * 0.7, 4)
                    if tp3 <= entry_float: tp3 = tp_float
                else:
                    # Для шорта берем более низкие уровни Фибоначчи
                    tp1 = fib_levels.get('0.382', round(entry_float - (entry_float - tp_float) * 0.4, 4))
                    tp2 = fib_levels.get('0.0', round(entry_float - (entry_float - tp_float) * 0.7, 4))
                    tp3 = fib_levels.get('-0.618', round(entry_float - (entry_float - tp_float) * 1.5, 4))
                    
                    # Если уровня -0.618 нет, используем фоллбэк
                    if tp3 == tp_float and '-0.618' not in fib_levels:
                        tp3 = round(entry_float - (entry_float - tp_float) * 1.5, 4)
                    
                    # 🔧 ПРОВЕРКА: для шорта TP должны быть СТРОГО НИЖЕ входа
                    if tp1 >= entry_float: tp1 = round(entry_float - (entry_float - tp_float) * 0.4, 4)
                    if tp2 >= entry_float: tp2 = round(entry_float - (entry_float - tp_float) * 0.7, 4)
                    if tp3 >= entry_float: tp3 = round(entry_float - (entry_float - tp_float) * 1.5, 4)
                    
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
                    tp3 = round(entry_float - (entry_float - tp_float) * 1.5, 4)

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

            # 🎨 6. BOLLINGER BANDS: Рисуем как ПЛАВАЮЩИЕ КРИВЫЕ, а не прямые линии!
            add_plots = []
            try:
                # Рассчитываем полосы для ВСЕХ свечей в DataFrame
                bollinger = ta.volatility.BollingerBands(close=df['close'], window=20, window_dev=2)
                bb_upper = bollinger.bollinger_hband()
                bb_middle = bollinger.bollinger_mavg()
                bb_lower = bollinger.bollinger_lband()
                
                # Создаем addplot для кривых линий. 
                # Цвет 'gray', тонкая линия (width=0.8) и прозрачность (alpha=0.7) делают их 
                # отлично заметными как фон, но они не перебивают яркие линии Entry/SL/TP.
                ap_upper = mpf.make_addplot(bb_upper, color='gray', linestyle='-.', width=0.8, alpha=0.7)
                ap_middle = mpf.make_addplot(bb_middle, color='gray', linestyle='--', width=0.8, alpha=0.7)
                ap_lower = mpf.make_addplot(bb_lower, color='gray', linestyle='-.', width=0.8, alpha=0.7)
                
                add_plots = [ap_upper, ap_middle, ap_lower]
            except Exception as e:
                logging.warning(f"⚠️ Не удалось построить кривые Bollinger Bands: {e}")

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
                addplot=add_plots if add_plots else None,  # <-- Добавляем кривые Боллинджера сюда
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
    print("\n--- Тест Chart Visualizer (с кривыми Bollinger Bands) ---")

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

    # Тестовые данные
    mock_ta_data = {
        "price": 98.0000,
        "entry": 98.0000,
        "sl": 95.0000,
        "tp": 105.0000,
        "trend": "Бычий 🟢 (Цена > EMA50)",
        "estimated_R:R": "1 : 2.5",
        "fib_levels": {
            '0.0': 95.0000,
            '0.382': 99.6500,
            '0.618': 102.3700,
            '1.0': 105.0000,
            '1.618': 109.5800
        }
        # boll_upper и т.д. больше не нужны для hlines, они посчитаются автоматически из df
    }

    visualizer = ChartVisualizer()
    filepath = visualizer.generate_signal_chart(df, "TESTUSDT", mock_ta_data, "test_chart.png")

    if filepath:
        print(f"\n✅ УСПЕХ! График сохранен по пути: {os.path.abspath(filepath)}")
        print("👉 Открой картинку: теперь Bollinger Bands нарисованы как плавные кривые линии!")
        print("💡 Защита от ботов-хантеров и логических ошибок TP активна.")
    else:
        print("\n❌ Ошибка при создании графика.")

    print("\n--- Тест завершен ---\n")
