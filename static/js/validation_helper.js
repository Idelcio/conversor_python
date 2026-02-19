/**
 * HELPER DE VALIDAÇÃO GOCAL
 * Reutiliza a lógica do chat para validar campos obrigatórios antes do insert
 */

// Valida data valida no formato YYYY-MM-DD
function isValidDate(str) {
    if (!str || str === 'n/i' || str === 'N/I') return false;
    // Tenta validar como data
    try {
        const d = new Date(str);
        return !isNaN(d.getTime());
    } catch {
        return false;
    }
}

// Converte DD/MM/YYYY para YYYY-MM-DD
function normalizarData(str) {
    if (!str) return '';
    // YYYY-MM-DD já está ok
    if (/^\d{4}-\d{2}-\d{2}/.test(str)) return str;

    // Tenta DD/MM/YYYY
    const brMatch = String(str).match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
    if (brMatch) {
        return `${brMatch[3]}-${brMatch[2]}-${brMatch[1]}`;
    }
    return str;
}

// Verifica campos obrigatorios do Gocal e retorna lista de pendencias
// Mesmo código do gocal_chat.js
function validarCamposGocal(instrumentos) {
    const pendencias = [];
    instrumentos.forEach((inst, idx) => {
        const nome = inst.identificacao || inst.nome || `Instrumento ${idx + 1}`;
        const campos = [];

        if (!isValidDate(inst.data_calibracao)) {
            campos.push('data_calibracao');
        }

        // Verifica periodicidade (deve ser numero valido)
        const perio = inst.periodicidade;
        if (!perio || perio === 'n/i' || perio === 'N/I' || isNaN(parseInt(perio))) {
            campos.push('periodicidade');
        }

        // Verifica numero certificado ou identificacao
        const numCert = inst.numero_certificado || inst.identificacao;
        if (!numCert || numCert === 'n/i' || numCert === 'N/I') {
            campos.push('numero_certificado');
        }

        if (campos.length > 0) {
            pendencias.push({ idx, nome, campos });
        }
    });
    return pendencias;
}

// Gerencia o Modal de Validação
const ValidationModal = {
    overlay: document.getElementById('validationModal'),
    list: document.getElementById('validationList'),
    btnConfirm: document.getElementById('btnConfirmValidation'),
    btnCancel: document.getElementById('btnCancelValidation'),
    btnClose: document.getElementById('btnCloseValidation'),

    resolvePromise: null, // Callback de sucesso
    pendencias: [],

    init() {
        if (this.btnCancel) {
            this.btnCancel.addEventListener('click', () => this.close());
            this.btnClose.addEventListener('click', () => this.close());
            this.btnConfirm.addEventListener('click', () => this.submit());
        }
    },

    open(extractedData, pendencias, callback) {
        this.pendencias = pendencias;
        this.resolvePromise = callback;

        // Renderiza formulario
        this.list.innerHTML = pendencias.map(p => {
            const inst = extractedData[p.idx];

            let fieldsHtml = '';

            // Campo Data
            if (p.campos.includes('data_calibracao')) {
                let val = inst.data_calibracao || '';
                if (val === 'n/i' || val === 'N/I') val = '';
                // Tenta preencher com hoje se vazio
                if (!val) {
                    val = new Date().toISOString().split('T')[0];
                } else {
                    val = normalizarData(val);
                }

                fieldsHtml += `
                     <div class="validation-field">
                         <label>Data de Calibração *</label>
                         <input type="date" class="valid-input" data-field="data_calibracao" data-idx="${p.idx}" value="${val}">
                         <div class="validation-error-msg">Data é obrigatória</div>
                     </div>
                 `;
            }

            // Campo Periodicidade
            if (p.campos.includes('periodicidade')) {
                let val = inst.periodicidade;
                if (!val || val === 'n/i' || isNaN(parseInt(val))) val = 12; // Default 12 meses

                fieldsHtml += `
                     <div class="validation-field">
                         <label>Periodicidade (meses) *</label>
                         <input type="number" class="valid-input" data-field="periodicidade" data-idx="${p.idx}" value="${val}" min="1" max="120">
                         <div class="validation-error-msg">Informe um período válido</div>
                     </div>
                 `;
            }

            // Campo ID / Certificado
            if (p.campos.includes('numero_certificado')) {
                let val = '';

                fieldsHtml += `
                     <div class="validation-field">
                         <label>Número do Certificado / Identificação *</label>
                         <input type="text" class="valid-input" data-field="numero_certificado" data-idx="${p.idx}" value="${val}" placeholder="Ex: CERT-2025-001">
                         <div class="validation-error-msg">Identificação é obrigatória</div>
                     </div>
                 `;
            }

            return `
                 <div class="validation-item">
                     <div class="validation-item-title">
                         <span>📄</span> ${p.nome}
                     </div>
                     <div class="validation-fields">
                         ${fieldsHtml}
                     </div>
                 </div>
             `;
        }).join('');

        this.overlay.style.display = 'flex';
    },

    close() {
        this.overlay.style.display = 'none';
        this.pendencias = [];
        this.resolvePromise = null;
    },

    submit() {
        let isValid = true;
        const updates = {};

        // Valida todos os inputs
        const inputs = this.list.querySelectorAll('.valid-input');
        inputs.forEach(input => {
            const val = input.value.trim();
            const parent = input.parentElement;

            if (!val) {
                isValid = false;
                parent.classList.add('error');
            } else {
                parent.classList.remove('error');

                // Coleta updates
                const idx = input.dataset.idx;
                const field = input.dataset.field;

                if (!updates[idx]) updates[idx] = {};
                updates[idx][field] = val;

                // Se preencheu numero_certificado e nao tem identificacao, usa o mesmo
                if (field === 'numero_certificado') {
                    updates[idx]['identificacao'] = val;
                }
            }
        });

        if (!isValid) return; // Tem erro, não deixa salvar

        // Sucesso! Aplica updates e chama callback
        if (this.resolvePromise) {
            this.resolvePromise(updates);
        }
        this.close();
    }
};

// Inicia listeners
document.addEventListener('DOMContentLoaded', () => {
    ValidationModal.init();
});
