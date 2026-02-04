let uploadedFiles = [];
let extractedData = null;

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
    renderFilesList();
    addBotMessage(`✅ ${files.length} arquivo(s) carregado(s)! O que você gostaria de fazer?`);
}

function renderFilesList() {
    if (uploadedFiles.length === 0) {
        filesList.style.display = 'none';
        return;
    }

    filesList.style.display = 'block';
    filesContainer.innerHTML = uploadedFiles.map((file, idx) => {
        const sizeKB = (file.size / 1024).toFixed(1);
        // Sanitiza nome para usar como ID (remove pontos e espacos)
        const fileId = 'file-' + file.name.replace(/[^a-zA-Z0-9]/g, '');

        return `
                    <div class="file-item" id="${fileId}" style="position: relative; overflow: hidden;">
                        <div class="file-icon">📄</div>
                        <div class="file-info">
                            <div class="file-name" title="${file.name}">${file.name}</div>
                            <div class="file-size">${sizeKB} KB</div>
                        </div>
                        <div class="status-icon" id="status-${fileId}"></div>
                        <button class="file-remove" onclick="removeFile(${idx})" title="Remover">×</button>
                        <div class="file-progress" style="position: absolute; bottom: 0; left: 0; width: 100%; height: 4px; background: rgba(0,0,0,0.05); display: none;">
                            <div class="file-progress-bar" style="height: 100%; width: 0%; background: #4CAF50; transition: width 0.5s;"></div>
                        </div>
                    </div>
                `;
    }).join('');
}

function removeFile(idx) {
    uploadedFiles.splice(idx, 1);
    renderFilesList();
    if (uploadedFiles.length === 0) {
        addBotMessage('Todos os arquivos foram removidos. Sessão limpa.');

        // Limpa cache se remover arquivos manualmente
        extractedData = null;
        fetch('/limpar-cache', { method: 'POST' });
    }
}

// Chat handlers
sendBtn.addEventListener('click', sendMessage);
chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

async function sendMessage() {
    const message = chatInput.value.trim();
    // Se tem arquivos, message pode ser vazio (comando implícito)
    if (!message && uploadedFiles.length === 0) return;

    if (message) addUserMessage(message);
    chatInput.value = '';
    chatInput.style.height = 'auto';

    addLoadingMessage();

    try {
        if (uploadedFiles.length > 0) {
            // MODO ASYNC (Upload com Progresso)

            // Mostra barras de progresso vazias
            document.querySelectorAll('.file-progress').forEach(el => el.style.display = 'block');
            document.querySelectorAll('.file-remove').forEach(el => el.style.display = 'none'); // Trava remoção

            const formData = new FormData();
            uploadedFiles.forEach(file => {
                formData.append('pdfs', file);
            });

            if (message) {
                formData.append('comando', message);
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

                    if (extractedData.length > 0 && extractedData[0].is_text_response) {
                        if (actionBar) actionBar.classList.remove('show');

                        extractedData.forEach((inst) => {
                            // Formata Markdown básico para HTML (quebras de linha e negrito)
                            let text = inst.descricao || "";
                            text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>'); // Negrito
                            text = text.replace(/\n/g, '<br>'); // Quebra de linha
                            addBotMessage(text);
                        });
                    } else {
                        if (actionBar) actionBar.classList.add('show');
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
        addBotMessage('⚠️ Nenhum dado extraído!');
        return;
    }

    const userId = prompt('Digite o ID do usuário (user_id):');
    if (!userId) return;

    addLoadingMessage();

    try {
        const response = await fetch('/inserir-banco', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                instrumentos: extractedData,
                user_id: parseInt(userId)
            })
        });

        const data = await response.json();
        removeLastMessage();

        if (data.success) {
            addBotMessage(`✅ ${data.message}`);
        } else {
            addBotMessage(`❌ ${data.message}`);
        }
    } catch (error) {
        removeLastMessage();
        addBotMessage(`❌ Erro: ${error.message}`);
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
        btn.textContent = '📋 Ver como Lista';
    } else {
        // Gera a lista formatada
        const listHTML = gerarVisualizacao(extractedData, lastCommandMessage);
        removeLastMessage();
        addBotMessage(listHTML);
        btn.textContent = '📝 Ver como JSON';
    }
}

function renderEditableJSON(data) {
    let html = '<div class="json-editor-container">';

    // Header
    html += '<div style="margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center;">';
    html += '<div><strong style="color: var(--accent-primary);">📝 Editor de Dados</strong><span style="margin-left: 12px; font-size: 12px; color: var(--text-secondary);">Clique nos valores para editar</span></div>';
    html += '<div><button onclick="saveAllEdits()" style="padding: 6px 12px; background: #4CAF50; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 12px;">Salvar Edições</button></div>';
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

            html += `<div class="instrument-card" style="border: 1px solid #e0e0e0; border-radius: 8px; margin-bottom: 16px; background: #fff; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">`;

            // Header do Card
            html += `<div class="card-header" style="background: #f8f9fa; padding: 12px 16px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; cursor: pointer;" onclick="document.getElementById('body-${idx}').classList.toggle('hidden-card')">`;
            html += `<div><strong style="font-size:14px; color:#333;">${icon} ${titulo}</strong><div style="font-size:11px; color:#888;">${subtitulo}</div></div>`;
            html += `<span style="font-size: 12px; color: #666;">Show/Hide ▼</span>`;
            html += `</div>`;

            // Corpo do Card
            html += `<div id="body-${idx}" class="card-body" style="padding: 15px;">`;
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
    html += '<div style="margin-top: 16px; padding-top: 12px; border-top: 1px solid var(--border-color); display: flex; justify-content: flex-end;">';
    html += '<button onclick="saveAllEdits()" style="padding: 8px 16px; background: #4CAF50; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 500;">Salvar Edições</button>';
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