"""Teste de upload para debug"""
import requests

# Testa upload de PDF
url = 'http://localhost:5000/processar'

# Abre o PDF de teste
with open('032369-2024-2024-09-11.pdf', 'rb') as f:
    files = {'pdfs': ('teste.pdf', f, 'application/pdf')}

    print("Enviando requisição...")
    response = requests.post(url, files=files)

    print(f"Status Code: {response.status_code}")
    print(f"Headers: {response.headers}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")
    print(f"\nResposta:")
    print(response.text[:500] if response.text else "(vazio)")

    # Tenta parsear JSON
    try:
        json_data = response.json()
        print(f"\nJSON parseado com sucesso:")
        print(json_data)
    except Exception as e:
        print(f"\nErro ao parsear JSON: {e}")
