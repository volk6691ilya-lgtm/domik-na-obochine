import os
import requests
import time
from ai_models_config import ALL_MODELS, PRIMARY_MODELS

def get_free_models_from_api():
    """Получает актуальный список бесплатных моделей от OpenRouter"""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ Ключ OPENROUTER_API_KEY не найден!")
        return []
    
    url = "https://openrouter.ai/api/v1/models"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    try:
        print(" Запрос актуального списка моделей у OpenRouter...")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        free_models = []
        for model in data.get('data', []):
            model_id = model.get('id', '')
            if ':free' in model_id.lower():
                free_models.append(model_id)
                
        print(f"✅ Найдено {len(free_models)} бесплатных моделей в API.")
        return free_models
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return []

def test_model(model_name):
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return "❌ Нет API ключа"
    
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
        response = requests.post(url, json=payload, headers=headers, timeout=25)
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                return "✅ РАБОТАЕТ"
            return "⚠️ Пустой ответ"
        elif response.status_code == 429:
            return " Rate Limit"
        elif response.status_code == 404:
            return "❌ Не найдена (404)"
        elif response.status_code == 402:
            return "💰 Платная"
        else:
            return f"❌ Ошибка {response.status_code}"
    except Exception as e:
        return f"❌ Сбой: {str(e)[:30]}"

def main():
    print("=" * 75)
    print("🧪 ТЕСТ ИИ-МОДЕЛЕЙ: ПОИСК НОВЫХ МОДЕЛЕЙ В API OPENROUTER")
    print("=" * 75)
    
    # Получаем свежие модели из API
    api_models = get_free_models_from_api()
    if not api_models:
        print("⚠️ Не удалось получить список моделей. Завершение.")
        return
    
    # Находим новые модели (которые есть в API, но нет в конфиге)
    existing_models = set(ALL_MODELS)
    new_models = [m for m in api_models if m not in existing_models]
    
    print(f"\n📊 СТАТИСТИКА:")
    print(f"   Всего в API: {len(api_models)}")
    print(f"   Уже в конфиге: {len(existing_models)}")
    print(f"   НОВЫХ моделей: {len(new_models)}")
    
    if new_models:
        print(f"\n🆕 НОВЫЕ МОДЕЛИ (не в конфиге):")
        for i, model in enumerate(new_models[:15], 1):  # Показываем первые 15
            print(f"   {i}. {model}")
        if len(new_models) > 15:
            print(f"   ... и ещё {len(new_models) - 15}")
    
    # Тестируем ВСЕ модели из API (и старые, и новые)
    print(f"\n🔬 ТЕСТИРОВАНИЕ ВСЕХ МОДЕЛЕЙ ({len(api_models)} штук)...")
    print("-" * 75)
    
    working_models = []
    for i, model in enumerate(api_models, 1):
        print(f"[{i:3d}/{len(api_models)}] {model}")
        result = test_model(model)
        print(f"            Статус: {result}")
        if "✅ РАБОТАЕТ" in result:
            working_models.append(model)
        time.sleep(1.5)
    
    print("\n" + "=" * 75)
    print(f" ИТОГ: Работает {len(working_models)} из {len(api_models)}")
    
    if working_models:
        print("\n🎯 ГОТОВЫЙ СПИСОК ДЛЯ ai_models_config.py (BACKUP_MODELS):")
        print("BACKUP_MODELS = [")
        for m in working_models:
            if m not in PRIMARY_MODELS.values():  # Исключаем основные модели
                print(f'    "{m}",')
        print("]")
        
        print("\n🆕 НОВЫЕ РАБОЧИЕ МОДЕЛИ (добавь в конфиг):")
        new_working = [m for m in working_models if m in new_models]
        if new_working:
            for m in new_working:
                print(f'    "{m}",')
        else:
            print("   (нет новых рабочих моделей)")
            
    print("=" * 75)

if __name__ == "__main__":
    main()
