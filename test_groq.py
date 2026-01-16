"""
Script de teste para verificar se a API do Groq está funcionando
"""

from assistente_groq import inicializar_assistente

# Inicializa o assistente
print("Inicializando assistente Groq...")
assistente = inicializar_assistente()

# Verifica se está disponível
if assistente.esta_disponivel():
    print("✅ Assistente Groq disponível!")
    
    # Testa um comando simples
    print("\nTestando comando: 'quanto é 10 + 10?'")
    resultado = assistente.processar_comando("quanto é 10 + 10?")
    
    print(f"\nResultado:")
    print(f"  Tipo: {resultado.get('tipo')}")
    print(f"  Resposta: {resultado.get('resposta')}")
    
else:
    print("❌ Assistente Groq NÃO disponível!")
    print("   Verifique se a GROQ_API_KEY está configurada corretamente no arquivo .env")
