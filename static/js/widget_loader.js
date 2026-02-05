
(function () {
    // Configurações (URL do seu servidor Python)
    const CHAT_URL = "http://localhost:5001";

    // Pega user_id da página pai se existir (ex: input hidden ou variavel global)
    // Adapte isso conforme seu sistema Labster expõe o ID do usuário
    let userId = "";
    try {
        // Tenta pegar de uma variavel global comum em sistemas legados
        if (typeof current_user_id !== 'undefined') userId = current_user_id;
        // Ou tenta pegar de um input hidden padrao
        else if (document.getElementById('user_id')) userId = document.getElementById('user_id').value;
    } catch (e) { }

    const FULL_URL = userId ? `${CHAT_URL}/?user_id=${userId}` : CHAT_URL;

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
            width: 48px;
            height: 48px;
            border-radius: 24px;
            background: linear-gradient(135deg, #00A8E8 0%, #0077B6 100%);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            border: none;
        }

        #metron-toggle-btn:hover {
            transform: scale(1.05);
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
                height: 100%;
                max-height: 100%;
                bottom: 0;
                right: 0;
                border-radius: 0;
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
    // Ajusta fonte para o emoji ficar bonito
    btn.style.fontSize = "24px";
    btn.style.padding = "0";
    btn.innerHTML = `🤖`;

    // Iframe Container
    const frameContainer = document.createElement('div');
    frameContainer.id = 'metron-chat-frame';

    // Iframe Real (Carregado apenas no primeiro clique para performance)
    let iframeLoaded = false;

    // Ouvir mensagens do Iframe para fechar, navegar ou PEDIR contexto
    window.addEventListener('message', (e) => {
        if (e.data === 'close-widget') {
            frameContainer.classList.remove('open');
        }
        if (e.data && e.data.type === 'navigate' && e.data.url) {
            console.log("Metron Navegação:", e.data.url);
            window.location.href = e.data.url;
        }
        // Novo: Chat pedindo para escanear se tem PDF na tela
        if (e.data === 'request-pdf-url') {
            scanForPDFs();
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
                foundPdfUrl = window.location.origin + `/calibracoes/visualizar-pdf/${id}`;
                // console.log("[Metron] URL INFERIDA:", foundPdfUrl);
            }
        }

        // Se achou
        if (foundPdfUrl) {
            const iframe = document.getElementById('metron-iframe');

            // Se o chat pediu o CONTEUDO (Blob), vamos baixar e mandar
            if (returnContent && iframe && iframe.contentWindow) {
                console.log("[Metron] Baixando conteudo do PDF para o chat...", foundPdfUrl);
                fetch(foundPdfUrl)
                    .then(r => r.arrayBuffer())
                    .then(buffer => {
                        console.log("[Metron] Download OK! Enviando bytes...");
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

    // Ouvintes atualizados
    window.addEventListener('message', (e) => {
        if (e.data === 'close-widget') {
            frameContainer.classList.remove('open');
        }
        if (e.data && e.data.type === 'navigate' && e.data.url) {
            window.location.href = e.data.url;
        }
        // Novo: Chat pedindo conteudo ou url
        if (e.data === 'request-pdf-url') {
            scanForPDFs(false);
        }
        if (e.data === 'request-pdf-content') {
            scanForPDFs(true);
        }
        // Novo: Chat pedindo para preencher checklist
        if (e.data && e.data.type === 'fill_checklist' && e.data.data) {
            fillChecklistForm(e.data.data);
        }
    });

    // Funcao auxiliar para preencher o formulario na pagina pai
    function fillChecklistForm(data) {
        if (!data) return;

        // Verifica se estamos numa pagina de calibração/edição antes de tentar preencher
        const isCalibrationPage = /calibracao|edit|create/.test(window.location.href);

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

    // Polling removido
    // setInterval(scanForPDFs, 3000);

    // Tenta escanear assim que o iframe carregar
    btn.onclick = () => {
        const isOpen = frameContainer.classList.contains('open');

        if (isOpen) {
            frameContainer.classList.remove('open');
        } else {
            if (!iframeLoaded) {
                const iframe = document.createElement('iframe');
                iframe.id = 'metron-iframe';
                iframe.src = FULL_URL;
                iframe.onload = () => {
                    setTimeout(() => scanForPDFs(false), 1000); // Espera 1s para garantir
                };
                frameContainer.appendChild(iframe);
                iframeLoaded = true;
            }
            frameContainer.classList.add('open');
            // Se ja estava carregado, escaneia agora
            if (iframeLoaded) scanForPDFs(false);
        }
    };

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
