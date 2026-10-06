# ai_models_config.py
# ЕДИНЫЙ ЦЕНТР УПРАВЛЕНИЯ ИИ-МОДЕЛЯМИ ДЛЯ ВСЕЙ СИСТЕМЫ
# Обновлено на основе живого теста API OpenRouter (11 рабочих моделей, включая 3 новые)

# 🎯 3 ОСНОВНЫЕ МОДЕЛИ (распределены строго по задачам)
PRIMARY_MODELS = {
    # 🧠 Лучшая для глубокого анализа и длинных текстов (Утренние/Вечерние обзоры)
    "main_analyst": "nvidia/nemotron-3-super-120b-a12b:free",
    
    # ⚡ Самая быстрая и стабильная (Для Умного Пожарного Бота, чтобы реагировать мгновенно)
    "smart_fire_spy": "nvidia/nemotron-3.5-lightning:free",
    
    # 📊 Отлично структурирует финансовые данные и параметры сделок (Для торговых сигналов)
    "signal_generator": "inclusionai/ling-3.0-flash-sante:free"
}

# 🛡️ РЕЗЕРВНЫЕ МОДЕЛИ (отсортированы по приоритету: от самых мощных/быстрых к вспомогательным)
BACKUP_MODELS = [
    # --- НОВЫЕ РАБОЧИЕ МОДЕЛИ (добавлены по результатам теста) ---
    "nvidia/nemotron-3-ultra-550b-a55b:free",  # 🚀 НОВИНКА! Самая мощная (550B), тяжелая артиллерия
    "poolside/laguna-s-2.1:free",               # 🚀 НОВИНКА! Отличная универсальная страховка
    "poolside/laguna-xs-2.1:free",              # 🚀 НОВИНКА! Сверхбыстрая (XS), страховка для fire_spy
    
    # --- ПРОВЕРЕННЫЕ СТАРЫЕ РЕЗЕРВЫ ---
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free", # Хороша для логики и рассуждений
    "cohere/north-mini-code:free",                        # Отлична для структурированных данных
    "dots-studio/dots-3-note-preview:free",
    "liquid/lfm-2.5-2.6b:free",
    "nvidia/nemotron-3.5-content-safety:free"
]

# 📋 ПОЛНЫЙ СПИСОК ВСЕХ МОДЕЛЕЙ (для циклического перебора: сначала основная задача, потом резерв)
ALL_MODELS = list(PRIMARY_MODELS.values()) + BACKUP_MODELS

# Функция для получения моделей по задаче
def get_models_for_task(task: str) -> list:
    """
    Возвращает список моделей для конкретной задачи.
    Сначала идет идеальная модель для задачи, затем весь список резервных.
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
