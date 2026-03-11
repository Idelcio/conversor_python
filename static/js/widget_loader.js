
(function () {
    // Detecta automaticamente a URL do Metron a partir do próprio script
    const _scriptSrc = document.currentScript ? document.currentScript.src : '';
    const CHAT_URL = _scriptSrc ? (new URL(_scriptSrc)).origin : "http://localhost:5001";

    // Pega user_id da página pai se existir (ex: input hidden ou variavel global)
    // Adapte isso conforme seu sistema Gocal expõe o ID do usuário
    // Pega user_id e funcionario_id da página pai
    let userId = "";
    let funcionarioId = "";

    try {
        // Novo padrão: current_company_id + current_employee_id
        if (typeof current_company_id !== 'undefined') {
            userId = current_company_id;
            if (typeof current_employee_id !== 'undefined' && current_employee_id) {
                funcionarioId = current_employee_id;
            }
        }
        // Fallback legado
        else if (typeof current_user_id !== 'undefined') {
            userId = current_user_id;
        }
        else if (document.getElementById('user_id')) {
            userId = document.getElementById('user_id').value;
        }
    } catch (e) { }

    let params = [];
    if (userId) params.push(`user_id=${userId}`);
    if (funcionarioId) params.push(`funcionario_id=${funcionarioId}`);

    const FULL_URL = params.length > 0 ? `${CHAT_URL}/?${params.join('&')}` : CHAT_URL;

    // Estilos do Widget
    const style = document.createElement('style');
    style.innerHTML = `
        #metron-widget-container {
            position: fixed;
            bottom: 80px; /* Mais alto para não cobrir paginação */
            right: 20px;
            z-index: 99999;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }

        #metron-toggle-btn {
            width: 56px;
            height: 56px;
            border-radius: 28px;
            background: linear-gradient(135deg, #00A8E8 0%, #0077B6 100%);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            border: none;
            padding: 0;
            overflow: hidden;
        }

        #metron-toggle-btn:hover {
            transform: scale(1.1) rotate(5deg);
        }

        #metron-toggle-btn img {
            width: 75%;
            height: 75%;
            object-fit: contain;
        }

        #metron-toggle-btn svg {
            width: 24px;
            height: 24px;
            fill: white;
        }

        #metron-chat-frame {
            position: fixed;
            bottom: 150px; /* Acompanha a subida do botão */
            right: 20px;
            width: 600px;
            height: 650px;
            max-height: 75vh;
            background: white;
            border-radius: 16px;
            box-shadow: 0 5px 40px rgba(0,0,0,0.16);
            overflow: hidden;
            display: flex;
            flex-direction: column;
            opacity: 0;
            transform: translateY(20px) scale(0.95);
            pointer-events: none;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            border: 1px solid #e1e1e1;
        }

        #metron-chat-frame.open {
            opacity: 1;
            transform: translateY(0) scale(1);
            pointer-events: all;
        }

        #metron-iframe {
            width: 100%;
            height: 100%;
            border: none;
            position: relative;
            z-index: 999999;
        }

        /* Mobile */
        @media (max-width: 480px) {
            #metron-chat-frame {
                width: 100%;
                height: 85%;
                max-height: 85vh;
                bottom: 0;
                right: 0;
                border-radius: 24px 24px 0 0;
                box-shadow: 0 -10px 40px rgba(0,0,0,0.2);
                border: none;
            }
            
            #metron-chat-frame.open {
                transform: translateY(0);
            }
            
            #metron-chat-frame:not(.open) {
                transform: translateY(100%);
            }
        }
    `;
    document.head.appendChild(style);

    // Container Principal
    const container = document.createElement('div');
    container.id = 'metron-widget-container';

    // Botão Flutuante
    const btn = document.createElement('button');
    btn.id = 'metron-toggle-btn';
    btn.innerHTML = `<img src="${CHAT_URL}/static/img/metron_face.png" alt="Metron">`;

    // Iframe Container
    const frameContainer = document.createElement('div');
    frameContainer.id = 'metron-chat-frame';

    // Iframe Real (Carregado apenas no primeiro clique para performance)
    let iframeLoaded = false;

    // Funções de Controle
    function openChat() {
        if (!iframeLoaded) {
            const iframe = document.createElement('iframe');
            iframe.id = 'metron-iframe';
            iframe.src = FULL_URL;
            iframe.onload = () => {
                setTimeout(() => {
                    scanForPDFs(false);
                    sendPageContext();
                }, 1000);
            };
            frameContainer.appendChild(iframe);
            iframeLoaded = true;
        } else {
            sendPageContext();
            scanForPDFs(false);
        }
        frameContainer.classList.add('open');
        btn.style.display = 'none'; // Esconde a bolinha
    }

    function closeChat() {
        frameContainer.classList.remove('open');
        btn.style.display = 'flex'; // Volta a bolinha
    }

    // Ouvir mensagens do Iframe
    window.addEventListener('message', (e) => {
        if (e.data === 'close-widget') {
            closeChat();
        }
        if (e.data && e.data.type === 'navigate' && e.data.url) {
            window.location.href = e.data.url;
        }
        if (e.data === 'request-pdf-url') {
            scanForPDFs(false);
        }
        if (e.data === 'request-pdf-content') {
            scanForPDFs(true);
        }
        if (e.data && e.data.type === 'fill_checklist' && e.data.data) {
            fillChecklistForm(e.data.data);
        }
        if (e.data && e.data.type === 'create_calibracao') {
            criarCalibracaoNoGocal(e.data);
        }
    });

    // Fechar ao clicar fora
    document.addEventListener('mousedown', (e) => {
        const isClickInside = container.contains(e.target);
        if (!isClickInside && frameContainer.classList.contains('open')) {
            closeChat();
        }
    });

    // Funcao para procurar PDFs na pagina pai
    function scanForPDFs(returnContent = false) {
        // console.log("[Metron] Escaneando por PDFs na pagina...");

        // Procura em iframes, embeds e objects
        const pdfElements = [
            ...document.querySelectorAll('iframe'),
            ...document.querySelectorAll('embed'),
            ...document.querySelectorAll('object')
        ];

        let foundPdfUrl = null;

        for (const el of pdfElements) {
            const src = el.src || el.data;
            const type = el.type; // Tenta pegar mimetype

            // Criterios de deteccao
            const isPdfExtension = src && src.toLowerCase().split('?')[0].endsWith('.pdf');
            const isPdfMime = type === 'application/pdf';
            const isBlob = src && src.startsWith('blob:') && type === 'application/pdf';
            const isVisualizer = src && src.includes('visualizar-pdf');

            if (isPdfExtension || isPdfMime || isBlob || isVisualizer) {
                foundPdfUrl = src;
                console.log("[Metron] PDF ENCONTRADO:", foundPdfUrl);
                break;
            }
        }

        // 2. Tenta inferir pela URL da pagina (Estrategia para Laravel/Gocal)
        if (!foundPdfUrl) {
            const path = window.location.pathname;
            // Regex para capturar ID na rota de aprovacao
            const match = path.match(/\/calibracoes\/(\d+)\/aprovar/);

            if (match && match[1]) {
                const id = match[1];
                // Busca PDF pelo Metron (Flask) que acessa o banco direto
                foundPdfUrl = CHAT_URL + `/certificado-pdf/${id}`;
                console.log("[Metron] URL do PDF via Metron:", foundPdfUrl);
            }
        }

        // Se achou
        if (foundPdfUrl) {
            const iframe = document.getElementById('metron-iframe');

            // Se o chat pediu o CONTEUDO (Blob), vamos baixar e mandar
            if (returnContent && iframe && iframe.contentWindow) {
                console.log("[Metron] Baixando conteudo do PDF para o chat...", foundPdfUrl);
                fetch(foundPdfUrl)
                    .then(r => {
                        if (!r.ok) {
                            throw new Error(`HTTP ${r.status}: PDF nao encontrado em ${foundPdfUrl}`);
                        }
                        const contentType = r.headers.get('content-type') || '';
                        if (!contentType.includes('pdf') && !contentType.includes('octet-stream')) {
                            console.warn("[Metron] Content-Type inesperado:", contentType);
                        }
                        return r.arrayBuffer();
                    })
                    .then(buffer => {
                        if (buffer.byteLength < 100) {
                            throw new Error("PDF vazio ou muito pequeno (" + buffer.byteLength + " bytes)");
                        }
                        console.log("[Metron] Download OK! Enviando", buffer.byteLength, "bytes...");
                        iframe.contentWindow.postMessage({
                            type: 'context-pdf-blob',
                            buffer: buffer,
                            url: foundPdfUrl
                        }, '*', [buffer]); // Transferable
                    })
                    .catch(err => {
                        console.error("[Metron] Erro ao baixar PDF:", err);
                        iframe.contentWindow.postMessage({ type: 'context-pdf-error', error: err.toString() }, '*');
                    });
            }
            // Se nao pediu conteudo, manda so a URL (Legacy / Aviso)
            else if (iframe && iframe.contentWindow) {
                // SEMPRE ENVIA
                iframe.contentWindow.postMessage({ type: 'context-pdf-url', url: foundPdfUrl }, '*');
            }
        } else {
            // Avisa que nao achou nada
            if (returnContent) {
                const iframe = document.getElementById('metron-iframe');
                if (iframe) iframe.contentWindow.postMessage({ type: 'context-pdf-not-found' }, '*');
            }
        }
    }


    // Funcao auxiliar para preencher o formulario na pagina pai
    function fillChecklistForm(data) {
        if (!data) return;

        // Verifica se estamos numa pagina de calibração/edição antes de tentar preencher
        const isCalibrationPage = /calibracoes|calibracao|aprovar|edit|create/.test(window.location.href);

        if (!isCalibrationPage) {
            console.log('[Metron] Checklist recebido, mas não estamos na tela de calibração. Ignorando preenchimento visual.');
            return;
        }

        console.log("[Metron] Preenchendo formulario na pagina...", data);

        // Itera sobre as chaves do JSON (1, 2, 3...)
        for (const [key, value] of Object.entries(data)) {
            // Seletor exato pelo NAME que vimos no HTML: name="checklist[1]"
            const selector = `input[name="checklist[${key}]"]`;
            const chk = document.querySelector(selector);

            if (chk) {
                // Marca ou desmarca baseado no valor true/false
                chk.checked = value;

                // Dispara eventos para garantir que frameworks (Livewire/Alpine/JS) percebam a mudanca
                chk.dispatchEvent(new Event('change', { bubbles: true }));
                chk.dispatchEvent(new Event('input', { bubbles: true }));
                chk.dispatchEvent(new Event('click', { bubbles: true }));
            } else {
                console.warn(`[Metron] Checkbox checklist[${key}] não encontrado.`);
            }
        }

        alert("✅ Checklist preenchido automaticamente pelo Metron!");
    }

    // Funcao para criar calibracao no Gocal via POST (como se fosse o humano)
    async function criarCalibracaoNoGocal(data) {
        const iframe = document.getElementById('metron-iframe');

        try {
            // 1. Pega CSRF token da pagina Gocal
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
            if (!csrfToken) {
                console.error('[Metron] CSRF token nao encontrado na pagina!');
                if (iframe) iframe.contentWindow.postMessage({ type: 'calibracao_error', message: 'CSRF token nao encontrado. Voce esta logado no Gocal?' }, '*');
                return;
            }

            // 2. Reconstroi o PDF a partir do ArrayBuffer
            let pdfFile = null;
            if (data.pdfBuffer) {
                const blob = new Blob([data.pdfBuffer], { type: 'application/pdf' });
                pdfFile = new File([blob], data.pdfName || 'certificado.pdf', { type: 'application/pdf' });
            }

            if (!pdfFile) {
                if (iframe) iframe.contentWindow.postMessage({ type: 'calibracao_error', message: 'PDF nao disponivel para upload.' }, '*');
                return;
            }

            const instrumentos = data.instrumentos || [];
            let totalCriados = 0;
            let erros = [];

            for (const inst of instrumentos) {
                // Valida data_calibracao antes de enviar
                let dataCalib = inst.data_calibracao;
                if (!dataCalib || dataCalib === 'n/i' || dataCalib === 'N/I') {
                    dataCalib = new Date().toISOString().split('T')[0];
                    console.warn('[Metron] data_calibracao ausente, usando data de hoje:', dataCalib);
                }
                // Converte DD/MM/YYYY para YYYY-MM-DD se necessario
                const brMatch = String(dataCalib).match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
                if (brMatch) {
                    dataCalib = brMatch[3] + '-' + brMatch[2] + '-' + brMatch[1];
                }

                // 3. Monta FormData identico ao formulario do Gocal
                const formData = new FormData();
                formData.append('_token', csrfToken);
                formData.append('instrumento_id', inst.instrumento_id);
                formData.append('numero_calibracao', inst.numero_calibracao || 'SN');
                formData.append('data_calibracao', dataCalib);
                formData.append('laboratorio_responsavel', inst.laboratorio_responsavel || '');
                formData.append('motivo_calibracao', inst.motivo_calibracao || 'Calibração Periódica');
                formData.append('resultado_calibracao', 'Em Revisão');
                formData.append('certificado_pdf', pdfFile);
                formData.append('acao', 'salvar');

                // 4. POST ao Gocal (usa sessao do usuario autenticado)
                console.log('[Metron] Criando calibracao para instrumento ID:', inst.instrumento_id, 'data:', dataCalib);
                const resp = await fetch('/calibracoes', {
                    method: 'POST',
                    body: formData,
                    credentials: 'same-origin',
                    redirect: 'follow'
                });

                // Laravel redireciona apos store com sucesso
                // Com redirect:'follow', resp.ok=true e resp.redirected=true
                if (resp.ok || resp.redirected) {
                    totalCriados++;
                    console.log('[Metron] Calibracao criada com sucesso!');
                } else if (resp.status === 422) {
                    // Erro de validacao do Laravel
                    let errDetail = 'Validacao falhou';
                    try {
                        const errBody = await resp.text();
                        // Tenta extrair mensagens de erro do HTML do Laravel
                        const match = errBody.match(/class="invalid-feedback[^"]*"[^>]*>([^<]+)/g);
                        if (match) {
                            errDetail = match.map(m => m.replace(/.*>/, '')).join(', ');
                        }
                    } catch (e) { }
                    console.error('[Metron] Erro validacao:', resp.status, errDetail);
                    erros.push(`Instrumento ${inst.instrumento_id}: ${errDetail}`);
                } else if (resp.status === 419) {
                    console.error('[Metron] CSRF token expirado/invalido');
                    erros.push(`Instrumento ${inst.instrumento_id}: Token CSRF expirado. Recarregue a pagina do Gocal.`);
                    break; // Nao adianta continuar com token invalido
                } else {
                    const errText = await resp.text().catch(() => 'Erro desconhecido');
                    console.error('[Metron] Erro ao criar calibracao:', resp.status, errText.substring(0, 200));
                    erros.push(`Instrumento ${inst.instrumento_id}: HTTP ${resp.status}`);
                }
            }

            // 5. Reporta resultado ao chat
            if (totalCriados > 0 && iframe) {
                iframe.contentWindow.postMessage({
                    type: 'calibracao_created',
                    message: totalCriados + ' calibracao(oes) criada(s).' + (erros.length > 0 ? ' Erros: ' + erros.join(', ') : '')
                }, '*');
            } else if (iframe) {
                iframe.contentWindow.postMessage({
                    type: 'calibracao_error',
                    message: erros.join(', ') || 'Nenhuma calibracao criada.'
                }, '*');
            }

        } catch (err) {
            console.error('[Metron] Erro geral ao criar calibracao:', err);
            if (iframe) iframe.contentWindow.postMessage({ type: 'calibracao_error', message: err.toString() }, '*');
        }
    }

    // Polling removido
    // setInterval(scanForPDFs, 3000);

    // Tenta escanear assim que o iframe carregar
    // Envia a rota atual da pagina pai para o iframe do chat
    function sendPageContext() {
        const iframe = document.getElementById('metron-iframe');
        if (!iframe || !iframe.contentWindow) return;

        iframe.contentWindow.postMessage({
            type: 'set_page_context',
            path: window.location.pathname,
            url: window.location.href,
            title: document.title,
            chat_url: CHAT_URL
        }, '*');
    }

    btn.onclick = () => {
        const isOpen = frameContainer.classList.contains('open');
        if (isOpen) {
            closeChat();
        } else {
            openChat();
        }
    };

    // Detecta navegacao SPA (pushState/popState) para atualizar contexto
    const _origPushState = history.pushState;
    history.pushState = function () {
        _origPushState.apply(this, arguments);
        setTimeout(sendPageContext, 300);
    };
    window.addEventListener('popstate', () => setTimeout(sendPageContext, 300));

    container.appendChild(frameContainer);
    container.appendChild(btn);
    document.body.appendChild(container); // Adiciona ao DOM

    // Polling Limitado a 5 tentativas (User Request) para não rodar infinito
    let scanAttempts = 0;
    const scanInterval = setInterval(() => {
        scanForPDFs(false);
        scanAttempts++;
        if (scanAttempts >= 5) {
            clearInterval(scanInterval);
            console.log("[Metron] Polling finalizado (5 tentativas).");
        }
    }, 2000);

    // Escaneia IMEDIATAMENTE ao carregar o script
    setTimeout(() => scanForPDFs(false), 1000);

})();
