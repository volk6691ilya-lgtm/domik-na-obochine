import os
import requests
import time

def get_free_models_from_api():
    """Получает актуальный список бесплатных моделей напрямую от OpenRouter"""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ Ключ OPENROUTER_API_KEY не найден в Secrets!")
        return []
    
    url = "https://openrouter.ai/api/v1/models"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    try:
        print("📡 Запрос актуального списка моделей у OpenRouter...")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        free_models = []
        for model in data.get('data', []):
            model_id = model.get('id', '')
            # Фильтруем только бесплатные модели (по наличию :free или нулевой цене)
            if ':free' in model_id.lower():
                free_models.append(model_id)
                
        print(f"✅ Найдено {len(free_models)} бесплатных моделей в API.")
        return free_models
    except Exception as e:
        print(f"❌ Ошибка при получении списка моделей: {e}")
        return []

def test_model(model_name):
    """Быстро тестирует одну модель на способность ответить"""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": "Кратко: что такое RSI?"}],
        "max_tokens": 30
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=20)
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                return "✅ РАБОТАЕТ"
            return "⚠️ Пустой ответ"
        elif response.status_code == 429:
            return "⏳ Rate Limit"
        elif response.status_code == 404:
            return "❌ Не найдена (404)"
        elif response.status_code == 402:
            return "💰 Стала платной"
        else:
            return f"❌ Ошибка {response.status_code}"
    except Exception as e:
        return f"❌ Сбой: {str(e)[:30]}"

def main():
    print("=" * 75)
    print("🧪 ЕДИНЫЙ ТЕСТ: ПОЛУЧЕНИЕ И ПРОВЕРКА АКТУАЛЬНЫХ МОДЕЛЕЙ OPENROUTER")
    print("=" * 75)
    
    # 1. Получаем свежий список из API
    all_free_models = get_free_models_from_api()
    if not all_free_models:
        print("⚠️ Не удалось получить список моделей. Завершение.")
        return

    # 2. Тестируем их (берем первые 30, чтобы не ждать час и не получить бан по IP)
    # Можно увеличить число, если нужно проверить абсолютно все
    models_to_test = all_free_models[:30] 
    
    print(f"\n🔬 Начинаем тестирование {len(models_to_test)} моделей (пауза 1.5 сек между запросами)...\n")
    
    working_models = []
    for i, model in enumerate(models_to_test, 1):
        print(f"[{i:2d}/{len(models_to_test)}] {model}")
        result = test_model(model)
        print(f"      Статус: {result}")
        
        if "✅ РАБОТАЕТ" in result:
            working_models.append(model)
            
        time.sleep(1.5) # Критически важно: защита от Rate Limit
        
    # 3. Выводим готовый результат для копирования
    print("\n" + "=" * 75)
    print(f"📊 ИТОГ: Стабильно работают {len(working_models)} из {len(models_to_test)} протестированных моделей")
    
    if working_models:
        print("\n🎯 ГОТОВЫЙ СПИСОК ДЛЯ ВСТАВКИ В `ai_models_config.py` (BACKUP_MODELS):")
        print("BACKUP_MODELS = [")
        for m in working_models:
            print(f'    "{m}",')
        print("]")
    print("=" * 75)

if __name__ == "__main__":
    main()
