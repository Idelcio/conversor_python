-- ======================================================================
-- SQL de Importação de Instrumentos - Sistema Gocal
-- Gerado em: 2026-01-05 15:56:16
-- Total de instrumentos: 5
-- ======================================================================


SET FOREIGN_KEY_CHECKS=0;
SET SQL_MODE = 'NO_AUTO_VALUE_ON_ZERO';
SET AUTOCOMMIT = 0;
START TRANSACTION;


-- ======================================================================
-- Instrumento #1: ALT-001
-- =======================================================================

-- Instrumento: ALT-001 - Medidor de Altura de 0 a 300 mm, com resolução de 0,01 mm - Digital
INSERT INTO instrumentos (identificacao, nome, fabricante, modelo, numero_serie, descricao, periodicidade, departamento, responsavel, status, tipo_familia, serie_desenv, criticidade, motivo_calibracao, quantidade, user_id, responsavel_cadastro_id, created_at, updated_at)
VALUES ('ALT-001', 'Medidor de Altura de 0 a 300 mm, com resolução de 0,01 mm - Digital', 'DIGIMESS', NULL, '1804280', 'Medidor de Altura de 0 a 300 mm, com resolução de 0,01 mm - Digital', 12, 'AV UNISINOS, 950 Cristo Rei - São Leopoldo/RS', 'OTIMIZARE SISTEMAS INTELIGENTES LTDA', 'Sem Calibração', 'Medidor de Altura de 0 a 300 mm, com resolução de 0,01 mm - Digital', NULL, NULL, 'Calibração Periódica', 1, 1, 1, '2026-01-05 15:56:16', '2026-01-05 15:56:16');

SET @instrumento_id_0 = LAST_INSERT_ID();


-- Grandezas do instrumento ALT-001

INSERT INTO grandezas (instrumento_id, servicos, tolerancia_processo, tolerancia_simetrica, unidade, resolucao, criterio_aceitacao, regra_decisao_id, faixa_nominal, classe_norma, classificacao, faixa_uso, created_at, updated_at)
VALUES (@instrumento_id_0, '["QPC047 - Calibração de Micrometros Internos"]', '1804280', 1, 'mm', '0.01 mm', 'Comparação com anel liso cilíndrico / Comparação com máquina de medição linear', 1, '0 a 300 mm', NULL, NULL, NULL, '2026-01-05 15:56:16', '2026-01-05 15:56:16');


-- ======================================================================
-- Instrumento #2: CLP002
-- =======================================================================

-- Instrumento: CLP002 - Canal de Temperatura Sensor de entrada tipo: "PT100" Data de Emissão: 16/11/2020
INSERT INTO instrumentos (identificacao, nome, fabricante, modelo, numero_serie, descricao, periodicidade, departamento, responsavel, status, tipo_familia, serie_desenv, criticidade, motivo_calibracao, quantidade, user_id, responsavel_cadastro_id, created_at, updated_at)
VALUES ('CLP002', 'Canal de Temperatura Sensor de entrada tipo: "PT100" Data de Emissão: 16/11/2020', '--- Modelo:--- Nº de Série: ---', '--- Nº de Série: ---', NULL, 'Canal de Temperatura Sensor de entrada tipo: "PT100" Data de Emissão: 16/11/2020', 12, 'RS 118 Nº 12.707 KM 11, GLP Gravataí, Gravataí - RS', 'yapp brazil automotive systems', 'Sem Calibração', 'Canal de Temperatura Sensor de entrada tipo: "PT100" Data de Emissão: 16/11/2020', NULL, NULL, 'Calibração Periódica', 1, 1, 1, '2026-01-05 15:56:16', '2026-01-05 15:56:16');

SET @instrumento_id_1 = LAST_INSERT_ID();


-- Grandezas do instrumento CLP002

INSERT INTO grandezas (instrumento_id, servicos, tolerancia_processo, tolerancia_simetrica, unidade, resolucao, criterio_aceitacao, regra_decisao_id, faixa_nominal, classe_norma, classificacao, faixa_uso, created_at, updated_at)
VALUES (@instrumento_id_1, '["QPC066F -Calibração de Indicadores, Controladores e Registradores de temperatura-Entrada Termoresistência."]', '0,20', 1, '°C', '0.01 °C', 'Comparação Direta', 1, '0 a 300 °C', NULL, NULL, NULL, '2026-01-05 15:56:16', '2026-01-05 15:56:16');


-- ======================================================================
-- Instrumento #3: BL-010
-- =======================================================================

-- Instrumento: BL-010 - Balança - Digital
INSERT INTO instrumentos (identificacao, nome, fabricante, modelo, numero_serie, descricao, periodicidade, departamento, responsavel, status, tipo_familia, serie_desenv, criticidade, motivo_calibracao, quantidade, user_id, responsavel_cadastro_id, created_at, updated_at)
VALUES ('BL-010', 'Balança - Digital', 'Marte', 'AD300', '478868', 'Balança - Digital', 12, 'AV UNISINOS, 950 Cristo Rei - São Leopoldo/RS', 'OTIMIZARE SISTEMAS INTELIGENTES LTDA', 'Sem Calibração', 'Balança - Digital', NULL, NULL, 'Calibração Periódica', 1, 1, 1, '2026-01-05 15:56:16', '2026-01-05 15:56:16');

SET @instrumento_id_2 = LAST_INSERT_ID();


-- Grandezas do instrumento BL-010

INSERT INTO grandezas (instrumento_id, servicos, tolerancia_processo, tolerancia_simetrica, unidade, resolucao, criterio_aceitacao, regra_decisao_id, faixa_nominal, classe_norma, classificacao, faixa_uso, created_at, updated_at)
VALUES (@instrumento_id_2, '["QPC023 - Calibração de Balança"]', '478868', 1, NULL, NULL, 'Método de comparação com pesos padrão e massas', 1, NULL, NULL, NULL, NULL, '2026-01-05 15:56:16', '2026-01-05 15:56:16');


-- ======================================================================
-- Instrumento #4: MTBL-CJ-03-M1
-- =======================================================================

-- Instrumento: MTBL-CJ-03-M1 - CJ. PESOS PADRÃO
INSERT INTO instrumentos (identificacao, nome, fabricante, modelo, numero_serie, descricao, periodicidade, departamento, responsavel, status, tipo_familia, serie_desenv, criticidade, motivo_calibracao, quantidade, user_id, responsavel_cadastro_id, created_at, updated_at)
VALUES ('MTBL-CJ-03-M1', 'CJ. PESOS PADRÃO', 'WEIGHTECH Rua Aristides D''Ávila, 208 - Parque dos Anjos - Gravatai - RS', 'WT1000 Fone: (51)35908-639', NULL, 'CJ. PESOS PADRÃO', 12, NULL, NULL, 'Sem Calibração', 'CJ. PESOS PADRÃO', NULL, NULL, 'Calibração Periódica', 1, 1, 1, '2026-01-05 15:56:16', '2026-01-05 15:56:16');

SET @instrumento_id_3 = LAST_INSERT_ID();


-- Grandezas do instrumento MTBL-CJ-03-M1

INSERT INTO grandezas (instrumento_id, servicos, tolerancia_processo, tolerancia_simetrica, unidade, resolucao, criterio_aceitacao, regra_decisao_id, faixa_nominal, classe_norma, classificacao, faixa_uso, created_at, updated_at)
VALUES (@instrumento_id_3, '[]', '0,20', 1, NULL, NULL, 'de comparação com', 1, NULL, NULL, NULL, NULL, '2026-01-05 15:56:16', '2026-01-05 15:56:16');


-- ======================================================================
-- Instrumento #5: BLP001
-- =======================================================================

-- Instrumento: BLP001 - Conjunto de Bloco Padrão Data de Emissão do Certificado: 30/09/2025
INSERT INTO instrumentos (identificacao, nome, fabricante, modelo, numero_serie, descricao, periodicidade, departamento, responsavel, status, tipo_familia, serie_desenv, criticidade, motivo_calibracao, quantidade, user_id, responsavel_cadastro_id, created_at, updated_at)
VALUES ('BLP001', 'Conjunto de Bloco Padrão Data de Emissão do Certificado: 30/09/2025', '--- Nº de Série: --- Modelo: ---', NULL, '--- Modelo: ---', 'Conjunto de Bloco Padrão Data de Emissão do Certificado: 30/09/2025', 12, 'ROD RS-118, 12.701 - Gravataí/RS', 'YAPP BRASIL', 'Sem Calibração', 'Conjunto de Bloco Padrão Data de Emissão do Certificado: 30/09/2025', NULL, NULL, 'Calibração Periódica', 1, 1, 1, '2026-01-05 15:56:16', '2026-01-05 15:56:16');

SET @instrumento_id_4 = LAST_INSERT_ID();


-- Grandezas do instrumento BLP001

INSERT INTO grandezas (instrumento_id, servicos, tolerancia_processo, tolerancia_simetrica, unidade, resolucao, criterio_aceitacao, regra_decisao_id, faixa_nominal, classe_norma, classificacao, faixa_uso, created_at, updated_at)
VALUES (@instrumento_id_4, '["QPC080D - Medição de Peças Diversas e Componentes"]', '0,20', 1, NULL, NULL, NULL, 1, NULL, NULL, NULL, NULL, '2026-01-05 15:56:16', '2026-01-05 15:56:16');


-- Finalização
COMMIT;
SET FOREIGN_KEY_CHECKS=1;


-- Resumo:
-- [OK] 5 instrumentos inseridos
-- [OK] 5 grandezas inseridas
