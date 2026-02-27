/**
 * VALIDAÇÃO DE CAMPOS GOCAL
 * Valida campos críticos antes de inserir instrumentos no banco.
 */

// ============================================================
// DEFINIÇÃO DOS CAMPOS
// ============================================================
const CAMPOS_CRITICOS_INSTRUMENTO = [
    { campo: 'identificacao', label: 'Identificação (Tag)', alternativas: ['tag', 'codigo', 'patrimonio'], placeholder: 'Ex: TAG-001' },
    { campo: 'nome', label: 'Nome do Instrumento', alternativas: ['instrumento'], placeholder: 'Ex: Paquímetro Digital' },
    { campo: 'periodicidade', label: 'Periodicidade (meses)', alternativas: [], placeholder: 'Ex: 12' },
];

const CAMPOS_IMPORTANTES_INSTRUMENTO = [
    { campo: 'numero_serie', label: 'Número de Série', placeholder: 'Nº de série do instrumento' },
    { campo: 'fabricante', label: 'Fabricante', placeholder: 'Ex: Mitutoyo' },
    { campo: 'modelo', label: 'Modelo', placeholder: 'Ex: 530-104' },
];

const CAMPOS_CRITICOS_CALIBRACAO = [
    { campo: 'numero_certificado', label: 'Nº Certificado', alternativas: ['numero_calibracao'], placeholder: 'Número do certificado' },
    { campo: 'data_calibracao',         label: 'Data de Calibracao',      alternativas: [], placeholder: 'Ex: 2025-01-15' },
    { campo: 'laboratorio_responsavel', label: 'Laboratorio Responsavel', alternativas: ['laboratorio'], placeholder: 'Nome do laboratorio' },
];

const CAMPOS_IMPORTANTES_CALIBRACAO = [
    { campo: 'data_proxima_calibracao', label: 'Próxima Calibração', alternativas: ['validade'], placeholder: 'Ex: 2026-01-15' },
    { campo: 'motivo_calibracao', label: 'Motivo', alternativas: [], placeholder: 'Ex: Calibração Periódica' },
];

// ============================================================
// FUNÇÃO AUXILIAR
// ============================================================
function _temValor(inst, campo, alternativas) {
    const v = inst[campo] || (alternativas || []).map(a => inst[a]).find(Boolean);
    return v && v !== 'n/i' && v !== 'N/I' && String(v).trim() !== '';
}

// ============================================================
// FUNÇÃO DE VALIDAÇÃO PRINCIPAL
// ============================================================
window.validarCamposGocal = function (instrumentos) {
    const pendencias = [];

    instrumentos.forEach((inst, idx) => {
        const pdf = inst._pdf_filename || `Certificado ${idx + 1}`;
        const nome = inst.nome || inst.instrumento || `Instrumento ${idx + 1}`;

        const erros_inst = [];
        const avisos_inst = [];
        const erros_calib = [];
        const avisos_calib = [];

        CAMPOS_CRITICOS_INSTRUMENTO.forEach(def => {
            if (!_temValor(inst, def.campo, def.alternativas)) erros_inst.push(def);
        });
        CAMPOS_IMPORTANTES_INSTRUMENTO.forEach(def => {
            if (!_temValor(inst, def.campo, def.alternativas)) avisos_inst.push(def);
        });
        CAMPOS_CRITICOS_CALIBRACAO.forEach(def => {
            if (!_temValor(inst, def.campo, def.alternativas)) erros_calib.push(def);
        });
        CAMPOS_IMPORTANTES_CALIBRACAO.forEach(def => {
            if (!_temValor(inst, def.campo, def.alternativas)) avisos_calib.push(def);
        });

        const totalErros = erros_inst.length + erros_calib.length;
        const totalAvisos = avisos_inst.length + avisos_calib.length;

        if (totalErros > 0 || totalAvisos > 0) {
            pendencias.push({ idx, pdf, nome, erros_inst, avisos_inst, erros_calib, avisos_calib });
        }
    });

    return pendencias;
};


// ============================================================
// MODAL DE VALIDAÇÃO
// ============================================================
window.ValidationModal = (function () {
    let _callback = null;
    let _instrumentos = null;
    let _pendencias = null;
    let _updates = {};

    function _criarModal() {
        if (document.getElementById('validationModal')) return;

        const modal = document.createElement('div');
        modal.id = 'validationModal';
        modal.innerHTML = `
        <div class="vmodal-overlay" id="vmodalOverlay">
            <div class="vmodal-box">
                <div class="vmodal-header">
                    <div class="vmodal-title">
                        <span class="vmodal-icon">⚠️</span>
                        Campos Obrigatórios Pendentes
                    </div>
                    <button class="vmodal-close" onclick="window.ValidationModal.close()">✖</button>
                </div>
                <div class="vmodal-subtitle" id="vmodalSubtitle"></div>
                <div class="vmodal-body" id="vmodalBody"></div>
                <div class="vmodal-footer">
                    <button class="vmodal-btn-cancel" onclick="window.ValidationModal.close()">Cancelar</button>
                    <button class="vmodal-btn-skip" onclick="window.ValidationModal.confirm(false)">Inserir mesmo assim</button>
                    <button class="vmodal-btn-confirm" onclick="window.ValidationModal.confirm(true)">✅ Confirmar e Inserir</button>
                </div>
            </div>
        </div>`;

        // Estilos inline para não depender de CSS externo
        const style = document.createElement('style');
        style.textContent = `
        #validationModal .vmodal-overlay {
            position: fixed; inset: 0; z-index: 9999;
            background: rgba(0,0,0,0.55); backdrop-filter: blur(4px);
            display: flex; align-items: center; justify-content: center;
            padding: 16px;
        }
        #validationModal .vmodal-box {
            background: var(--bg-primary, #fff); border-radius: 16px;
            box-shadow: 0 24px 64px rgba(0,0,0,0.3);
            max-width: 720px; width: 100%; max-height: 88vh;
            display: flex; flex-direction: column;
        }
        #validationModal .vmodal-header {
            display: flex; align-items: center; justify-content: space-between;
            padding: 18px 24px 14px; border-bottom: 1px solid var(--border, #eee);
            flex-shrink: 0;
        }
        #validationModal .vmodal-title {
            font-size: 17px; font-weight: 700; color: var(--text-primary, #222);
            display: flex; align-items: center; gap: 8px;
        }
        #validationModal .vmodal-icon { font-size: 22px; }
        #validationModal .vmodal-close {
            background: none; border: none; font-size: 18px; cursor: pointer;
            color: var(--text-secondary, #999); padding: 4px 8px; border-radius: 6px;
        }
        #validationModal .vmodal-close:hover { background: #f0f0f0; }
        #validationModal .vmodal-subtitle {
            padding: 8px 24px; font-size: 13px; color: var(--text-secondary, #888);
            background: var(--bg-secondary, #f9f9f9); border-bottom: 1px solid var(--border, #eee);
            flex-shrink: 0;
        }
        #validationModal .vmodal-body {
            overflow-y: auto; padding: 16px 24px; flex: 1;
            display: flex; flex-direction: column; gap: 14px;
        }
        #validationModal .vcard {
            border: 1.5px solid var(--border, #e5e7eb); border-radius: 12px;
        }
        #validationModal .vcard-header {
            padding: 10px 14px; background: var(--bg-secondary, #f8f9fa);
            font-size: 13px; font-weight: 600; color: var(--text-primary, #333);
            display: flex; justify-content: space-between; align-items: center;
            border-radius: 11px 11px 0 0; border-bottom: 1px solid var(--border, #e5e7eb);
        }
        #validationModal .vcard.has-erros .vcard-header {
            background: #fff5f5; border-bottom-color: #fecaca;
        }
        #validationModal .vcard-pdf {
            font-size: 11px; color: var(--text-secondary, #888); font-weight: 400;
            font-family: monospace; background: rgba(0,0,0,0.05);
            padding: 2px 7px; border-radius: 4px;
        }
        #validationModal .vcard-body {
            padding: 14px 14px 12px;
            display: flex; flex-direction: column; gap: 12px;
        }
        #validationModal .vfield { display: flex; flex-direction: column; gap: 5px; }
        #validationModal .vfield-label {
            font-size: 10.5px; font-weight: 700; text-transform: uppercase;
            letter-spacing: 0.6px; display: flex; align-items: center; gap: 6px;
        }
        #validationModal .vfield-label.critico { color: #b91c1c; }
        #validationModal .vfield-label.aviso { color: #b45309; }
        #validationModal .badge-critico {
            background: #fef2f2; color: #dc2626; border: 1px solid #fecaca;
            font-size: 9px; padding: 1px 7px; border-radius: 20px;
            text-transform: none; letter-spacing: 0; font-weight: 600;
        }
        #validationModal .badge-aviso {
            background: #fffbeb; color: #d97706; border: 1px solid #fde68a;
            font-size: 9px; padding: 1px 7px; border-radius: 20px;
            text-transform: none; letter-spacing: 0; font-weight: 600;
        }
        #validationModal .vfield-input {
            border: 1.5px solid #d1d5db; border-radius: 8px; padding: 9px 12px;
            font-size: 14px; width: 100%; box-sizing: border-box;
            background: #fff; color: #1f2937; outline: none;
            transition: border 0.2s, box-shadow 0.2s;
            font-family: inherit;
        }
        #validationModal .vfield-input:focus {
            border-color: #6366f1; box-shadow: 0 0 0 3px rgba(99,102,241,0.12);
        }
        #validationModal .vfield-input.critico-border { border-color: #f87171; background: #fff8f8; }
        #validationModal .vfield-input.critico-border:focus { border-color: #dc2626; box-shadow: 0 0 0 3px rgba(220,38,38,0.1); }
        #validationModal .vfield-input[disabled] {
            background: #f3f4f6; cursor: not-allowed; color: #9ca3af;
            border-style: dashed;
        }
        #validationModal .vfield-hint {
            font-size: 11px; color: #f97316; display: flex; align-items: center; gap: 4px;
        }
        #validationModal .vmodal-footer {
            padding: 14px 24px; border-top: 1px solid var(--border, #eee);
            display: flex; justify-content: flex-end; gap: 10px; flex-shrink: 0;
        }
        #validationModal .vmodal-btn-cancel {
            padding: 9px 18px; border-radius: 8px; border: 1px solid var(--border, #ddd);
            background: none; cursor: pointer; font-size: 13px; color: var(--text-secondary, #666);
        }
        #validationModal .vmodal-btn-skip {
            padding: 9px 18px; border-radius: 8px; border: 1px solid #d97706;
            background: #fffbeb; cursor: pointer; font-size: 13px; color: #92400e; font-weight: 600;
        }
        #validationModal .vmodal-btn-confirm {
            padding: 9px 22px; border-radius: 8px; border: none;
            background: linear-gradient(135deg, #6366f1, #8b5cf6); cursor: pointer;
            font-size: 13px; color: #fff; font-weight: 700; letter-spacing: 0.2px;
        }
        #validationModal .vmodal-btn-confirm:hover { filter: brightness(1.08); }
        #validationModal .no-errors-badge {
            background: #f0fdf4; border: 1px solid #bbf7d0; color: #166534;
            border-radius: 8px; padding: 8px 12px; font-size: 12px; text-align: center;
        }
        #validationModal .vsection-title {
            padding: 8px 14px; font-size: 11px; font-weight: 700; text-transform: uppercase;
            letter-spacing: 0.7px; color: var(--text-secondary, #666);
            background: var(--bg-secondary, #f8f9fa);
            display: flex; align-items: center; gap: 5px;
        }
        `;
        document.head.appendChild(style);
        document.body.appendChild(modal);
    }

    function _renderBody() {
        const body = document.getElementById('vmodalBody');
        const subtitle = document.getElementById('vmodalSubtitle');
        _updates = {};

        const totalErros = _pendencias.reduce((n, p) => n + p.erros_inst.length + p.erros_calib.length, 0);
        const totalAvisos = _pendencias.reduce((n, p) => n + p.avisos_inst.length + p.avisos_calib.length, 0);

        subtitle.innerHTML = `
            <strong>${_pendencias.length}</strong> certificado(s) com campos pendentes
            ${totalErros > 0 ? `— <span style="color:#dc2626">${totalErros} campo(s) crítico(s)</span>` : ''}
            ${totalAvisos > 0 ? `— <span style="color:#d97706">${totalAvisos} campo(s) importante(s)</span>` : ''}
            <span style="color:#6366f1;margin-left:4px;">— preencha e clique Confirmar</span>
        `;

        body.innerHTML = _pendencias.map(p => {
            const temErro = (p.erros_inst.length + p.erros_calib.length) > 0;

            // Seção Instrumento
            const instHtml = [
                ...p.erros_inst.map(e => _renderField(p.idx, e, 'critico')),
                ...p.avisos_inst.map(a => _renderField(p.idx, a, 'aviso')),
            ].join('');

            // Seção Calibração
            const calibHtml = [
                ...p.erros_calib.map(e => _renderField(p.idx, e, 'critico')),
                ...p.avisos_calib.map(a => _renderField(p.idx, a, 'aviso')),
            ].join('');

            return `
            <div class="vcard ${temErro ? 'has-erros' : ''}">
                <div class="vcard-header">
                    <span>📄 ${p.nome}</span>
                    <span class="vcard-pdf">${p.pdf}</span>
                </div>
                ${instHtml ? `
                <div class="vsection-title">🔧 Instrumento</div>
                <div class="vcard-body">${instHtml}</div>` : ''}
                ${calibHtml ? `
                <div class="vsection-title" style="border-top:1px solid #e5e7eb;">📅 Calibração</div>
                <div class="vcard-body">${calibHtml}</div>` : ''}
            </div>`;
        }).join('');
    }

    function _renderField(idx, fieldDef, tipo) {
        const instAtual = _instrumentos[idx] || {};
        // Busca valor no campo principal ou em aliases
        let valorAtual = instAtual[fieldDef.campo] || '';
        if (!valorAtual && fieldDef.alternativas) {
            valorAtual = fieldDef.alternativas.map(a => instAtual[a]).find(Boolean) || '';
        }
        if (valorAtual === 'n/i' || valorAtual === 'N/I') valorAtual = '';

        const hint = fieldDef.placeholder || (tipo === 'critico' ? 'Campo obrigatório' : 'Recomendado preencher');

        return `
        <div class="vfield">
            <span class="vfield-label ${tipo}">
                ${fieldDef.label}
                <span class="badge-${tipo}">${tipo === 'critico' ? '⛔ CRÍTICO' : '⚠️ IMPORTANTE'}</span>
            </span>
            <input class="vfield-input ${tipo === 'critico' ? 'critico-border' : ''}"
                   data-idx="${idx}"
                   data-campo="${fieldDef.campo}"
                   value="${String(valorAtual).replace(/"/g, '&quot;')}"
                   placeholder="${hint}"
                   oninput="window.ValidationModal._onInput(this)" />
        </div>`;
    }

    return {
        open(instrumentos, pendencias, callback) {
            _instrumentos = instrumentos;
            _pendencias = pendencias;
            _callback = callback;
            _updates = {};

            _criarModal();
            _renderBody();
            document.getElementById('validationModal').style.display = 'block';
        },

        close() {
            const m = document.getElementById('validationModal');
            if (m) m.style.display = 'none';
        },

        confirm(aplicarCorrecoes) {
            if (aplicarCorrecoes) {
                Object.keys(_updates).forEach(idx => {
                    Object.keys(_updates[idx]).forEach(campo => {
                        if (_instrumentos[idx]) {
                            _instrumentos[idx][campo] = _updates[idx][campo];
                            // Aliases: laboratorio_responsavel → laboratorio e vice-versa
                            if (campo === 'laboratorio_responsavel') _instrumentos[idx]['laboratorio'] = _updates[idx][campo];
                            if (campo === 'data_proxima_calibracao') _instrumentos[idx]['validade'] = _updates[idx][campo];
                        }
                    });
                });
            }
            this.close();
            if (typeof _callback === 'function') _callback(_updates);
        },

        _onInput(input) {
            const idx = parseInt(input.dataset.idx);
            const campo = input.dataset.campo;
            if (!_updates[idx]) _updates[idx] = {};
            _updates[idx][campo] = input.value;
        }
    };
})();
