import json
import logging
from multi_exchange_aggregator import ExchangeAggregator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Списки монет из PDF "Портфели"
PORTFOLIOS = {
    "🏛️ Фундаментальные (Core)": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT", "DOTUSDT"],
    "🌐 Перспективные экосистемы": ["LINKUSDT", "PENDLEUSDT", "RENDERUSDT", "ONDOUSDT", "ARBUSDT", "AVAXUSDT"],
    "🏢 Институциональные фавориты": ["XRPUSDT", "ATOMUSDT", "FILUSDT", "INJUSDT", "NEARUSDT", "TONUSDT"],
    "💸 DeFi сектор": ["AAVEUSDT", "UNIUSDT", "COMPUSDT", "MKRUSDT", "JUPUSDT"],
    "🤖 Искусственный интеллект (AI)": ["ICPUSDT", "FETUSDT", "GRTUSDT", "THETAUSDT"]
    # RENDER, FIL, INJ, NEAR уже учтены выше, чтобы не дублировать запросы
}

class PortfolioTracker:
    """
    Модуль для анализа инвестиционных портфелей по секторам.
    Оценивает, какой сектор показывает наибольший рост объемов и цены.
    """

    def __init__(self):
        self.aggregator = ExchangeAggregator()

    def analyze_sectors(self):
        """Анализирует каждый сектор и возвращает сводку"""
        sector_summary = {}

        for sector_name, coins in PORTFOLIOS.items():
            sector_growth_count = 0
            sector_volume_score = 0
            
            for coin in coins:
                # Используем наш агрегатор для получения данных (приоритет Bybit для альтов)
                data = self.aggregator.get_unified_data(coin)
                
                if data:
                    # Для упрощения локального теста используем объем как показатель интереса
                    # В реальной системе здесь можно добавить запрос исторических данных для сравнения
                    volume_millions = data.get('bybit_volume', 0) / 1_000_000
                    
                    # Эвристика: если объем > 10M, сектор активен
                    if volume_millions > 10:
                        sector_growth_count += 1
                        sector_volume_score += volume_millions

            # Оценка активности сектора
            activity_percentage = (sector_growth_count / len(coins)) * 100
            
            if activity_percentage >= 70:
                status = "🔥 ГОРЯЧИЙ (Высокий интерес)"
            elif activity_percentage >= 40:
                status = "🟡 УМЕРЕННЫЙ (Накопление)"
            else:
                status = "❄️ ХОЛОДНЫЙ (Низкая активность)"

            sector_summary[sector_name] = {
                "status": status,
                "active_coins": f"{sector_growth_count}/{len(coins)}",
                "total_volume_score": round(sector_volume_score, 2)
            }

        return sector_summary

    def generate_weekly_digest(self):
        """Генерирует готовый текст для поста в канал"""
        summary = self.analyze_sectors()
        
        digest = "💼 **ИНВЕСТИЦИОННЫЙ ДАЙДЖЕСТ: ОБЗОР СЕКТОРОВ**\n\n"
        digest += "Анализ активности и притока ликвидности по ключевым направлениям:\n\n"
        
        # Сортируем сектора по "горячести" (просто для красивого вывода)
        for sector, data in summary.items():
            digest += f"▫️ **{sector}**\n"
            digest += f"   Статус: {data['status']}\n"
            digest += f"   Активных монет: {data['active_coins']}\n\n"
            
        digest += "💡 **Вывод:** Фокусируйтесь на секторах со статусом 🔥 или 🟡. "
        digest += "Не забывайте про правило 5% от депозита на одну позицию и обязательный Stop-Loss!\n"
        digest += "⚠️ *Это аналитический обзор, а не индивидуальная инвестиционная рекомендация (DYOR).*"
        
        return digest

# Блок для локального тестирования
if __name__ == "__main__":
    print("\n--- Тест Portfolio Tracker (Анализ секторов) ---")
    tracker = PortfolioTracker()
    
    print("Сбор данных с бирж (это может занять 10-15 секунд)...")
    digest = tracker.generate_weekly_digest()
    
    print("\n" + "="*50)
    print(digest)
    print("="*50 + "\n")
    print("--- Тест завершен ---\n")
