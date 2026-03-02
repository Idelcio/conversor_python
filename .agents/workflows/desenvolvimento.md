# Workflow: Desenvolvimento Seguro (Non-Destructive)

## Regra principal

**Nunca modificar uma função que já está funcionando.**

Sempre criar uma função nova ao lado, mesmo que precise chamar a antiga internamente.
Só depois de testada e aprovada é que as duas são unidas e a versão final substitui a antiga.

---

## Passo a passo

### 1. Identificar o que precisa mudar
- Leia a função existente sem alterar nada
- Entenda exatamente o que ela faz e onde é chamada

### 2. Criar a nova versão ao lado
```python
# ❌ Errado — mexe no que funciona
def inserir_banco():
    # modifica aqui...

# ✅ Certo — cria ao lado, pode chamar a antiga se precisar
def inserir_banco_v2():
    # nova lógica
    # resultado_antigo = inserir_banco()  # pode reaproveitar
```

No frontend (JS):
```javascript
// ❌ Errado
function sendMessage() { /* modifica ... */ }

// ✅ Certo
function sendMessageV2() { /* nova lógica, pode chamar sendMessage() */ }
```

### 3. Testar a nova função isoladamente
- Chamar a nova sem remover a antiga
- Garantir que o fluxo existente não foi quebrado
- Validar com o usuário

### 4. Substituir após aprovação
- Somente após o usuário confirmar que funcionou
- Remover a antiga, renomear a nova para o nome original
- Commitar com mensagem clara

---

## Convenção de nomes temporários

| Contexto | Sufixo |
|---|---|
| Python (backend) | `_v2`, `_novo`, `_refatorado` |
| JavaScript (frontend) | `V2`, `Novo`, `Refatorado` |
| Rotas Flask | `/v2/rota` ou `/rota-novo` |

---

## Quando juntar as duas

Só juntar quando:
- [ ] Testou manualmente o fluxo completo
- [ ] Usuário aprovou o comportamento
- [ ] Não quebrou nenhuma funcionalidade existente

---

## Por que essa regra existe

Evita o padrão destrutivo de "vou só ajustar isso aqui" que acaba quebrando
funcionalidades que já estavam funcionando e dificultam o rollback.
Com funções paralelas, o rollback é trivial: basta parar de chamar a nova.

## Protecao critica: tabelas e graficos

**As rotinas de criacao/atualizacao de tabelas e graficos sao areas protegidas.**

Regra obrigatoria:
- Nao alterar codigo dessas rotinas sem ordem explicita do usuario
- Antes de implementar qualquer mudanca, revisar o codigo proposto e validar impacto em comportamento, dependencias e regressao
- Sem essa verificacao previa, a alteracao deve ser bloqueada
- Quando autorizado, aplicar o fluxo nao-destrutivo (criar versao nova ao lado, testar, validar com usuario e so depois substituir)

### Funcoes protegidas mapeadas (codigo atual)

Arquivo: `static/js/gocal_chat.js`
- `markdownToHtml(text)` -> renderizacao de tabela Markdown/HTML e tratamento de quebra de linha no chat
- `buscarEExibirInstrumentos(filtros)` -> renderizacao de tabela HTML de instrumentos no chat
- `renderGraficoCalib(grafico)` -> renderizacao do grafico de calibracao via Chart.js

Regra: qualquer mudanca nessas funcoes so pode ocorrer com ordem explicita do usuario e revisao tecnica previa.
