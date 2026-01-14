-- ======================================================================
-- SQL de Importação de Instrumentos - Sistema Gocal
-- Gerado em: 2026-01-05 14:39:20
-- Total de instrumentos: 2
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
VALUES ('ALT-001', 'Medidor de Altura de 0 a 300 mm, com resolução de 0,01 mm - Digital', 'DIGIMESS', NULL, '1804280', 'Medidor de Altura de 0 a 300 mm, com resolução de 0,01 mm - Digital', 12, 'AV UNISINOS, 950 Cristo Rei - São Leopoldo/RS', 'OTIMIZARE SISTEMAS INTELIGENTES LTDA', 'Sem Calibração', 'Medidor de Altura de 0 a 300 mm, com resolução de 0,01 mm - Digital', NULL, NULL, 'Calibração Periódica', 1, 1, 1, '2026-01-05 14:39:20', '2026-01-05 14:39:20');

SET @instrumento_id_0 = LAST_INSERT_ID();


-- Grandezas do instrumento ALT-001

INSERT INTO grandezas (instrumento_id, servicos, tolerancia_processo, tolerancia_simetrica, unidade, resolucao, criterio_aceitacao, regra_decisao_id, faixa_nominal, classe_norma, classificacao, faixa_uso, created_at, updated_at)
VALUES (@instrumento_id_0, '["QPC047 - Calibração de Micrometros Internos"]', '1804280', True, 'mm', '0.01 mm', 'Comparação com anel liso cilíndrico / Comparação com máquina de medição linear', 1, '0 a 300 mm', NULL, NULL, NULL, '2026-01-05 14:39:20', '2026-01-05 14:39:20');


-- ======================================================================
-- Instrumento #2: CLP002 Nº Certificado: 36839/20 Data de Calibração: 09/11/2020
-- =======================================================================

-- Instrumento: CLP002 Nº Certificado: 36839/20 Data de Calibração: 09/11/2020 - Canal de Temperatura Sensor de entrada tipo: "PT100" Data de Emissão: 16/11/2020
INSERT INTO instrumentos (identificacao, nome, fabricante, modelo, numero_serie, descricao, periodicidade, departamento, responsavel, status, tipo_familia, serie_desenv, criticidade, motivo_calibracao, quantidade, user_id, responsavel_cadastro_id, created_at, updated_at)
VALUES ('CLP002 Nº Certificado: 36839/20 Data de Calibração: 09/11/2020', 'Canal de Temperatura Sensor de entrada tipo: "PT100" Data de Emissão: 16/11/2020', '--- Modelo:--- Nº de Série: ---', '--- Nº de Série: ---', NULL, 'Canal de Temperatura Sensor de entrada tipo: "PT100" Data de Emissão: 16/11/2020', 12, 'RS 118 Nº 12.707 KM 11, GLP Gravataí, Gravataí - RS', 'yapp brazil automotive systems', 'Sem Calibração', 'Canal de Temperatura Sensor de entrada tipo: "PT100" Data de Emissão: 16/11/2020', NULL, NULL, 'Calibração Periódica', 1, 1, 1, '2026-01-05 14:39:20', '2026-01-05 14:39:20');

SET @instrumento_id_1 = LAST_INSERT_ID();


-- Grandezas do instrumento CLP002 Nº Certificado: 36839/20 Data de Calibração: 09/11/2020

INSERT INTO grandezas (instrumento_id, servicos, tolerancia_processo, tolerancia_simetrica, unidade, resolucao, criterio_aceitacao, regra_decisao_id, faixa_nominal, classe_norma, classificacao, faixa_uso, created_at, updated_at)
VALUES (@instrumento_id_1, '["QPC066F -Calibração de Indicadores, Controladores e Registradores de temperatura-Entrada Termoresistência."]', '0,20', True, '°C', '0.01 °C', 'Comparação Direta', 1, '0 a 300 °C', NULL, NULL, NULL, '2026-01-05 14:39:20', '2026-01-05 14:39:20');


-- Finalização
COMMIT;
SET FOREIGN_KEY_CHECKS=1;


-- Resumo:
-- [OK] 2 instrumentos inseridos
-- [OK] 2 grandezas inseridas
