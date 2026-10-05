# ai_models_config.py
# ЕДИНЫЙ ЦЕНТР УПРАВЛЕНИЯ ИИ-МОДЕЛЯМИ ДЛЯ ВСЕЙ СИСТЕМЫ
# Изменения здесь автоматически применяются ко всем скриптам

# 🎯 3 ОСНОВНЫЕ МОДЕЛИ (берут на себя лучшие задачи)
PRIMARY_MODELS = {
    "main_analyst": "inclusionai/ling-3.0-flash-fin:free",       # 🏆 Лучшая для финансового анализа (main.py)
    "signal_generator": "nvidia/nemotron-3-super-120b-a12b:free", # 🧠 Глубокие рассуждения (signal_generator.py)
    "smart_fire_spy": "nvidia/nemotron-3.5-lightning:free"        # ⚡ Самая быстрая (умный пожарный бот)
}

# ️ РЕЗЕРВНЫЕ МОДЕЛИ (страхуют основные, если те перегружены)
BACKUP_MODELS = [
    "google/gemma-4-31b-it:free",
    "google/gemma-4-26b-a4b-it:free",
    "cohere/north-mini-code:free",
    "inclusionai/ling-3.0-flash-sante:free",
    "dots-studio/dots-3-note-preview:free",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
    "liquid/lfm-2.5-2.6b:free",
    "nvidia/nemotron-3.5-content-safety:free"
]

#  ПОЛНЫЙ СПИСОК ВСЕХ МОДЕЛЕЙ (для тестирования)
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
