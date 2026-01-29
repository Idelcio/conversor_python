# 📝 Editor JSON Interativo - Metron

## 🎯 O que é?

Uma interface visual e interativa para **editar os dados extraídos dos PDFs** em formato JSON, antes de inserir no banco de dados.

---

## 🚀 Como Usar

### 1. **Acesse o Editor**
```
http://localhost:5000/json-editor
```

### 2. **Faça Upload dos PDFs**
- Clique na área de upload ou arraste os PDFs
- Os arquivos serão listados na sidebar

### 3. **Extraia os Dados**
- Clique no botão **"🔍 Extrair Dados"**
- Aguarde o processamento
- O JSON será exibido em formato de árvore editável

### 4. **Edite os Valores**
- Clique em qualquer campo para editar
- As mudanças são salvas automaticamente
- Use os botões **▼/▶** para expandir/recolher seções

### 5. **Ações Disponíveis**

| Botão | Função |
|-------|--------|
| **✨ Formatar JSON** | Reorganiza e formata o JSON |
| **💾 Baixar JSON** | Baixa o JSON editado |
| **✅ Inserir no Banco** | Insere os dados no MySQL |

---

## ✨ Funcionalidades

### **Editor Interativo**
- ✅ Edição em tempo real
- ✅ Validação de tipos (string, number)
- ✅ Estrutura em árvore colapsável
- ✅ Syntax highlighting

### **Interface Moderna**
- 🌙 **Tema Claro/Escuro**
- 📱 **Responsivo**
- ⚡ **Rápido e fluido**
- 🎨 **Design premium**

### **Gerenciamento de Arquivos**
- 📄 Upload múltiplo
- 🗑️ Remover arquivos
- 📊 Visualizar tamanho

---

## 🎨 Diferenças do Chat

| Recurso | Chat | Editor JSON |
|---------|------|-------------|
| **Visualização** | Lista formatada | Árvore JSON |
| **Edição** | Por comando | Direta nos campos |
| **Estrutura** | HTML preview | JSON editável |
| **Download** | Via botão | JSON puro |
| **Validação** | Automática | Em tempo real |

---

## 📖 Exemplo de Uso

### **Antes (Chat)**
```
👤 "muda o numero de serie do arquivo x34 para 123"
🤖 "✅ Campo editado com sucesso!"
```

### **Agora (Editor JSON)**
```json
{
  "numero_serie": "123" ← Edita diretamente aqui
}
```

---

## 🔧 Teclas de Atalho

| Tecla | Ação |
|-------|------|
| `Ctrl + S` | Salvar alterações |
| `Ctrl + F` | Formatar JSON |
| `Ctrl + D` | Baixar JSON |

---

## 💡 Dicas

1. **Expanda apenas o necessário** - Use os botões de colapso para navegar melhor
2. **Valide antes de salvar** - Verifique os valores editados
3. **Baixe uma cópia** - Sempre baixe o JSON antes de inserir no banco
4. **Use o tema escuro** - Melhor para longas sessões de edição

---

## 🎯 Quando Usar?

### **Use o Editor JSON quando:**
- ✅ Precisar editar **muitos campos** de uma vez
- ✅ Quiser **visualizar toda a estrutura** dos dados
- ✅ Precisar **validar** os dados antes de inserir
- ✅ Quiser **baixar** o JSON para backup

### **Use o Chat quando:**
- ✅ Precisar fazer **edições rápidas** pontuais
- ✅ Quiser usar **linguagem natural**
- ✅ Preferir uma **interface conversacional**

---

## 🚀 Acesso Rápido

```bash
# Inicie o servidor
python app.py

# Acesse:
http://localhost:5000/json-editor
```

---

**Desenvolvido com ❤️ pela equipe Metron**
