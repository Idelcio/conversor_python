# 🔧 Guia de Edição de Instrumentos via Chat

## 📋 Visão Geral

Agora você pode **editar qualquer campo dos instrumentos extraídos ANTES de inserir no banco de dados** usando comandos naturais no chat!

## 🚀 Como Funciona

### 1️⃣ **Extrair os PDFs**
Primeiro, faça upload dos PDFs e extraia os dados normalmente:
```
"metron extrai tudo"
```

Os instrumentos serão salvos temporariamente na sua sessão.

### 2️⃣ **Editar Campos**
Use comandos naturais para editar qualquer campo:

#### Exemplos de Comandos:

**Alterar número de série:**
```
muda o numero de serie do arquivo x34 de 456 para 123
```

**Alterar tag/identificação:**
```
altera a tag do certificado ABC para XYZ
```

**Corrigir fabricante:**
```
corrige o fabricante do instrumento metron para Mitutoyo
```

**Atualizar modelo:**
```
mude o modelo do pdf teste123 para ABC-500
```

**Trocar status:**
```
atualiza o status do item x para Calibrado
```

### 3️⃣ **Confirmar e Inserir**
Depois de fazer todas as edições, insira no banco:
- Clique no botão "Inserir no Banco"
- Ou use o comando: `"inserir no banco"`

## 📝 Padrões de Comando

### Padrão Completo (com valor antigo):
```
[verbo] [campo] do [tipo] [identificador] de [valor_antigo] para [valor_novo]
```

### Padrão Simplificado (sem valor antigo):
```
[verbo] [campo] do [tipo] [identificador] para [valor_novo]
```

### Verbos Aceitos:
- `muda` / `mude`
- `altera` / `altere`
- `corrige` / `corrija`
- `atualiza` / `atualize`
- `troca` / `troque`

### Tipos de Identificador:
- `arquivo` - nome do arquivo PDF
- `certificado` - tag/identificação
- `instrumento` - tag/identificação
- `pdf` - nome do arquivo PDF
- `tag` - tag/identificação
- `item` - tag/identificação

### Campos Editáveis:

| Nome do Campo | Aliases Aceitos |
|--------------|----------------|
| **identificacao** | tag, identificação, codigo, código, id |
| **nome** | nome, denominacao, denominação, instrumento |
| **fabricante** | fabricante, marca |
| **modelo** | modelo, model |
| **numero_serie** | numero de serie, número de série, serie, série, serial, ns |
| **descricao** | descricao, descrição |
| **periodicidade** | periodicidade |
| **departamento** | departamento, endereco, endereço, local |
| **responsavel** | responsavel, responsável, cliente |
| **status** | status |
| **tipo_familia** | tipo, familia, família, tipo familia, tipo família |

## 💡 Dicas

1. **Identificador Flexível**: Você pode usar a tag/identificação OU o nome do arquivo PDF
2. **Confirmação Visual**: Após cada edição, o sistema mostra o antes/depois
3. **Múltiplas Edições**: Faça quantas edições quiser antes de inserir no banco
4. **Sessão Temporária**: Os dados ficam salvos na sua sessão por 2 horas

## ⚠️ Importante

- As edições são temporárias até você clicar em "Inserir no Banco"
- Se você fechar o navegador ou a sessão expirar (2h), as edições serão perdidas
- Após inserir no banco, os dados são limpos da sessão

## 🎯 Exemplo Completo de Fluxo

```
1. Você: "metron extrai tudo"
   → Sistema extrai 3 instrumentos

2. Você: "muda o numero de serie do arquivo cert_001 para ABC123"
   → Sistema confirma a alteração

3. Você: "corrige o fabricante do certificado TAG-X para Mitutoyo"
   → Sistema confirma a alteração

4. Você: "inserir no banco"
   → Sistema insere os 3 instrumentos (com as edições) no banco
```

## 🔍 Ver Instrumentos Pendentes

Para ver quais instrumentos estão aguardando inserção:
```
GET /instrumentos-pendentes
```

Retorna todos os instrumentos extraídos (com edições aplicadas) que ainda não foram inseridos no banco.
