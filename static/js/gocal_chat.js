let uploadedFiles = [];
let extractedData = null;
let currentUserId = new URLSearchParams(window.location.search).get('user_id') || null;

// Escuta mensagem do Pai (Widget Loader) com o contexto do usuario
window.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'set_user_ctx') {
        currentUserId = event.data.user_id;
        console.log("[Chat] Contexto de usuario recebido:", currentUserId);
    }
});

const uploadBox = document.getElementById('uploadBox');
const fileInput = document.getElementById('fileInput');
const filesList = document.getElementById('filesList');
const filesContainer = document.getElementById('filesContainer');
const chatInput = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');
const chatMessages = document.getElementById('chatMessages');
const actionBar = document.getElementById('actionBar');
const themeToggle = document.getElementById('themeToggle');
const attachBtn = document.getElementById('attachBtn');

// Contexto do PDF da pagina pai
let contextPdfUrl = null;

window.addEventListener('message', (e) => {
    // Recebe URL do PDF detectado pelo widget
    if (e.data && e.data.type === 'context-pdf-url' && e.data.url) {
        console.log("PDF Contexto Detectado (Silencioso):", e.data.url);
        contextPdfUrl = e.data.url;
        // showContextToast(); // Desativado a pedido do usuario

        // Avisa visualmente no input de forma sutil
        if (chatInput.placeholder.indexOf('📄') === -1) {
            chatInput.placeholder = "📄 PDF de contexto detectado. Digite para analisar...";
        }
    }
});

window.analyzeContextPDF = async function () {
    const toast = document.getElementById('pdf-context-toast');
    if (toast) toast.remove();

    if (!contextPdfUrl) return;

    addBotMessage('📥 Baixando e analisando o documento da tela...');
    addLoadingMessage();

    try {
        const formData = new FormData();
        formData.append('pdf_url', contextPdfUrl);
        formData.append('comando', 'analise completa com checklist');

        const response = await fetch('/upload-async', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            pollProgress(data.task_id);
        } else {
            removeLastMessage();
            addBotMessage('❌ Erro ao baixar PDF: ' + data.message);
        }
    } catch (e) {
        removeLastMessage();
        addBotMessage('Erro técnico: ' + e.message);
    }
}

// Theme Toggle
themeToggle.addEventListener('click', () => {
    const body = document.body;
    const currentTheme = body.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    body.setAttribute('data-theme', newTheme);
    themeToggle.textContent = newTheme === 'light' ? '🌙' : '☀️';
    localStorage.setItem('theme', newTheme);
});

// Load saved theme
const savedTheme = localStorage.getItem('theme') || 'light';
document.body.setAttribute('data-theme', savedTheme);
themeToggle.textContent = savedTheme === 'light' ? '🌙' : '☀️';

// Auto-resize textarea
chatInput.addEventListener('input', function () {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 120) + 'px';
});

// Botão de anexar PDFs
attachBtn.addEventListener('click', () => fileInput.click());

// Drag & Drop no campo de texto
chatInput.addEventListener('dragover', (e) => {
    e.preventDefault();
    chatInput.classList.add('dragover');
});

chatInput.addEventListener('dragleave', () => {
    chatInput.classList.remove('dragover');
});

chatInput.addEventListener('drop', (e) => {
    e.preventDefault();
    chatInput.classList.remove('dragover');
    handleFiles(e.dataTransfer.files);
});

// Upload handlers (sidebar)
// ADICIONADO: Drag & Drop na tela inteira (REFORÇADO)
const events = ['dragenter', 'dragover', 'dragleave', 'drop'];

events.forEach(eventName => {
    document.body.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
    }, false);
});

document.body.addEventListener('dragover', (e) => {
    document.body.style.backgroundColor = '#eef';
});

document.body.addEventListener('dragleave', (e) => {
    if (e.clientX === 0 || e.clientY === 0) {
        document.body.style.backgroundColor = '';
    }
});

document.body.addEventListener('drop', (e) => {
    document.body.style.backgroundColor = '';
    if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        handleFiles(e.dataTransfer.files);
    }
});

uploadBox.addEventListener('click', () => fileInput.click());


uploadBox.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadBox.classList.add('dragover');
});

uploadBox.addEventListener('dragleave', () => {
    uploadBox.classList.remove('dragover');
});

uploadBox.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadBox.classList.remove('dragover');
    handleFiles(e.dataTransfer.files);
});

fileInput.addEventListener('change', (e) => {
    handleFiles(e.target.files);
});

function handleFiles(files) {
    uploadedFiles = Array.from(files);

    // VISUAL FEEDBACK IMEDIATO
    const fileNames = uploadedFiles.map(f => f.name).join(', ');

    // 1. Muda o placeholder
    chatInput.placeholder = `📄 ${uploadedFiles.length} arquivo(s) carregado(s)`;

    // 2. Mostra caixa visual acima do input
    const listDiv = document.getElementById('filesList');
    if (listDiv) {
        listDiv.style.display = 'block';
        listDiv.innerHTML = `
            <div style="background: #e3f2fd; color: #1565c0; padding: 8px; border-radius: 8px; font-size: 13px; display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; border: 1px solid #90caf9;">
                <div style="display:flex; align-items:center; gap:6px; overflow:hidden;">
                    <span>📄</span>
                    <span style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 200px;">
                        ${fileNames}
                    </span>
                </div>
                <button onclick="limparArquivos()" style="background:none; border:none; cursor:pointer; font-size:14px; color:#c62828;">✖</button>
            </div>
        `;
    }

    addBotMessage(`✅ ${files.length} arquivo(s) pronto(s)! Clique em 'Extrair Dados' ou digite um comando.`);
}

// Expor funcoes para o HTML (Garantia de funcionamento)
window.handleFiles = handleFiles;

function limparArquivos() {
    uploadedFiles = [];
    document.getElementById('filesList').style.display = 'none';
    chatInput.placeholder = "Digite ou arraste um PDF...";
    fileInput.value = ""; // Limpa o input para permitir selecionar o mesmo arquivo de novo
}
window.limparArquivos = limparArquivos;

// Função renderFilesList removida pois foi substituída pelo feedback visual direto em handleFiles.

// Chat handlers
sendBtn.addEventListener('click', sendMessage);
chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// Funcao para pedir o Blob ao pai (Promise-based)
function getPdfContentFromParent() {
    return new Promise((resolve, reject) => {
        // Timeout de seguranca (10s para garantir)
        const timeout = setTimeout(() => {
            window.removeEventListener('message', listener);
            reject("Timeout: Pai não respondeu com o PDF.");
        }, 10000);

        // Listener temporario
        const listener = (e) => {
            if (e.data && e.data.type === 'context-pdf-blob' && e.data.buffer) {
                clearTimeout(timeout);
                window.removeEventListener('message', listener);

                // Reconstroi Blob
                const blob = new Blob([e.data.buffer], { type: 'application/pdf' });
                resolve(blob);
            }
            if (e.data && e.data.type === 'context-pdf-error') {
                clearTimeout(timeout);
                window.removeEventListener('message', listener);
                reject("Erro no Pai: " + e.data.error);
            }
            if (e.data && e.data.type === 'context-pdf-not-found') {
                clearTimeout(timeout);
                window.removeEventListener('message', listener);
                reject("PDF não encontrado na página.");
            }
        };

        window.addEventListener('message', listener);

        // Pede ao pai
        window.parent.postMessage('request-pdf-content', '*');
    });
}

async function sendMessage() {
    const message = chatInput.value.trim();
    // Se tem arquivos, message pode ser vazio (comando implícito)
    if (!message && uploadedFiles.length === 0 && !contextPdfUrl) return;

    if (message) addUserMessage(message);
    chatInput.value = '';
    chatInput.style.height = 'auto';

    addLoadingMessage();

    try {
        if (uploadedFiles.length > 0 || contextPdfUrl) {
            // MODO ASYNC (Upload com Progresso ou Contexto URL)

            // Mostra barras de progresso vazias se tiver arquivo fisico
            if (uploadedFiles.length > 0) {
                document.querySelectorAll('.file-progress').forEach(el => el.style.display = 'block');
                document.querySelectorAll('.file-remove').forEach(el => el.style.display = 'none');
            }

            const formData = new FormData();

            // 1. Adiciona arquivos fisicos (Upload Manual)
            uploadedFiles.forEach(file => {
                formData.append('pdfs', file);
            });

            // 2. Se nao tem arquivo manual, mas tem Contexto PDF Pede ao pai
            if (uploadedFiles.length === 0 && contextPdfUrl) {
                addBotMessage('📥 Baixando documento da tela...');
                try {
                    // Pede ao pai o conteudo fisico (bypass CORS)
                    const pdfBlob = await getPdfContentFromParent();
                    const pdfFile = new File([pdfBlob], "documento_tela.pdf", { type: "application/pdf" });

                    // Anexa como se fosse um arquivo normal
                    formData.append('pdfs', pdfFile);
                } catch (err) {
                    console.error("Erro ao obter PDF do pai:", err);
                    addBotMessage('⚠️ Não consegui acessar o documento da tela: ' + err);
                    removeLastMessage();
                    return;
                }
            }

            if (message) {
                formData.append('comando', message);
            } else {
                formData.append('comando', 'resumo e analise geral');
            }

            // Envia para endpoint async
            const response = await fetch('/upload-async', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                // Inicia Polling
                pollProgress(data.task_id);
            } else {
                removeLastMessage();
                addBotMessage('❌ Erro no envio: ' + data.message);
            }

        } else {
            // MODO CHAT (Apenas Texto)
            const response = await fetch('/chat-mensagem', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: message })
            });

            const data = await response.json();
            removeLastMessage();
            addBotMessage(data.message);

            // Navegação Real
            if (data.redirect_url) {
                // Pequeno delay para o usuario ler a mensagem
                setTimeout(() => {
                    window.parent.postMessage({ type: 'navigate', url: data.redirect_url }, '*');
                }, 1000);
            }

            // Checklist Automático
            if (data.auto_checklist) {
                console.log("Aplicando checklist:", data.auto_checklist);
                window.parent.postMessage({ type: 'fill_checklist', data: data.auto_checklist }, '*');
            }
        }

    } catch (error) {
        console.error('Erro:', error);
        removeLastMessage();
        addBotMessage('Desculpe, ocorreu um erro na comunicação.');
    }
}

// Função de Polling para verificar progresso
function pollProgress(taskId) {
    const interval = setInterval(async () => {
        try {
            const res = await fetch(`/upload-status/${taskId}`);
            const statusData = await res.json();

            // Atualiza cada arquivo na lista lateral
            if (statusData.files) {
                for (const [filename, status] of Object.entries(statusData.files)) {
                    // Recria ID sanitizado
                    const fileId = 'file-' + filename.replace(/[^a-zA-Z0-9]/g, '');
                    const item = document.getElementById(fileId);
                    if (!item) continue;

                    const bar = item.querySelector('.file-progress-bar');
                    const icon = document.getElementById('status-' + fileId);

                    // Adiciona classe de animacao visual
                    // Adiciona classe de animacao visual
                    if (status === 'processing') {
                        bar.classList.add('processing'); // Animação lenta via CSS
                    } else if (status === 'done') {
                        bar.classList.remove('processing');
                        bar.style.width = '100%';
                        bar.style.background = '#4CAF50'; // Verde
                        icon.innerHTML = '✅';
                    } else if (status === 'error') {
                        bar.classList.remove('processing');
                        bar.style.width = '100%';
                        bar.style.background = '#e74c3c'; // Vermelho
                        icon.innerHTML = '⚠️';
                    }
                }
            }

            // Verifica conclusão total
            if (statusData.status === 'completed' || statusData.status === 'error') {
                clearInterval(interval);
                removeLastMessage(); // Remove loading spinner

                if (statusData.results && statusData.results.length > 0) {
                    extractedData = statusData.results;

                    // VERIFICA SE É RESPOSTA TEXTUAL (CHATGPT-STYLE)
                    const actionBar = document.getElementById('actionBar');

                    // NOVO: Verifica se é um CHECKLIST AUTOMATICO (Via Async)
                    const firstRes = extractedData[0];
                    const checklistPayload = firstRes.auto_checklist || firstRes.checklist_data;

                    if (checklistPayload) {
                        addBotMessage(firstRes.message || "✅ Checklist verificado! Marcando itens na tela...");
                        window.parent.postMessage({ type: 'fill_checklist', data: checklistPayload }, '*');

                        // Limpa input
                        fileInput.value = "";
                        uploadedFiles = [];
                        contextPdfUrl = null;
                        chatInput.placeholder = "Digite ou arraste um PDF...";
                        document.getElementById('filesList').style.display = 'none';

                        return; // Para por aqui
                    }

                    if (extractedData.length > 0 && extractedData[0].is_text_response) {
                        // Não esconde mais a action bar
                        // if (actionBar) actionBar.classList.remove('show');

                        extractedData.forEach((inst) => {
                            // Formata Markdown básico para HTML (quebras de linha e negrito)
                            let text = inst.descricao || "";
                            text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>'); // Negrito
                            text = text.replace(/\n/g, '<br>'); // Quebra de linha
                            addBotMessage(text);
                        });
                    } else {
                        // if (actionBar) actionBar.classList.add('show');
                        // MODO ESTRUTURADO (Cards JSON)
                        // 1. Resumo Textual
                        let summary = `✅ **Processamento concluído!** (${statusData.results.length} arquivos)<br><br>`;
                        statusData.results.forEach((inst, i) => {
                            const ident = inst.identificacao || inst.numero_certificado || 'S/N';
                            summary += `${i + 1}. <b>${ident}</b> - ${inst.nome || 'Instrumento'}<br>`;
                        });
                        addBotMessage(summary);

                        // 2. Editor de Cards
                        const cardsHTML = renderEditableJSON(extractedData);
                        addBotMessage(cardsHTML);
                    }

                    // 3. Limpa arquivos da lateral após 4 segundos
                    // 3. Limpa arquivos da lateral após 4 segundos (DESATIVADO PARA MANTER CONTEXTO)
                    /*
                    setTimeout(() => {
                        if (uploadedFiles.length > 0) {
                            uploadedFiles = [];
                            renderFilesList();
                        }
                    }, 4000);
                    */

                } else {
                    addBotMessage('⚠️ Processamento finalizado. Verifique erros na lista lateral.');
                }
            }
        } catch (e) {
            console.error("Polling error:", e);
            clearInterval(interval);
        }
    }, 1000); // Checa a cada 1 segundo
}


function gerarVisualizacao(instrumentos, comando) {
    comando = comando.toLowerCase();

    const wantsTags = comando.includes('tag') || comando.includes('identificação') || comando.includes('identificacao') || comando.includes('código') || comando.includes('codigo');
    const wantsOnlyTags = (wantsTags && comando.includes('apenas')) || (wantsTags && comando.includes('só')) || (wantsTags && comando.includes('somente'));

    let html = `<strong>✅ Processado com sucesso!</strong><br>`;
    html += `<span class="summary-badge">${instrumentos.length} instrumento(s)</span><br><br>`;

    if (wantsOnlyTags) {
        html += '<div class="tag-grid">';
        instrumentos.forEach(inst => {
            const tag = inst.identificacao || 'n/i';
            html += `<div class="tag-card">${tag}</div>`;
        });
        html += '</div>';
    } else if (comando.includes('lista') || comando.includes('listar')) {
        let errosProcessamento = [];
        instrumentos.forEach((inst, idx) => {
            try {
                // Trata arquivo_origem que pode ser string ou array
                let nomeArquivo = `Instrumento ${idx + 1}`;
                if (inst.arquivo_origem) {
                    if (typeof inst.arquivo_origem === 'string') {
                        nomeArquivo = inst.arquivo_origem.split(/[\\\/]/).pop().replace('.pdf', '');
                    } else if (Array.isArray(inst.arquivo_origem)) {
                        nomeArquivo = inst.arquivo_origem[0].split(/[\\\/]/).pop().replace('.pdf', '');
                    }
                }

                const temData = inst.data_calibracao && inst.data_calibracao !== 'n/i';
                const alertaData = temData ? '' : ' ⚠️';

                html += `<div class="instrument-card">`;
                html += `<div class="instrument-title">📄 ${nomeArquivo}${alertaData}</div>`;
                html += `<div class="quick-view">`;

                if (inst.identificacao && inst.identificacao !== 'n/i') {
                    html += `<div class="quick-item"><span class="quick-label">TAG:</span><span class="quick-value">${inst.identificacao}</span></div>`;
                }
                if (inst.nome && inst.nome !== 'n/i') {
                    html += `<div class="quick-item"><span class="quick-label">Nome:</span><span class="quick-value">${inst.nome}</span></div>`;
                }
                if (inst.fabricante && inst.fabricante !== 'n/i') {
                    html += `<div class="quick-item"><span class="quick-label">Fabricante:</span><span class="quick-value">${inst.fabricante}</span></div>`;
                }
                if (inst.modelo && inst.modelo !== 'n/i') {
                    html += `<div class="quick-item"><span class="quick-label">Modelo:</span><span class="quick-value">${inst.modelo}</span></div>`;
                }
                if (inst.data_calibracao && inst.data_calibracao !== 'n/i') {
                    html += `<div class="quick-item"><span class="quick-label">Data Calib.:</span><span class="quick-value">${inst.data_calibracao}</span></div>`;
                }

                html += `</div></div>`;
            } catch (error) {
                console.error(`Erro ao processar instrumento ${idx + 1}:`, error);
                errosProcessamento.push(`Instrumento ${idx + 1}: ${error.message}`);
            }
        });

        // Adiciona aviso de erros no final, se houver
        if (errosProcessamento.length > 0) {
            html += `<div style="padding: 12px; background: #fff3cd; border-left: 4px solid #ffc107; border-radius: 4px; margin-top: 12px;">`;
            html += `<strong>⚠️ Avisos de processamento:</strong><br>`;
            html += errosProcessamento.join('<br>');
            html += `</div>`;
        }
    } else {
        // Mostra TODOS os instrumentos (removido o limite de 5)
        let errosProcessamento = [];
        instrumentos.forEach((inst, idx) => {
            try {
                // Trata arquivo_origem que pode ser string ou array
                let nomeArquivo = `Instrumento ${idx + 1}`;
                if (inst.arquivo_origem) {
                    if (typeof inst.arquivo_origem === 'string') {
                        nomeArquivo = inst.arquivo_origem.split(/[\\\/]/).pop().replace('.pdf', '');
                    } else if (Array.isArray(inst.arquivo_origem)) {
                        nomeArquivo = inst.arquivo_origem[0].split(/[\\\/]/).pop().replace('.pdf', '');
                    }
                }

                const temData = inst.data_calibracao && inst.data_calibracao !== 'n/i';
                const alertaData = temData ? '' : ' ⚠️ <span style="color: #ff9800; font-size: 12px;">Sem data</span>';

                html += `<div class="instrument-card">`;
                html += `<div class="instrument-title">📄 ${nomeArquivo}${alertaData}</div>`;
                html += '<div class="data-table">';

                const campos = [
                    ['Identificação', inst.identificacao],
                    ['Nome', inst.nome],
                    ['Fabricante', inst.fabricante],
                    ['Modelo', inst.modelo],
                    ['Nº Série', inst.numero_serie],
                    ['Responsável', inst.responsavel],
                    ['Departamento', inst.departamento],
                    ['Data Calibração', inst.data_calibracao],
                    ['Data Emissão', inst.data_emissao]
                ];

                campos.forEach(([label, value]) => {
                    if (value && value !== 'n/i') {
                        html += `
                                    <div class="data-row">
                                        <div class="data-label">${label}</div>
                                        <div class="data-value">${value}</div>
                                    </div>
                                `;
                    }
                });

                // Show Grandezas
                if (inst.grandezas && Array.isArray(inst.grandezas) && inst.grandezas.length > 0) {
                    html += '<div style="padding: 12px; background: var(--bg-tertiary); border-top: 1px solid var(--border-color);">';
                    html += '<div style="font-weight: 600; margin-bottom: 8px; font-size: 13px; color: var(--text-secondary);">📏 Grandezas</div>';

                    inst.grandezas.forEach((grand, gIdx) => {
                        html += `<div style="background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 8px; padding: 10px; margin-bottom: 8px;">`;

                        const grandFields = [
                            ['Faixa Nominal', grand.faixa_nominal],
                            ['Unidade', grand.unidade],
                            ['Resolução', grand.resolucao],
                            ['Tolerância', grand.tolerancia_processo],
                            ['Critério', grand.criterio_aceitacao]
                        ];

                        grandFields.forEach(([gLabel, gValue]) => {
                            if (gValue && gValue !== 'n/i') {
                                html += `<div style="display: flex; font-size: 13px; margin-bottom: 4px;">
                                            <span style="color: var(--text-tertiary); width: 100px;">${gLabel}:</span>
                                            <span style="color: var(--text-primary); font-weight: 500;">${gValue}</span>
                                        </div>`;
                            }
                        });
                        html += '</div>';
                    });
                    html += '</div>';
                }

                html += '</div></div>';
            } catch (error) {
                console.error(`Erro ao processar instrumento ${idx + 1}:`, error);
                errosProcessamento.push(`Instrumento ${idx + 1}: ${error.message}`);
            }
        });

        // Adiciona aviso de erros no final, se houver
        if (errosProcessamento.length > 0) {
            html += `<div style="padding: 12px; background: #fff3cd; border-left: 4px solid #ffc107; border-radius: 4px; margin-top: 12px;">`;
            html += `<strong>⚠️ Avisos de processamento:</strong><br>`;
            html += errosProcessamento.join('<br>');
            html += `</div>`;
        }
    }

    return html;
}

function addUserMessage(text) {
    const div = document.createElement('div');
    div.className = 'message user';
    div.innerHTML = `
                <div class="avatar">👤</div>
                <div class="message-content">${text}</div>
            `;
    chatMessages.appendChild(div);
    scrollToBottom();
}

function addBotMessage(html) {
    const div = document.createElement('div');
    div.className = 'message bot';

    // Detecta se é HTML rico (preview de dados)
    const isRichHTML = html.includes('INSTRUMENTO') || html.includes('border-radius') || html.includes('<div style');
    const contentClass = isRichHTML ? 'message-content rich-html' : 'message-content';

    div.innerHTML = `
                <div class="avatar">🤖</div>
                <div class="${contentClass}">${html}</div>
            `;
    chatMessages.appendChild(div);
    scrollToBottom();
}

function addLoadingMessage() {
    const div = document.createElement('div');
    div.className = 'message bot';
    div.innerHTML = `
                <div class="avatar">🤖</div>
                <div class="message-content">
                    Processando
                    <div class="loading-dots">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
            `;
    chatMessages.appendChild(div);
    scrollToBottom();
}

function removeLastMessage() {
    const last = chatMessages.lastElementChild;
    if (last) last.remove();
}

function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function insertarNoBanco() {
    if (!extractedData) {
        addBotMessage('⚠️ Nenhum dado extraído disponível para inserir. Faça a extração primeiro.');
        return;
    }

    // Tenta pegar o user_id do campo oculto (injetado pelo Gocal/Widget)
    // Se não tiver, usa contexto do postMessage ou fallback
    let userId = null;
    const integrationField = document.getElementById('integrationUserId');
    if (integrationField && integrationField.value) {
        userId = integrationField.value;
    }
    if (!userId) userId = currentUserId || 1;

    addLoadingMessage();

    try {
        const response = await fetch('/inserir-banco', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                instrumentos: extractedData,
                user_id: parseInt(userId) // Envia user_id explicitamente
            })
        });

        const data = await response.json();
        removeLastMessage();

        if (data.success) {
            addBotMessage(`✅ ${data.message}`);
        } else {
            addBotMessage(`❌ Erro ao inserir: ${data.message}`);
        }
    } catch (error) {
        removeLastMessage();
        addBotMessage(`❌ Erro de comunicação: ${error.message}`);
    }
}

async function gerarSQL() {
    if (!extractedData) {
        addBotMessage('⚠️ Nenhum dado extraído!');
        return;
    }

    addLoadingMessage();

    try {
        const response = await fetch('/gerar-sql', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ instrumentos: extractedData })
        });

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `instrumentos_${Date.now()}.sql`;
        a.click();

        removeLastMessage();
        addBotMessage('✅ SQL gerado e baixado com sucesso!');
    } catch (error) {
        removeLastMessage();
        addBotMessage(`❌ Erro: ${error.message}`);
    }
}

async function baixarJSON() {
    if (!extractedData) {
        addBotMessage('⚠️ Nenhum dado extraído!');
        return;
    }

    const dataStr = JSON.stringify(extractedData, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `instrumentos_${Date.now()}.json`;
    a.click();

    addBotMessage('✅ JSON baixado com sucesso!');
}

// Toggle JSON View
let isJSONView = false;
let lastBotMessageContent = null;
let lastCommandMessage = '';

function toggleJSONView() {
    if (!extractedData) {
        addBotMessage('⚠️ Nenhum dado extraído!');
        return;
    }

    isJSONView = !isJSONView;
    const btn = document.querySelector('.action-btn[onclick="toggleJSONView()"]');

    if (isJSONView) {
        // Salva o conteúdo atual (lista)
        const lastMessage = chatMessages.lastElementChild;
        if (lastMessage && lastMessage.classList.contains('bot')) {
            lastBotMessageContent = lastMessage.querySelector('.message-content').innerHTML;
        }

        // Mostra JSON editável
        const jsonHTML = renderEditableJSON(extractedData);
        removeLastMessage();
        addBotMessage(jsonHTML);
        btn.innerHTML = '📋 Ver como Lista';
    } else {
        // Gera a lista formatada
        const listHTML = gerarVisualizacao(extractedData, lastCommandMessage);
        removeLastMessage();
        addBotMessage(listHTML);
        btn.innerHTML = '📊 Extrair Dados';
    }
}

function renderEditableJSON(data) {
    let html = '<div class="json-editor-container">';

    // Header
    html += '<div style="margin-bottom: 8px; padding-bottom: 8px; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center;">';
    html += '<div><strong style="color: var(--accent-primary); font-size: 12px;">📝 Editor de Dados</strong><span style="margin-left: 8px; font-size: 10px; color: var(--text-secondary);">Clique nos valores para editar</span></div>';
    html += '<div><button onclick="saveAllEdits()" style="padding: 4px 10px; background: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 11px;">Salvar Edições</button></div>';
    html += '</div>';

    // Conteudo: Cards para cada instrumento
    if (Array.isArray(data)) {
        html += '<div class="instrument-cards">';

        // Definição de ordem (copiada para manter consistencia)
        const topFields = ['arquivo_origem', 'identificacao', 'nome', 'fabricante', 'modelo', 'numero_serie', 'descricao', 'data_calibracao', 'validade', 'periodicidade', 'departamento', 'responsavel'];
        const bottomFields = ['grandezas', 'padroes_utilizados', 'observacoes', 'detalhes_calibracao', 'outros_dados'];

        data.forEach((inst, idx) => {
            // Titulo do card
            const titulo = inst.identificacao || inst.nome || `Instrumento #${idx + 1}`;
            const subtitulo = inst.arquivo_origem || '';
            const icon = inst.nome && inst.nome.toLowerCase().includes('paquimetro') ? '📏' : '🔬';

            html += `<div class="instrument-card" style="border: 1px solid #e0e0e0; border-radius: 6px; margin-bottom: 10px; background: #fff; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">`;

            // Header do Card
            html += `<div class="card-header" style="background: #f8f9fa; padding: 8px 12px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; cursor: pointer;" onclick="document.getElementById('body-${idx}').classList.toggle('hidden-card')">`;
            html += `<div><strong style="font-size:12px; color:#333;">${icon} ${titulo}</strong><div style="font-size:10px; color:#888;">${subtitulo}</div></div>`;
            html += `<span style="font-size: 10px; color: #666;">Show/Hide ▼</span>`;
            html += `</div>`;

            // Corpo do Card
            html += `<div id="body-${idx}" class="card-body" style="padding: 10px;">`;
            html += '<div class="json-object">';

            // Renderiza campos ordenados
            const entries = Object.entries(inst);
            entries.sort((a, b) => {
                const idxA = topFields.indexOf(a[0]);
                const idxB = topFields.indexOf(b[0]);
                const botA = bottomFields.indexOf(a[0]);
                const botB = bottomFields.indexOf(b[0]);

                if (idxA !== -1 && idxB !== -1) return idxA - idxB;
                if (idxA !== -1) return -1;
                if (idxB !== -1) return 1;
                if (botA !== -1 && botB !== -1) return botA - botB;
                if (botA !== -1) return 1;
                if (botB !== -1) return -1;
                return 0;
            });

            entries.forEach(([k, v]) => {
                // Path correto: idx.chave (ex: "0.modelo")
                html += createJSONNode(v, k, idx.toString());
            });

            html += '</div></div></div>'; // Fecha json-object, card-body, card
        });
        html += '</div>';

        // Estilo para ocultar
        html += `<style>.hidden-card { display: none; }</style>`;

    } else {
        // Fallback objeto unico
        html += createJSONNode(data, 'dados', '');
    }

    // Footer
    html += '<div style="margin-top: 10px; padding-top: 8px; border-top: 1px solid var(--border-color); display: flex; justify-content: flex-end;">';
    html += '<button onclick="saveAllEdits()" style="padding: 4px 12px; background: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 11px; font-weight: 500;">Salvar Edições</button>';
    html += '</div>';
    html += '</div>';
    return html;
}

function syntaxHighlight(json) {
    json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
        let cls = 'json-number';
        if (/^"/.test(match)) {
            if (/:$/.test(match)) {
                cls = 'json-key';
            } else {
                cls = 'json-string';
            }
        } else if (/true|false/.test(match)) {
            cls = 'json-boolean';
        } else if (/null/.test(match)) {
            cls = 'json-null';
        }
        return '<span class="' + cls + '">' + match + '</span>';
    });
}

function copyJSON() {
    if (!extractedData) return;

    const jsonString = JSON.stringify(extractedData, null, 2);
    navigator.clipboard.writeText(jsonString).then(() => {
        // Mostra feedback visual
        const btn = event.target;
        const originalText = btn.textContent;
        btn.textContent = '✅ Copiado!';
        btn.style.background = '#4CAF50';

        setTimeout(() => {
            btn.textContent = originalText;
            btn.style.background = 'var(--accent-primary)';
        }, 2000);
    });
}

function createJSONNode(value, key = '', path = '') {
    const currentPath = path ? `${path}.${key}` : key;
    let html = '';

    if (Array.isArray(value)) {
        html += '<div class="json-line">';
        html += `<button class="collapse-btn" onclick="toggleCollapse(this)">▼</button>`;
        html += `<span class="json-key">"${key}":</span>`;
        html += `<span> [ ${value.length} items ]</span>`;
        html += '</div>';
        html += '<div class="json-object">';

        value.forEach((item, idx) => {
            html += createJSONNode(item, idx, currentPath);
        });

        html += '</div>';

    } else if (typeof value === 'object' && value !== null) {
        html += '<div class="json-line">';
        html += `<button class="collapse-btn" onclick="toggleCollapse(this)">▼</button>`;
        if (key !== '') {
            html += `<span class="json-key">"${key}":</span>`;
        }
        html += '<span> { }</span>';
        html += '</div>';
        html += '<div class="json-object">';

        const entries = Object.entries(value);

        // Define ordem de prioridade
        const topFields = ['arquivo_origem', 'identificacao', 'nome', 'fabricante', 'modelo', 'numero_serie', 'descricao', 'data_calibracao', 'validade', 'periodicidade', 'departamento', 'responsavel'];
        const bottomFields = ['grandezas', 'padroes_utilizados', 'observacoes', 'detalhes_calibracao', 'outros_dados'];

        entries.sort((a, b) => {
            const keyA = a[0];
            const keyB = b[0];

            const idxA = topFields.indexOf(keyA);
            const idxB = topFields.indexOf(keyB);
            const botA = bottomFields.indexOf(keyA);
            const botB = bottomFields.indexOf(keyB);

            // 1. Se ambos estão no topo, segue a ordem da lista topFields
            if (idxA !== -1 && idxB !== -1) return idxA - idxB;
            // 2. Se apenas A está no topo, ele vem antes
            if (idxA !== -1) return -1;
            // 3. Se apenas B está no topo, ele vem antes
            if (idxB !== -1) return 1;

            // 4. Se ambos estão no fundo, segue a ordem da lista bottomFields
            if (botA !== -1 && botB !== -1) return botA - botB;
            // 5. Se apenas A está no fundo, ele vem depois
            if (botA !== -1) return 1;
            // 6. Se apenas B está no fundo, ele vem depois
            if (botB !== -1) return -1;

            // 7. O resto fica no meio (mantem ordem original ou alfabetica opcional)
            return 0;
        });

        entries.forEach(([k, v]) => {
            html += createJSONNode(v, k, currentPath);
        });

        html += '</div>';

    } else {
        html += '<div class="json-line">';
        html += '<span style="width: 20px;"></span>'; // Espaço para alinhamento
        html += `<span class="json-key">"${key}":</span>`;

        const inputType = typeof value === 'number' ? 'number' : 'text';
        const inputClass = typeof value === 'number' ? 'json-number' : 'json-string';
        const displayValue = value === null ? 'null' : value;

        html += `<input type="${inputType}" class="json-input ${inputClass}" `;
        html += `value="${displayValue}" `;
        html += `data-path="${currentPath}" data-key="${key}" `;
        html += `onchange="updateJSONValue('${currentPath}', '${key}', this.value)">`;
        html += '</div>';
    }

    return html;
}

function toggleCollapse(btn) {
    const parent = btn.parentElement.nextElementSibling;
    if (parent && parent.classList.contains('json-object')) {
        if (parent.style.display === 'none') {
            parent.style.display = 'block';
            btn.textContent = '▼';
        } else {
            parent.style.display = 'none';
            btn.textContent = '▶';
        }
    }
}

function updateJSONValue(path, key, newValue) {
    if (!extractedData) {
        console.error('❌ extractedData não existe!');
        return;
    }

    // A path gerada no DOM inclui a chave no final.
    // Ex: "instrumentos.0.identificacao" ou "0.identificacao"
    // Se extractedData é um array, e a path começa com "instrumentos", removemos.

    let parts = path.split('.').filter(p => p);

    // Corrige se houver root virtual
    if (parts.length > 0 && parts[0] === 'instrumentos' && Array.isArray(extractedData)) {
        parts.shift();
    }

    let current = extractedData;
    console.log('🔍 Navegando:', parts, 'Key:', key, 'Novo valor:', newValue);

    try {
        // Navega até o objeto pai do valor alvo
        // Loop vai até penúltimo item, pois o último é a própria chave
        for (let i = 0; i < parts.length - 1; i++) {
            let part = parts[i];

            if (Array.isArray(current)) {
                part = parseInt(part);
            }

            if (current[part] === undefined) {
                console.error('❌ Caminho inválido (undefined):', part);
                return;
            }
            current = current[part];
        }

        // Agora current deve ser o objeto que contém a propriedade a ser alterada
        // A chave é o último item de partes
        const targetKey = parts[parts.length - 1];

        // Preparação do valor final com conversão de tipos
        let finalValue = newValue;
        const trimmed = String(newValue).trim();

        if (trimmed === 'true') finalValue = true;
        else if (trimmed === 'false') finalValue = false;
        else if (trimmed === 'null') finalValue = null;
        else if (trimmed === '') finalValue = '';
        else {
            // Tenta converter para número se parecer número
            const num = parseFloat(trimmed);
            if (!isNaN(num) && String(num) === trimmed) {
                finalValue = num;
            }
        }

        // Log para debug
        console.log(`📝 Atualizando chave "${targetKey}" para:`, finalValue);

        // Atualiza o valor
        if (Array.isArray(current)) {
            current[parseInt(targetKey)] = finalValue;
        } else {
            current[targetKey] = finalValue;
        }

        console.log('💾 extractedData atualizado:', extractedData);
    } catch (error) {
        console.error('❌ Erro ao atualizar valor:', error);
    }
}

function saveAllEdits() {
    if (!extractedData) return;

    // Mostra feedback visual
    const btn = event.target;
    const originalText = btn.textContent;
    const originalBg = btn.style.background;

    btn.textContent = '✅ Salvo!';
    btn.style.background = '#2196F3';

    // Adiciona mensagem de confirmação
    addBotMessage('✅ Edições salvas! Os dados atualizados serão usados ao inserir no banco.');

    setTimeout(() => {
        btn.textContent = originalText;
        btn.style.background = originalBg;
    }, 2000);

    console.log('💾 Dados salvos:', extractedData);
}

// Nova função para solicitar extração explícita
function solicitarExtracao() {
    // Envia comando como se fosse o usuário digitando
    chatInput.value = "Extrair todos os dados em formato JSON para tabela";
    sendMessage();
}

// ==========================================
// NOVAS FUNÇÕES: Enter e Fechar Mobile
// ==========================================

// Fechar Widget (Comunica com iframe pai)
function fecharWidget() {
    window.parent.postMessage('close-widget', '*');
}
window.fecharWidget = fecharWidget;

// Mostrar botao fechar apenas no mobile
if (window.innerWidth <= 480) {
    const closeBtn = document.querySelector('.close-mobile');
    if (closeBtn) closeBtn.style.display = 'block';
}

// ==========================================
// ESTILOS DO EDITOR JSON (Injetado dinamicamente)
// ==========================================
const styleJSON = document.createElement('style');
styleJSON.innerHTML = `
    .json-editor-container { font-family: 'Consolas', 'Monaco', monospace; font-size: 11px; line-height: 1.4; color: #444; }
    .instrument-cards { display: flex; flex-direction: column; gap: 10px; }
    .instrument-card { border: 1px solid #e0e0e0; border-radius: 6px; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,0.05); overflow: hidden; }
    .card-header { background: #f8f9fa; padding: 8px 12px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; cursor: pointer; user-select: none; }
    .card-header:hover { background: #f1f3f4; }
    .card-body { padding: 10px; display: block; }
    .json-object { margin-left: 10px; border-left: 1px solid #eee; padding-left: 6px; }
    .json-line { display: flex; align-items: center; margin-bottom: 3px; }
    .json-key { color: #880088; font-weight: 600; margin-right: 4px; white-space: nowrap; font-size: 11px; }
    .json-string { color: #2a8b3c; }
    .json-number { color: #d32f2f; }
    .json-boolean { color: #0000ff; font-weight: bold; }
    .json-null { color: #888; font-style: italic; }
    .json-input { border: 1px solid #ddd; border-radius: 3px; padding: 2px 5px; font-family: inherit; font-size: 11px; color: inherit; background: #fafafa; width: 100%; max-width: 180px; transition: all 0.2s; }
    .json-input:focus { border-color: #2196F3; background: #fff; outline: none; box-shadow: 0 0 0 2px rgba(33, 150, 243, 0.1); }
    .collapse-btn { background: none; border: none; color: #888; cursor: pointer; font-size: 9px; width: 16px; padding: 0; margin-right: 2px; }

    /* Overrides de Layout do Chat (Compacto) */
    .message-content { font-size: 13px !important; padding: 8px 12px !important; }
    #chatInput { font-size: 13px !important; padding: 8px !important; min-height: 36px !important; }
    #attachBtn { width: 36px !important; height: 36px !important; padding: 0 !important; font-size: 18px !important; display: flex !important; align-items: center !important; justify-content: center !important; }
    #sendBtn { width: 36px !important; height: 36px !important; padding: 0 !important; display: flex !important; align-items: center !important; justify-content: center !important; }
    .input-area { padding: 10px !important; gap: 8px !important; }
    .avatar { width: 28px !important; height: 28px !important; font-size: 16px !important; }
`;
document.head.appendChild(styleJSON);
