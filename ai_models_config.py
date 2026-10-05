# ai_models_config.py
# ЕДИНЫЙ ЦЕНТР УПРАВЛЕНИЯ ИИ-МОДЕЛЯМИ ДЛЯ ВСЕЙ СИСТЕМЫ
# Обновлено на основе тестов от 05.10.2026 (8 рабочих моделей)

# 🎯 3 ОСНОВНЫЕ МОДЕЛИ (берут на себя лучшие задачи из проверенных)
PRIMARY_MODELS = {
    # 🧠 Лучшая для глубокого анализа и длинных текстов (Утренние/Вечерние обзоры)
    "main_analyst": "nvidia/nemotron-3-super-120b-a12b:free",
    
    # ⚡ Самая быстрая и стабильная (Для Умного Пожарного Бота, чтобы реагировать мгновенно)
    "smart_fire_spy": "nvidia/nemotron-3.5-lightning:free",
    
    # 📊 Отлично структурирует финансовые данные (Для торговых сигналов)
    "signal_generator": "inclusionai/ling-3.0-flash-sante:free"
}

# 🛡️ РЕЗЕРВНЫЕ МОДЕЛИ (страхуют основные, если те вдруг упадут или получат Rate Limit)
BACKUP_MODELS = [
    "cohere/north-mini-code:free",
    "dots-studio/dots-3-note-preview:free",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
    "liquid/lfm-2.5-2.6b:free",
    "nvidia/nemotron-3.5-content-safety:free",
    # Можно раскомментировать Gemma, если захочешь рискнуть, но лучше полагаться на стабильные:
    # "google/gemma-4-31b-it:free",
    # "google/gemma-4-26b-a4b-it:free"
]

# 📋 ПОЛНЫЙ СПИСОК ВСЕХ МОДЕЛЕЙ (для циклического перебора: сначала основные, потом резерв)
ALL_MODELS = list(PRIMARY_MODELS.values()) + BACKUP_MODELS

# Функция для получения моделей по задаче
def get_models_for_task(task: str) -> list:
    """
    Возвращает список моделей для конкретной задачи.
    task: 'main', 'signal', 'smart_fire_spy'
    """
    if task == 'main':
        return [PRIMARY_MODELS['main_analyst']] + BACKUP_MODELS
    elif task == 'signal':
        return [PRIMARY_MODELS['signal_generator']] + BACKUP_MODELS
    elif task == 'smart_fire_spy':
        return [PRIMARY_MODELS['smart_fire_spy']] + BACKUP_MODELS
    else:
        return ALL_MODELS
