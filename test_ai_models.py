import os
import requests
import json

# Твои текущие модели
MODELS_TO_TEST = [
    "minimax/minimax-m3:free",
    "nvidia/nemotron-3.5-lightning:free",
    "inclusionai/ling-3.0-flash-fin:free"
]

# Дополнительные модели для тестирования
EXTRA_MODELS = [
    "google/gemini-2.0-flash-exp:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "deepseek/deepseek-chat-v3-0324:free",
    "qwen/qwen3-235b-a22b:free",
    "google/gemma-3-27b-it:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "cognitivecomputations/dolphin3.0-mistral-24b:free"
]

def test_model(model_name):
    """Тестирует одну модель"""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    
    if not api_key:
        return "❌ API ключ не найден"
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    payload = {
        "model": model_name,
        "messages": [
            {"role": "user", "content": "Скажи 'тест работает' на русском"}
        ],
        "max_tokens": 50
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                return "✅ Работает"
            else:
                return "⚠️ Пустой ответ"
        elif response.status_code == 429:
            return " Rate limit (перегружена)"
        elif response.status_code == 402:
            return "💰 Требует оплату"
        elif response.status_code == 404:
            return "❌ Модель не найдена"
        else:
            return f"❌ Ошибка {response.status_code}"
    except Exception as e:
        return f"❌ Ошибка: {str(e)[:50]}"

def main():
    print("=" * 60)
    print("🧪 ТЕСТ ИИ-МОДЕЛЕЙ OPENROUTER")
    print("=" * 60)
    print()
    
    print("📋 ТЕКУЩИЕ МОДЕЛИ:")
    print("-" * 60)
    for model in MODELS_TO_TEST:
        print(f"🔍 Тестируем: {model}")
        result = test_model(model)
        print(f"   Результат: {result}")
        print()
    
    print("=" * 60)
    print("📋 ДОПОЛНИТЕЛЬНЫЕ МОДЕЛИ ДЛЯ РЕЗЕРВА:")
    print("-" * 60)
    working_models = []
    
    for model in EXTRA_MODELS:
        print(f"🔍 Тестируем: {model}")
        result = test_model(model)
        print(f"   Результат: {result}")
        
        if "✅" in result:
            working_models.append(model)
        print()
    
    print("=" * 60)
    print("📊 ИТОГОВЫЙ ОТЧЁТ:")
    print("-" * 60)
    print(f"✅ Рабочих дополнительных моделей: {len(working_models)}")
    
    if working_models:
        print("\n🎯 РЕКОМЕНДУЕМЫЙ СПИСОК МОДЕЛЕЙ:")
        all_models = MODELS_TO_TEST + working_models
        for i, model in enumerate(all_models, 1):
            print(f"{i}. {model}")
        
        print("\n📝 СКОПИРУЙ ЭТОТ СПИСОК В main.py:")
        print("\n    models = [")
        for model in all_models:
            print(f'        "{model}",')
        print("    ]")
    else:
        print("\n⚠️ Все дополнительные модели недоступны. Используем только текущие.")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
