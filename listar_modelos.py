from google import genai

# Use sua chave
client = genai.Client(api_key="AIzaSyBt8PiTH7khVOQi7ralAeao6CAdXocAKK8")

print("Modelos disponíveis na sua conta:\n")

for model in client.models.list():
    print(f"✅ {model.name}")
```

Salva como `listar_modelos.py` e roda:
```
python listar_modelos.py