# Suporte a OCR para PDFs Escaneados

## 📋 Visão Geral

O extrator agora suporta **3 estratégias de extração de texto**:

1. **pdfplumber** (preferido) - Extrai texto nativo do PDF
2. **PyMuPDF** (fallback) - Alternativa para texto nativo
3. **OCR com Tesseract** (para PDFs escaneados) - Converte imagem em texto

## 🔄 Como Funciona

```
PDF de Entrada
    ↓
┌─────────────────────────────────────┐
│ 1. Tenta extrair texto nativo       │
│    (pdfplumber + PyMuPDF)           │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 2. Texto < 400 caracteres?          │
│    Provavelmente PDF escaneado      │
└─────────────────────────────────────┘
    ↓ SIM
┌─────────────────────────────────────┐
│ 3. Renderiza páginas como imagens  │
│    (300 DPI) e aplica OCR           │
│    (pytesseract em português)       │
└─────────────────────────────────────┘
    ↓
Texto Extraído → Regex → Dados Estruturados
```

## 📦 Instalação

### 1. Instalar Dependências Python

```bash
pip install -r requirements.txt
```

Isso instalará:
- `PyMuPDF==1.23.8` - Renderização de PDFs
- `Pillow==10.1.0` - Processamento de imagens
- `pytesseract==0.3.10` - Interface Python para Tesseract

### 2. Instalar Tesseract OCR

#### Windows

1. Baixe o instalador: https://github.com/UB-Mannheim/tesseract/wiki
2. Execute o instalador (recomendado: `tesseract-ocr-w64-setup-5.3.x.exe`)
3. Durante a instalação, marque **"Portuguese"** nos idiomas adicionais
4. Adicione ao PATH ou configure manualmente:

```python
# Se não estiver no PATH, adicione no código:
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

#### Linux (Ubuntu/Debian)

```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-por
```

#### macOS

```bash
brew install tesseract tesseract-lang
```

### 3. Verificar Instalação

```bash
tesseract --version
tesseract --list-langs
```

Deve aparecer `por` (português) na lista de idiomas.

## 🧪 Testando OCR

### Teste Rápido

```python
from extrator_pdf import ExtratorCertificado

extrator = ExtratorCertificado()

# Testa com PDF escaneado
texto = extrator.extrair_texto_pdf("certificado_escaneado.pdf")
print(f"Texto extraído: {len(texto)} caracteres")
print(texto[:500])  # Primeiros 500 caracteres
```

### Teste com Processamento Completo

```bash
python processar_pdfs.py
```

Se o PDF for escaneado, você verá:
```
[INFO] Texto nativo insuficiente (45 chars), tentando OCR...
[OK] OCR extraiu 2847 caracteres
```

## ⚙️ Configurações Avançadas

### Ajustar DPI do OCR

Maior DPI = melhor qualidade, mas mais lento:

```python
# No arquivo extrator_pdf.py, método _extrair_com_ocr
texto_ocr = self._extrair_com_ocr(caminho_pdf, dpi=400)  # Padrão: 300
```

### Ajustar Limite de Texto Mínimo

```python
# No método extrair_texto_pdf
if len(texto_completo.strip()) < 400:  # Ajuste este valor
    # Tenta OCR...
```

### Configurar Tesseract para Melhor Precisão

```python
# Adicione configurações customizadas no pytesseract
import pytesseract

custom_config = r'--oem 3 --psm 6'  # OCR Engine Mode 3, Page Segmentation Mode 6
texto = pytesseract.image_to_string(img, lang="por", config=custom_config)
```

**Modos úteis:**
- `--psm 6`: Assume um bloco uniforme de texto
- `--psm 3`: Segmentação automática de página (padrão)
- `--oem 3`: LSTM neural network (mais preciso)

## 📊 Comparação de Métodos

| Método | Velocidade | Precisão | Quando Usar |
|--------|-----------|----------|-------------|
| **pdfplumber** | ⚡⚡⚡ Rápido | 🎯🎯🎯 Perfeita | PDFs com texto nativo |
| **PyMuPDF** | ⚡⚡ Médio | 🎯🎯🎯 Perfeita | Fallback para texto nativo |
| **OCR (Tesseract)** | ⚡ Lento | 🎯🎯 Boa (90-95%) | PDFs escaneados/imagens |

## ⚠️ Limitações do OCR

1. **Erros de reconhecimento**: Números e caracteres especiais podem ser confundidos
   - `0` ↔ `O`, `1` ↔ `l`, `5` ↔ `S`
   
2. **Tabelas complexas**: Pode perder formatação

3. **Qualidade da imagem**: PDFs de baixa resolução terão resultados piores

4. **Performance**: OCR é ~10-20x mais lento que extração de texto nativo

## 🔍 Troubleshooting

### Erro: "Tesseract not found"

**Solução Windows:**
```python
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

**Solução Linux:**
```bash
which tesseract  # Verifica se está instalado
sudo apt-get install tesseract-ocr tesseract-ocr-por
```

### Erro: "Failed loading language 'por'"

**Solução:** Reinstale com pacote de idiomas:
```bash
# Windows: Reinstale marcando "Portuguese" no instalador
# Linux:
sudo apt-get install tesseract-ocr-por
```

### OCR retorna texto vazio ou incorreto

**Soluções:**
1. Aumente o DPI: `dpi=400` ou `dpi=600`
2. Pré-processe a imagem (contraste, binarização)
3. Verifique se o PDF não está protegido/criptografado

## 📝 Exemplo Completo

```python
"""
Exemplo de uso do extrator com suporte a OCR
"""

from extrator_pdf import ExtratorCertificado
from pathlib import Path

def processar_certificado(caminho_pdf: str):
    """Processa um certificado (nativo ou escaneado)"""
    
    extrator = ExtratorCertificado()
    
    # Extrai texto (usa OCR automaticamente se necessário)
    print(f"\nProcessando: {caminho_pdf}")
    instrumento = extrator.processar_pdf(caminho_pdf)
    
    if instrumento:
        print(f"\n✓ Extraído com sucesso!")
        print(f"  Identificação: {instrumento['identificacao']}")
        print(f"  Nome: {instrumento['nome']}")
        print(f"  Fabricante: {instrumento['fabricante']}")
        print(f"  Nº Série: {instrumento['numero_serie']}")
        print(f"  Data Calibração: {instrumento['data_calibracao']}")
        
        # Verifica se foi usado OCR
        if instrumento.get('laboratorio') == 'Gmetro':
            print(f"  Laboratório: Gmetro (formato específico detectado)")
    else:
        print("✗ Falha na extração")

if __name__ == "__main__":
    # Processa todos os PDFs na pasta
    pdfs = list(Path("pdfs").glob("*.pdf"))
    
    for pdf in pdfs:
        processar_certificado(str(pdf))
```

## 🚀 Próximos Passos

Para melhorar ainda mais a extração com OCR:

1. **Pré-processamento de imagens**: Aplicar filtros (contraste, binarização, remoção de ruído)
2. **Treinamento customizado**: Treinar Tesseract com fontes específicas dos certificados
3. **Validação de dados**: Verificar campos extraídos com regras de negócio
4. **Cache de OCR**: Salvar resultados de OCR para evitar reprocessamento

---

**Desenvolvido para o Sistema Gocal**  
Suporte a certificados de calibração com texto nativo e escaneados
