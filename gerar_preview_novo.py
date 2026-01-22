def gerar_preview(instrumentos):
    """Gera um preview COMPLETO e FORMATADO dos dados extraídos em HTML"""
    if not instrumentos:
        return "<p>Nenhum instrumento encontrado</p>"

    html_parts = []
    
    for idx, inst in enumerate(instrumentos, 1):
        # Cabeçalho do instrumento
        # Trata arquivo_origem que pode ser string ou lista
        arquivo_origem = inst.get('arquivo_origem', 'n/i')
        if isinstance(arquivo_origem, list):
            # Se for lista, pega o primeiro elemento
            arquivo_nome = arquivo_origem[0].split('/')[-1].split('\\\\')[-1] if arquivo_origem else 'n/i'
        elif isinstance(arquivo_origem, str):
            # Se for string, processa normalmente
            arquivo_nome = arquivo_origem.split('/')[-1].split('\\\\')[-1]
        else:
            arquivo_nome = 'n/i'
        
        html_parts.append(f"""
        <div style="margin: 20px 0; padding: 20px; background: #f5f5f5; border-radius: 8px; border-left: 4px solid #2196F3;">
            <h3 style="margin: 0 0 15px 0; color: #1976D2;">
                📄 INSTRUMENTO {idx}
            </h3>
            <p style="margin: 0; color: #666; font-size: 0.9em;">
                Arquivo: {arquivo_nome}
            </p>
        </div>
        """)
        
        # Container principal
        html_parts.append('<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 20px 0;">')
        
        # IDENTIFICAÇÃO E DADOS BÁSICOS
        html_parts.append(f"""
        <div style="background: white; padding: 15px; border-radius: 6px; border: 1px solid #e0e0e0;">
            <h4 style="margin: 0 0 10px 0; color: #424242; border-bottom: 2px solid #4CAF50; padding-bottom: 5px;">
                🔖 Identificação
            </h4>
            <table style="width: 100%; font-size: 0.9em;">
                <tr><td style="padding: 4px 0; color: #666;">Tag:</td><td style="padding: 4px 0;"><strong>{inst.get('identificacao', 'n/i')}</strong></td></tr>
                <tr><td style="padding: 4px 0; color: #666;">Nome:</td><td style="padding: 4px 0;">{inst.get('nome', 'n/i')}</td></tr>
                <tr><td style="padding: 4px 0; color: #666;">Descrição:</td><td style="padding: 4px 0;">{inst.get('descricao', 'n/i')}</td></tr>
                <tr><td style="padding: 4px 0; color: #666;">Tipo/Família:</td><td style="padding: 4px 0;">{inst.get('tipo_familia', 'n/i')}</td></tr>
            </table>
        </div>
        """)
        
        # FABRICANTE E MODELO
        html_parts.append(f"""
        <div style="background: white; padding: 15px; border-radius: 6px; border: 1px solid #e0e0e0;">
            <h4 style="margin: 0 0 10px 0; color: #424242; border-bottom: 2px solid #FF9800; padding-bottom: 5px;">
                🏭 Fabricante e Modelo
            </h4>
            <table style="width: 100%; font-size: 0.9em;">
                <tr><td style="padding: 4px 0; color: #666;">Fabricante:</td><td style="padding: 4px 0;"><strong>{inst.get('fabricante', 'n/i')}</strong></td></tr>
                <tr><td style="padding: 4px 0; color: #666;">Modelo:</td><td style="padding: 4px 0;"><strong>{inst.get('modelo', 'n/i')}</strong></td></tr>
                <tr><td style="padding: 4px 0; color: #666;">Nº Série:</td><td style="padding: 4px 0;">{inst.get('numero_serie', 'n/i')}</td></tr>
            </table>
        </div>
        """)
        
        # RESPONSÁVEL E LOCALIZAÇÃO
        html_parts.append(f"""
        <div style="background: white; padding: 15px; border-radius: 6px; border: 1px solid #e0e0e0;">
            <h4 style="margin: 0 0 10px 0; color: #424242; border-bottom: 2px solid #9C27B0; padding-bottom: 5px;">
                👤 Responsável
            </h4>
            <table style="width: 100%; font-size: 0.9em;">
                <tr><td style="padding: 4px 0; color: #666;">Cliente:</td><td style="padding: 4px 0;">{inst.get('responsavel', 'n/i')}</td></tr>
                <tr><td style="padding: 4px 0; color: #666;">Departamento:</td><td style="padding: 4px 0;">{inst.get('departamento', 'n/i')}</td></tr>
            </table>
        </div>
        """)
        
        # DATAS E PERIODICIDADE
        html_parts.append(f"""
        <div style="background: white; padding: 15px; border-radius: 6px; border: 1px solid #e0e0e0;">
            <h4 style="margin: 0 0 10px 0; color: #424242; border-bottom: 2px solid #2196F3; padding-bottom: 5px;">
                📅 Datas
            </h4>
            <table style="width: 100%; font-size: 0.9em;">
                <tr><td style="padding: 4px 0; color: #666;">Calibração:</td><td style="padding: 4px 0;">{inst.get('data_calibracao') or 'n/i'}</td></tr>
                <tr><td style="padding: 4px 0; color: #666;">Emissão:</td><td style="padding: 4px 0;">{inst.get('data_emissao') or 'n/i'}</td></tr>
                <tr><td style="padding: 4px 0; color: #666;">Periodicidade:</td><td style="padding: 4px 0;">{inst.get('periodicidade', 'n/i')} meses</td></tr>
            </table>
        </div>
        """)
        
        html_parts.append('</div>')  # Fecha grid
        
        # STATUS E CONTROLE (largura total)
        html_parts.append(f"""
        <div style="background: white; padding: 15px; border-radius: 6px; border: 1px solid #e0e0e0; margin: 15px 0;">
            <h4 style="margin: 0 0 10px 0; color: #424242; border-bottom: 2px solid #607D8B; padding-bottom: 5px;">
                ⚙️ Status e Controle
            </h4>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; font-size: 0.9em;">
                <div><span style="color: #666;">Status:</span> <strong>{inst.get('status', 'n/i')}</strong></div>
                <div><span style="color: #666;">Quantidade:</span> {inst.get('quantidade', 'n/i')}</div>
                <div><span style="color: #666;">Motivo:</span> {inst.get('motivo_calibracao', 'n/i')}</div>
                <div><span style="color: #666;">Criticidade:</span> {inst.get('criticidade') or 'n/i'}</div>
                <div><span style="color: #666;">Série Desenv.:</span> {inst.get('serie_desenv') or 'n/i'}</div>
            </div>
        </div>
        """)
        
        # GRANDEZAS
        grandezas = inst.get('grandezas', [])
        if grandezas:
            html_parts.append(f"""
            <div style="background: white; padding: 15px; border-radius: 6px; border: 1px solid #e0e0e0; margin: 15px 0;">
                <h4 style="margin: 0 0 10px 0; color: #424242; border-bottom: 2px solid #E91E63; padding-bottom: 5px;">
                    📊 Grandezas ({len(grandezas)})
                </h4>
            """)
            
            for g_idx, grandeza in enumerate(grandezas, 1):
                servicos = grandeza.get('servicos', [])
                servicos_texto = ', '.join(map(str, servicos[:2])) if servicos else 'n/i'
                if len(servicos) > 2:
                    servicos_texto += f' ... (+{len(servicos)-2})'
                
                html_parts.append(f"""
                <div style="background: #f9f9f9; padding: 12px; margin: 10px 0; border-radius: 4px; border-left: 3px solid #E91E63;">
                    <strong style="color: #C2185B;">Grandeza {g_idx}</strong>
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; margin-top: 8px; font-size: 0.85em;">
                        <div><span style="color: #666;">Unidade:</span> {grandeza.get('unidade', 'n/i')}</div>
                        <div><span style="color: #666;">Faixa Nominal:</span> {grandeza.get('faixa_nominal', 'n/i')}</div>
                        <div><span style="color: #666;">Tolerância:</span> {grandeza.get('tolerancia_processo', 'n/i')}</div>
                        <div><span style="color: #666;">Resolução:</span> {grandeza.get('resolucao', 'n/i')}</div>
                        <div style="grid-column: 1 / -1;"><span style="color: #666;">Critério:</span> {grandeza.get('criterio_aceitacao', 'n/i')}</div>
                        <div style="grid-column: 1 / -1;"><span style="color: #666;">Serviços:</span> {servicos_texto}</div>
                    </div>
                </div>
                """)
            
            html_parts.append('</div>')

    # Botão de inserir no banco (após todos os instrumentos)
    html_parts.append(f"""
    <div style="margin: 30px 0; text-align: center; padding: 20px; background: white; border-radius: 8px; border: 2px dashed #4CAF50;">
        <p style="margin: 0 0 15px 0; color: #666; font-size: 0.95em;">
            ✅ Dados prontos para inserir no banco de dados
        </p>
        <button onclick="inserirDadosNoBanco()" style="
            background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
            color: white;
            border: none;
            padding: 15px 40px;
            border-radius: 8px;
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
            transition: all 0.3s;
        " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 12px rgba(0,0,0,0.3)'" 
           onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 6px rgba(0,0,0,0.2)'">
            💾 Inserir no Banco de Dados
        </button>
    </div>
    
    <script>
    function inserirDadosNoBanco() {{
        // Desabilita o botão para evitar cliques duplos
        event.target.disabled = true;
        event.target.textContent = '⏳ Inserindo...';
        event.target.style.background = '#999';
        
        // Faz a requisição para inserir no banco
        fetch('/inserir-banco', {{
            method: 'POST',
            headers: {{
                'Content-Type': 'application/json'
            }},
            body: JSON.stringify({{
                user_id: 1  // Pode ser customizado
            }})
        }})
        .then(response => response.json())
        .then(data => {{
            if (data.success) {{
                // Mostra mensagem de sucesso
                event.target.textContent = '✅ ' + data.message;
                event.target.style.background = '#4CAF50';
                
                // Recarrega a página após 2 segundos
                setTimeout(() => {{
                    window.location.reload();
                }}, 2000);
            }} else {{
                // Mostra mensagem de erro
                event.target.textContent = '❌ Erro: ' + data.message;
                event.target.style.background = '#f44336';
                event.target.disabled = false;
            }}
        }})
        .catch(error => {{
            event.target.textContent = '❌ Erro ao inserir';
            event.target.style.background = '#f44336';
            event.target.disabled = false;
            console.error('Erro:', error);
        }});
    }}
    </script>
    """)

    return ''.join(html_parts)
