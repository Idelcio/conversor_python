# 📝 Como Usar o Editor de Campos

## 🎯 Guia Completo de Edição

### **1. Extrair Dados**
```
👤 "extrair tudo"
🤖 [Mostra Editor de Campos]
```

---

## ✏️ **Como Editar**

### **Passo a Passo:**

1. **Encontre o campo** que quer editar
2. **Clique no input** (caixa de texto)
3. **Digite o novo valor**
4. **Pressione Enter** ou clique fora
5. **Veja no console** (F12) a confirmação: "✅ Valor atualizado"

---

## 🔍 **Verificar se Salvou**

### **Método 1: Console do Navegador**
```
1. Pressione F12
2. Vá na aba "Console"
3. Edite um campo
4. Veja a mensagem:
   ✅ Valor atualizado em array[0][serie_desenv]: 123
   💾 extractedData atualizado: [...]
```

### **Método 2: Botão Salvar**
```
1. Edite os campos
2. Clique em "💾 Salvar Edições"
3. Veja mensagem: "✅ Edições salvas!"
4. No console aparece: "💾 Dados salvos: [...]"
```

---

## 💾 **Inserir no Banco**

### **IMPORTANTE:**
As edições são salvas **automaticamente** quando você:
- Pressiona Enter
- Clica fora do campo

**NÃO precisa** clicar em "Salvar Edições" antes de inserir no banco!

### **Fluxo Correto:**
```
1. Editar campo → Enter
2. Editar outro campo → Enter
3. Clicar em "💾 Inserir no Banco"
4. ✅ Dados editados são inseridos!
```

---

## 🐛 **Solução de Problemas**

### **Problema: Editei mas não salvou no banco**

**Solução 1: Verifique o Console**
```
F12 → Console → Procure por:
✅ Valor atualizado em array[0][campo]: valor
```

**Solução 2: Clique em "Salvar Edições"**
```
Após editar, clique em "💾 Salvar Edições"
Veja a mensagem de confirmação
Depois insira no banco
```

**Solução 3: Recarregue e Tente Novamente**
```
Ctrl + Shift + R (limpa cache)
Faça upload novamente
Extraia e edite
```

---

## 📊 **Tipos de Dados**

### **Números**
```
Input: 123
Salvo como: 123 (número)
```

### **Strings**
```
Input: texto qualquer
Salvo como: "texto qualquer" (string)
```

### **Boolean**
```
Input: true
Salvo como: true (boolean)

Input: false
Salvo como: false (boolean)
```

### **Null**
```
Input: null
Salvo como: null
```

---

## ✅ **Checklist de Edição**

Antes de inserir no banco, verifique:

- [ ] Editei todos os campos necessários
- [ ] Pressionei Enter após cada edição
- [ ] Vi "✅ Valor atualizado" no console (F12)
- [ ] (Opcional) Cliquei em "💾 Salvar Edições"
- [ ] Agora posso clicar em "💾 Inserir no Banco"

---

## 🎯 **Exemplo Prático**

### **Cenário: Mudar serie_desenv de null para 123**

```
1. Encontre o campo "serie_desenv": null
2. Clique no input
3. Digite: 123
4. Pressione Enter
5. Console mostra:
   🔍 Navegando: ["instrumentos", "0"] Key: serie_desenv Novo valor: 123
   ✅ Valor atualizado em array[0][serie_desenv]: 123
   💾 extractedData atualizado: [...]
6. Clique em "💾 Inserir no Banco"
7. ✅ Valor 123 é inserido no banco!
```

---

## 🚨 **Avisos Importantes**

1. **Sempre pressione Enter** após editar
2. **Verifique o console** (F12) para confirmar
3. **Não recarregue a página** antes de inserir no banco
4. **Edições são perdidas** se recarregar sem inserir

---

**Agora você sabe usar o Editor de Campos! 🎉**
