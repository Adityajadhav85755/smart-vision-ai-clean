import google.generativeai as genai

# Your new API key
API_KEY = "AIzaSyCxVQRqlIniY60VOOVTqBZUwPYMKamyqJI"

print("=" * 50)
print("🔍 TESTING GEMINI API CONNECTION")
print("=" * 50)

try:
    # Configure the API
    genai.configure(api_key=API_KEY)
    print("✅ API Key configured successfully")
    
    # List available models
    print("\n📋 Available models:")
    models = genai.list_models()
    model_found = False
    
    for model in models:
        print(f"  - {model.name}")
        if 'generateContent' in model.supported_generation_methods:
            print(f"    ✅ Supports text generation")
            if not model_found:
                # Try the first working model
                test_model = model.name
                model_found = True
    
    if model_found:
        print(f"\n🔧 Testing with model: {test_model}")
        
        # Create model instance
        model = genai.GenerativeModel(test_model)
        
        # Simple test prompt
        response = model.generate_content("Say 'Hello! Gemini API is working perfectly!'")
        
        print(f"\n📝 Response received:")
        print(f"   {response.text}")
        print("\n✅✅✅ API IS WORKING! ✅✅✅")
    else:
        print("\n❌ No suitable model found for text generation")
        
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    print("\n❌❌❌ API IS NOT WORKING ❌❌❌")

print("\n" + "=" * 50)