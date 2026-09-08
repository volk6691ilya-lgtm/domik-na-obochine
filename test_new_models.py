import os
import requests
import json

# Модели из list_free_models (актуальный список)
NEW_MODELS = [
    "cohere/north-mini-code:free",
    "dots-studio/dots-3-note-preview:free",
    "google/gemma-4-26b-a4b-it:free",
    "google/gemma-4-31b-it:free",
    "liquid/lfm-2.5-2.6b:free",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "nvidia/nemotron-3.5-content-safety:free",
    "nvidia/nemotron-3.5-lightning:free",  # Уже знаем что работает
    "poolside/laguna-s-2.1:free",
    "poolside/laguna-xs-2.1:free",
    "thinkingmachines/inkling:free",
    "thinkingmachines/inkling-small:free",
    "inclusionai/ling-3.0-flash-fin:free",  # Уже знаем что работает
    "inclusionai/ling-3.0-flash-sante:free"
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
            return "⏳ Rate limit"
        elif response.status_code == 402:
            return "💰 Требует оплату"
        elif response.status_code == 404:
            return "❌ Модель не найдена"
        else:
            return f"❌ Ошибка {response.status_code}"
    except Exception as e:
        return f"❌ Ошибка: {str(e)[:50]}"

def main():
    print("=" * 70)
    print("🧪 ТЕСТ НОВЫХ МОДЕЛЕЙ OPENROUTER (актуальный список)")
    print("=" * 70)
    print()
    
    working_models = []
    
    for i, model in enumerate(NEW_MODELS, 1):
        print(f"[{i:2d}/16] Тестируем: {model}")
        result = test_model(model)
        print(f"       Результат: {result}")
        
        if "✅" in result:
            working_models.append(model)
        print()
    
    print("=" * 70)
    print("📊 ИТОГОВЫЙ ОТЧЁТ:")
    print("=" * 70)
    print(f"\n✅ Рабочих моделей: {len(working_models)} из {len(NEW_MODELS)}")
    
    if working_models:
        print("\n🎯 СПИСОК РАБОЧИХ МОДЕЛЕЙ:")
        for i, model in enumerate(working_models, 1):
            print(f"  {i}. {model}")
        
        print("\n📝 СКОПИРУЙ ЭТОТ СПИСОК В main.py:")
        print("\n    models = [")
        for model in working_models:
            print(f'        "{model}",')
        print("    ]")
    else:
        print("\n⚠️ Ни одна модель не работает!")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
