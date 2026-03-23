/**
 * PROCESSAMENTO EM LOTE - JavaScript
 * Gerencia upload, processamento em background e exibição de resultados
 */

(function () {
    'use strict';

    // ============================================
    // ESTADO
    // ============================================
    let selectedFiles = [];
    let extractedResults = [];
    let currentTaskId = null;
    let pollInterval = null;

    // ============================================
    // REFERÊNCIAS DOM
    // ============================================
    const uploadZone = document.getElementById('uploadZone');
    const fileInput = document.getElementById('fileInput');
    const filesPreview = document.getElementById('filesPreview');
    const filesList = document.getElementById('filesList');
    const filesCount = document.getElementById('filesCount');
    const clearFilesBtn = document.getElementById('clearFilesBtn');
    const uploadActions = document.getElementById('uploadActions');
    const btnProcessar = document.getElementById('btnProcessar');

    const uploadSection = document.getElementById('uploadSection');
    const progressSection = document.getElementById('progressSection');
    const resultsSection = document.getElementById('resultsSection');
    const insertResult = document.getElementById('insertResult');

    const progressBarFill = document.getElementById('progressBarFill');
    const progressPercent = document.getElementById('progressPercent');
    const progressLabel = document.getElementById('progressLabel');
    const progressDetail = document.getElementById('progressDetail');
    const progressFiles = document.getElementById('progressFiles');

    const resultsStats = document.getElementById('resultsStats');
    const resultsGrid = document.getElementById('resultsGrid');
    const resultsDesc = document.getElementById('resultsDesc');
    const btnInserirBanco = document.getElementById('btnInserirBanco');
    const btnExportarJSON = document.getElementById('btnExportarJSON');
    const btnNovoLote = document.getElementById('btnNovoLote');

    // ============================================
    // UPLOAD HANDLERS
    // ============================================

    // Click na zona de upload
    uploadZone.addEventListener('click', () => fileInput.click());

    // Drag & Drop
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('dragover');
    });

    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('dragover');
    });

    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        addFiles(e.dataTransfer.files);
    });

    // File input change
    fileInput.addEventListener('change', (e) => {
        addFiles(e.target.files);
    });

    // Drag & Drop global (body)
    document.body.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('dragover');
    });

    document.body.addEventListener('dragleave', (e) => {
        if (e.clientX === 0 || e.clientY === 0) {
            uploadZone.classList.remove('dragover');
        }
    });

    document.body.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        if (e.dataTransfer && e.dataTransfer.files.length > 0) {
            addFiles(e.dataTransfer.files);
        }
    });

    // Limpar arquivos
    clearFilesBtn.addEventListener('click', () => {
        selectedFiles = [];
        renderFilesList();
        fileInput.value = '';
    });

    // ============================================
    // FILE MANAGEMENT
    // ============================================
    function addFiles(fileList) {
        const newFiles = Array.from(fileList).filter(f =>
            f.type === 'application/pdf' || f.name.toLowerCase().endsWith('.pdf')
        );

        if (newFiles.length === 0) {
            showToast('Apenas arquivos PDF são aceitos.', 'error');
            return;
        }

        // Evita duplicatas por nome
        newFiles.forEach(file => {
            if (!selectedFiles.find(f => f.name === file.name && f.size === file.size)) {
                selectedFiles.push(file);
            }
        });

        renderFilesList();
        showToast(`${newFiles.length} arquivo(s) adicionado(s).`, 'success');
    }

    function removeFile(index) {
        selectedFiles.splice(index, 1);
        renderFilesList();
    }

    function renderFilesList() {
        if (selectedFiles.length === 0) {
            filesPreview.style.display = 'none';
            uploadActions.style.display = 'none';
            return;
        }

        filesPreview.style.display = 'block';
        uploadActions.style.display = 'flex';
        filesCount.textContent = `${selectedFiles.length} arquivo(s)`;

        filesList.innerHTML = selectedFiles.map((file, idx) => `
            <div class="file-item" style="animation-delay: ${idx * 0.05}s">
                <span class="file-item-icon">📄</span>
                <div class="file-item-info">
                    <div class="file-item-name">${file.name}</div>
                    <div class="file-item-size">${formatFileSize(file.size)}</div>
                </div>
                <button class="file-item-remove" onclick="window.__removeLoteFile(${idx})" title="Remover">✖</button>
            </div>
        `).join('');
    }

    // Expor função de remoção
    window.__removeLoteFile = removeFile;

    // ============================================
    // PROCESSAMENTO
    // ============================================
    btnProcessar.addEventListener('click', startProcessing);

    async function startProcessing() {
        if (selectedFiles.length === 0) {
            showToast('Selecione ao menos um arquivo PDF.', 'error');
            return;
        }

        // Desabilita botão
        btnProcessar.disabled = true;
        btnProcessar.innerHTML = '<span class="mini-spinner"></span> Enviando...';

        // Monta FormData
        const formData = new FormData();
        selectedFiles.forEach(file => {
            formData.append('pdfs', file);
        });
        formData.append('comando', 'extrair dados estruturados em json para banco de dados');

        try {
            const response = await fetch('/upload-async', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.success && data.task_id) {
                currentTaskId = data.task_id;

                // Mostra seção de progresso
                showProgressSection();

                // Inicia polling
                startPolling(data.task_id);

                showToast('Processamento iniciado!', 'info');
                resetProcessButton();
            } else {
                showToast('Erro ao iniciar: ' + (data.message || 'Desconhecido'), 'error');
                resetProcessButton();
            }
        } catch (err) {
            console.error('Erro ao enviar:', err);
            showToast('Erro de conexão com o servidor.', 'error');
            resetProcessButton();
        }
    }

    function resetProcessButton() {
        btnProcessar.disabled = false;
        btnProcessar.innerHTML = '<span class="btn-icon">🚀</span> Iniciar Processamento';
    }

    function showProgressSection() {
        progressSection.style.display = 'block';
        progressSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

        // Renderiza lista de arquivos em progresso (usa INDICE como ID)
        progressFiles.innerHTML = selectedFiles.map((file, idx) => `
            <div class="progress-file" id="pf-${idx}">
                <span class="progress-file-icon"><span class="pending-dot"></span></span>
                <span class="progress-file-name">${file.name}</span>
                <span class="progress-file-status pending">Na fila</span>
            </div>
        `).join('');
    }

    // ============================================
    // POLLING
    // ============================================
    function startPolling(taskId) {
        pollInterval = setInterval(async () => {
            try {
                const res = await fetch(`/upload-status/${taskId}`);
                const status = await res.json();

                updateProgress(status);

                if (status.status === 'completed' || status.status === 'error') {
                    clearInterval(pollInterval);
                    pollInterval = null;

                    if (status.results && status.results.length > 0) {
                        extractedResults = status.results;
                        showResultsSection(status);
                    } else {
                        showToast('Processamento finalizado sem resultados.', 'error');
                    }
                }
            } catch (err) {
                console.error('Polling error:', err);
                clearInterval(pollInterval);
            }
        }, 1200);
    }

    function updateProgress(status) {
        const total = status.total || 1;
        const completed = status.completed || 0;
        const percent = Math.round((completed / total) * 100);

        progressBarFill.style.width = percent + '%';
        progressPercent.textContent = percent + '%';
        progressLabel.textContent = `Processando (${completed}/${total})`;

        if (status.status === 'running') {
            progressDetail.innerHTML = '<span class="mini-spinner"></span> A IA está analisando os documentos... Não feche esta página.';
        } else if (status.status === 'completed') {
            progressDetail.textContent = '✅ Processamento concluído!';
        } else {
            progressDetail.innerHTML = '<span class="mini-spinner"></span> Iniciando processamento...';
        }

        // Atualiza status individual dos arquivos (usa INDICE para match)
        if (status.files) {
            // Python dict preserva ordem de insercao (3.7+), mesma ordem do upload
            const entries = Object.entries(status.files);
            entries.forEach(([serverFilename, fileStatus], idx) => {
                const el = document.getElementById('pf-' + idx);
                if (!el) return;

                // Remove classes anteriores
                el.classList.remove('processing', 'done', 'error');

                const statusEl = el.querySelector('.progress-file-status');
                const iconEl = el.querySelector('.progress-file-icon');

                if (fileStatus === 'processing') {
                    el.classList.add('processing');
                    statusEl.className = 'progress-file-status processing';
                    statusEl.textContent = 'Processando...';
                    iconEl.innerHTML = '<span class="mini-spinner"></span>';
                } else if (fileStatus === 'done') {
                    el.classList.add('done');
                    statusEl.className = 'progress-file-status done';
                    statusEl.textContent = 'Concluído';
                    iconEl.textContent = '✅';
                } else if (fileStatus === 'error') {
                    el.classList.add('error');
                    statusEl.className = 'progress-file-status error';
                    statusEl.textContent = 'Erro';
                    iconEl.textContent = '❌';
                } else {
                    // pending - manter animação
                    statusEl.className = 'progress-file-status pending';
                    statusEl.textContent = 'Na fila';
                    iconEl.innerHTML = '<span class="pending-dot"></span>';
                }
            });
        }
    }

    // ============================================
    // RESULTADOS
    // ============================================
    function showResultsSection(status) {
        // Finaliza progresso
        progressBarFill.style.width = '100%';
        progressPercent.textContent = '100%';
        progressLabel.textContent = 'Processamento concluído!';
        progressDetail.textContent = `${extractedResults.length} instrumento(s) extraído(s) com sucesso.`;

        // Mostra seção de resultados
        resultsSection.style.display = 'block';
        resultsDesc.textContent = `${extractedResults.length} instrumento(s) extraído(s) de ${selectedFiles.length} arquivo(s).`;

        // Estatísticas
        const totalGrandezas = extractedResults.reduce((sum, inst) =>
            sum + (inst.grandezas ? inst.grandezas.length : 0), 0
        );
        const comData = extractedResults.filter(i =>
            i.data_calibracao && i.data_calibracao !== 'n/i' && i.data_calibracao !== 'N/I'
        ).length;

        resultsStats.innerHTML = `
            <div class="stat-card">
                <div class="stat-card-number">${extractedResults.length}</div>
                <div class="stat-card-label">Instrumentos</div>
            </div>
            <div class="stat-card">
                <div class="stat-card-number">${totalGrandezas}</div>
                <div class="stat-card-label">Grandezas</div>
            </div>
            <div class="stat-card">
                <div class="stat-card-number">${comData}</div>
                <div class="stat-card-label">Com Data Calib.</div>
            </div>
            <div class="stat-card">
                <div class="stat-card-number">${selectedFiles.length}</div>
                <div class="stat-card-label">PDFs Processados</div>
            </div>
        `;

        // Renderiza cards
        resultsGrid.innerHTML = extractedResults.map((inst, idx) => renderResultCard(inst, idx)).join('');

        // Scroll suave
        setTimeout(() => {
            resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 300);

        showToast(`${extractedResults.length} instrumento(s) extraído(s) com sucesso!`, 'success');
    }

    function renderResultCard(inst, idx) {
        const nome = inst.nome || inst.instrumento || 'Instrumento';
        const ident = inst.identificacao || inst.numero_certificado || 'S/N';
        const statusRaw = inst.status || 'Sem Calibração';
        const statusClass = getStatusClass(statusRaw);

        return `
        <div class="result-card" id="result-${idx}">
            <div class="result-card-header" onclick="window.__toggleResultCard(${idx})">
                <div class="result-card-title">
                    <div class="result-card-idx">${idx + 1}</div>
                    <div>
                        <div class="result-card-name">${nome}</div>
                        <div class="result-card-id">📄 ${ident}</div>
                    </div>
                </div>
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span class="result-card-status ${statusClass}">${statusRaw}</span>
                    <span class="result-card-toggle" id="toggle-${idx}">▼</span>
                </div>
            </div>
            <div class="result-card-body visible" id="body-${idx}">
                ${renderResultCardBody(inst, idx)}
            </div>
        </div>
        `;
    }

    // Mapa de criticidade dos campos
    const CAMPOS_STATUS = {
        // CRITICOS: borda vermelha se vazio
        identificacao: 'critico',
        nome: 'critico',
        periodicidade: 'critico',
        numero_certificado: 'critico',
        data_calibracao: 'critico',
        laboratorio_responsavel: 'critico',
        // IMPORTANTES: borda amarela se vazio
        numero_serie: 'importante',
        fabricante: 'importante',
        modelo: 'importante',
        data_proxima_calibracao: 'importante',
        motivo_calibracao: 'importante',
        validade: 'importante',
        // GRANDEZA critítica
        criterio_aceitacao: 'critico',
        tolerancia_processo: 'importante',
    };

    function renderResultCardBody(inst, idx) {
        let html = '';

        // ── Informações Básicas ──
        html += `
        <div class="info-block">
            <div class="info-block-title">📄 Instrumento <small style="font-weight:400;color:#888;">(todos editáveis)</small></div>
            <div class="info-grid">
                ${editField('Identificação (Tag)', inst.identificacao, 'identificacao', idx)}
                ${editField('Nome', inst.nome, 'nome', idx)}
                ${editField('Fabricante', inst.fabricante, 'fabricante', idx)}
                ${editField('Modelo', inst.modelo, 'modelo', idx)}
                ${editField('Nº Série', inst.numero_serie, 'numero_serie', idx)}
                ${editField('Periodicidade (m)', inst.periodicidade || 12, 'periodicidade', idx)}
                ${editField('Localização', inst.localizacao, 'localizacao', idx)}
                ${editField('Descrição', inst.descricao, 'descricao', idx, 'full')}
            </div>
        </div>`;

        // ── Calibração ──
        html += `
        <div class="info-block">
            <div class="info-block-title">📅 Calibração</div>
            <div class="info-grid">
                ${editField('Data Calibração', inst.data_calibracao, 'data_calibracao', idx)}
                ${editField('Data Emissão', inst.data_emissao, 'data_emissao', idx)}
                ${editField('Validade', inst.validade || inst.data_proxima_calibracao || calcValidade(inst.data_calibracao, inst.periodicidade || 12), 'validade', idx)}
                ${editField('Nº Certificado', inst.numero_certificado, 'numero_certificado', idx)}
                ${editField('Laboratório', inst.laboratorio || inst.laboratorio_responsavel, 'laboratorio_responsavel', idx)}
                ${editField('Motivo', inst.motivo_calibracao || 'Periodicidade', 'motivo_calibracao', idx)}
            </div>
        </div>`;

        // ── Informações Complementares ──
        html += `
        <div class="info-block">
            <div class="info-block-title">ℹ️ Complementares</div>
            <div class="info-grid">
                ${editField('Responsável', window.__metronUserName || '', 'responsavel', idx)}
                ${editField('Departamento', window.__metronCompanyName || '', 'departamento', idx)}
                ${editField('Criticidade', inst.criticidade, 'criticidade', idx)}
                ${editField('Regra Decisão', inst.regra_decisao, 'regra_decisao', idx)}
            </div>
        </div>`;

        return html;
    }

    // ── Handler de deleção de grandeza ──
    window.__deleteGrandeza = function (instIdx, gi) {
        if (!extractedResults[instIdx] || !extractedResults[instIdx].grandezas) return;
        extractedResults[instIdx].grandezas.splice(gi, 1);
        const el = document.getElementById(`grandeza-${instIdx}-${gi}`);
        if (el) {
            el.style.transition = 'opacity 0.2s, transform 0.2s';
            el.style.opacity = '0';
            el.style.transform = 'translateX(12px)';
            setTimeout(() => {
                el.remove();
                const bloco = document.getElementById(`grandezas-block-${instIdx}`);
                if (bloco) {
                    bloco.querySelectorAll('.grandeza-block').forEach((b, i) => {
                        const num = b.querySelector('.grandeza-num');
                        if (num) num.textContent = i + 1;
                    });
                    const c = document.getElementById(`grandezas-count-${instIdx}`);
                    if (c) c.textContent = extractedResults[instIdx].grandezas.length;
                }
            }, 220);
        }
    };


    // Campo simples (read-only)
    function infoItem(label, value) {
        const displayValue = (value && value !== 'n/i' && value !== 'N/I') ? value : '<span style="color:#ccc;">—</span>';
        return `
            <div class="info-item">
                <span class="info-label">${label}</span>
                <span class="info-value">${displayValue}</span>
            </div>`;
    }

    // Calcula validade somando periodicidade (meses) à data de calibração
    function calcValidade(dataCal, periodicidade) {
        if (!dataCal || dataCal === 'n/i') return null;
        const d = new Date(dataCal);
        if (isNaN(d.getTime())) return null;
        d.setMonth(d.getMonth() + (parseInt(periodicidade) || 12));
        return d.toISOString().split('T')[0];
    }

    // Campo editável com cor por criticidade
    function editField(label, value, fieldName, idx, span) {
        const baseField = fieldName.includes('[') ? fieldName.replace(/grandezas\[\d+\]\./, '') : fieldName;
        const criticidade = CAMPOS_STATUS[baseField] || 'normal';
        const vazio = !value || value === 'n/i' || value === 'N/I' || String(value).trim() === '';
        const displayValue = vazio ? '' : String(value);

        let borderClass = '';
        let tag = '';
        if (vazio) {
            if (criticidade === 'critico') { borderClass = 'field-critico'; tag = '<span class="field-tag-critico">⛔</span>'; }
            if (criticidade === 'importante') { borderClass = 'field-importante'; tag = '<span class="field-tag-importante">⚠️</span>'; }
        }

        // Campo grande (span full width)
        const style = span === 'full' ? 'grid-column: 1 / -1;' : '';

        return `
            <div class="info-item ${borderClass}" style="${style}">
                <span class="info-label">${label} ${tag}</span>
                <input class="info-input-edit ${borderClass}"
                       data-idx="${idx}"
                       data-field="${fieldName}"
                       value="${displayValue.replace(/"/g, '&quot;')}"
                       placeholder="${vazio && criticidade === 'critico' ? 'Obrigatório' : vazio && criticidade === 'importante' ? 'Recomendado' : ''}"
                       oninput="window.__onEditField && window.__onEditField(this)" />
            </div>`;
    }

    // Expor handler de edição de grandezas
    window.__onEditField = function (input) {
        const idx = parseInt(input.dataset.idx);
        const field = input.dataset.field;
        const val = input.value;

        // Campo simples: extractedResults[idx][campo]
        if (!field.includes('[')) {
            if (extractedResults[idx]) extractedResults[idx][field] = val;
            return;
        }

        // Campo de grandeza: grandezas[gi].subField
        const m = field.match(/grandezas\[(\d+)\]\.(.+)/);
        if (m && extractedResults[idx] && extractedResults[idx].grandezas) {
            const gi = parseInt(m[1]);
            const sub = m[2];
            if (extractedResults[idx].grandezas[gi]) {
                extractedResults[idx].grandezas[gi][sub] = val;
            }
        }
    };

    function editableInfoItem(label, value, fieldName, idx) {
        return editField(label, value, fieldName, idx);
    }

    function collectEditedValues() {
        // As edições já são aplicadas em tempo real via __onEditField
        // Este método garante que os campos sem oninput também são coletados
        document.querySelectorAll('.info-input-edit').forEach(input => {
            const idx = parseInt(input.dataset.idx);
            const field = input.dataset.field;
            if (isNaN(idx) || !field) return;
            if (!field.includes('[')) {
                if (extractedResults[idx]) extractedResults[idx][field] = input.value.trim();
            } else {
                const m = field.match(/grandezas\[(\d+)\]\.(.+)/);
                if (m && extractedResults[idx]?.grandezas?.[parseInt(m[1])]) {
                    extractedResults[idx].grandezas[parseInt(m[1])][m[2]] = input.value.trim();
                }
            }
        });
    }

    function getStatusClass(status) {
        if (!status) return 'sem-calibracao';
        const s = status.toLowerCase();
        if (s.includes('aprovado')) return 'aprovado';
        if (s.includes('pendente')) return 'pendente';
        if (s.includes('reprovado')) return 'reprovado';
        return 'sem-calibracao';
    }

    // Toggle card details
    window.__toggleResultCard = function (idx) {
        const body = document.getElementById('body-' + idx);
        const toggle = document.getElementById('toggle-' + idx);

        if (body.classList.contains('visible')) {
            body.classList.remove('visible');
            toggle.classList.remove('open');
        } else {
            body.classList.add('visible');
            toggle.classList.add('open');
        }
    };

    // ============================================
    // AÇÕES DE RESULTADO
    // ============================================

    // Inserir no Banco
    // Inserir no Banco
    btnInserirBanco.addEventListener('click', () => {
        if (extractedResults.length === 0) {
            showToast('Nenhum dado para inserir.', 'error');
            return;
        }

        // Sempre coleta edições (inclui grandezas deletadas) ANTES de validar
        collectEditedValues();

        // 1. Validação de campos obrigatórios
        const pendencias = window.validarCamposGocal ? window.validarCamposGocal(extractedResults) : [];

        if (pendencias.length > 0) {
            if (window.ValidationModal) {
                window.ValidationModal.open(extractedResults, pendencias, (updates) => {
                    // Aplica correções do modal no array principal
                    Object.keys(updates).forEach(idx => {
                        const fields = updates[idx];
                        Object.keys(fields).forEach(key => {
                            extractedResults[idx][key] = fields[key];
                        });
                    });
                    // Coleta edições dos cards mais uma vez (caso usuário tenha editado após abrir modal)
                    collectEditedValues();
                    executarInsercaoBanco();
                });
                return;
            }
        }

        // Sem pendências: insere direto
        executarInsercaoBanco();
    });

    async function executarInsercaoBanco() {
        const userId = document.getElementById('userId')?.value || 1;
        const funcionarioId = document.getElementById('funcionarioId')?.value || null;

        btnInserirBanco.disabled = true;
        btnInserirBanco.innerHTML = '<span class="mini-spinner"></span> Inserindo...';

        try {
            const response = await fetch('/inserir-banco', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    instrumentos: extractedResults,
                    user_id: parseInt(userId),
                    funcionario_id: funcionarioId,
                    task_id: currentTaskId
                })
            });

            const data = await response.json();

            insertResult.style.display = 'block';
            const card = document.getElementById('insertResultCard');

            if (data.success) {
                const calAdicionadas = data.calibracoes_adicionadas || 0;
                const detalhes = [
                    `${data.inseridos || 0} instrumento(s) novo(s)`,
                    calAdicionadas > 0 ? `${calAdicionadas} calibração(ões) adicionada(s) a instrumento(s) existente(s)` : null,
                    data.ignorados > 0 ? `${data.ignorados} duplicata(s) ignorada(s)` : null
                ].filter(Boolean).join(' • ');

                card.innerHTML = `
                    <div class="insert-success">
                        <div class="insert-success-icon">✅</div>
                        <div class="insert-success-text">
                            <h3>${data.message}</h3>
                            <p>${detalhes}</p>
                        </div>
                    </div>`;

                showToast('Dados inseridos no banco com sucesso!', 'success');
            } else {
                card.innerHTML = `
                    <div class="insert-success">
                        <div class="insert-success-icon">❌</div>
                        <div class="insert-success-text insert-error-text">
                            <h3>Erro na Inserção</h3>
                            <p>${data.message || 'Erro desconhecido'}</p>
                        </div>
                    </div>`;

                showToast('Erro ao inserir dados.', 'error');
            }

            insertResult.scrollIntoView({ behavior: 'smooth', block: 'center' });

        } catch (err) {
            showToast('Erro de conexão: ' + err.message, 'error');
        }

        btnInserirBanco.disabled = false;
        btnInserirBanco.innerHTML = '<span class="btn-icon">💾</span> Inserir Todos no Banco';
    }

    // Exportar JSON
    btnExportarJSON.addEventListener('click', () => {
        if (extractedResults.length === 0) return;

        const jsonStr = JSON.stringify(extractedResults, null, 2);
        const blob = new Blob([jsonStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `metron_lote_${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        URL.revokeObjectURL(url);

        showToast('JSON exportado com sucesso!', 'success');
    });

    // Novo Lote
    btnNovoLote.addEventListener('click', () => {
        selectedFiles = [];
        extractedResults = [];
        currentTaskId = null;

        fileInput.value = '';
        renderFilesList();
        resetProcessButton();

        progressSection.style.display = 'none';
        resultsSection.style.display = 'none';
        insertResult.style.display = 'none';

        progressBarFill.style.width = '0%';
        progressPercent.textContent = '0%';
        progressFiles.innerHTML = '';

        uploadSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

        showToast('Pronto para um novo lote!', 'info');
    });

    // ============================================
    // UTILS
    // ============================================
    function sanitizeId(str) {
        return str.replace(/[^a-zA-Z0-9]/g, '_');
    }

    function formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / 1048576).toFixed(1) + ' MB';
    }

    function showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;

        const icons = { success: '✅', error: '❌', info: 'ℹ️' };
        toast.innerHTML = `<span>${icons[type] || ''}</span> ${message}`;

        container.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'toastOut 0.3s ease forwards';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

})();
