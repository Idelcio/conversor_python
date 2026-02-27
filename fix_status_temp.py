
import os

try:
    path = '/root/app_python/app_openai.py'
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Busca trecho exato (pode variar espaco, entao vou buscar parte dele)
    # A linha era: status = normalizar_status(buscar_valor('status', inst)) or 'Em Revisão'
    
    # Vou buscar e substituir a linha inteira usando regex seria melhor, mas vou tentar string simples
    old_code = "status = normalizar_status(buscar_valor('status', inst)) or 'Em Revisão'"
    new_code = "status = 'Em Revisão' # Forcado sempre para IA"

    if old_code in content:
        content = content.replace(old_code, new_code)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Status corrigido com sucesso!")
    else:
        print(f"String nao encontrada: {old_code}")
        # Tenta buscar variacao sem espacos ou aspas duplas, mas o codigo original usava aspas simples
        print("Tentando variacao...")
        
except FileNotFoundError:
    print("Arquivo app_openai.py nao encontrado.")
except Exception as e:
    print(f"Erro: {e}")
