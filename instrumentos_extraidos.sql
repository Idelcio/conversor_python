-- ======================================================================
-- SQL de Importação de Instrumentos - Sistema Gocal
-- Gerado em: 2026-01-20 17:30:14
-- Total de instrumentos: 3
-- ======================================================================


SET FOREIGN_KEY_CHECKS=0;
SET SQL_MODE = 'NO_AUTO_VALUE_ON_ZERO';
SET AUTOCOMMIT = 0;
START TRANSACTION;


-- ======================================================================
-- Instrumento #1: CVZ 001
-- =======================================================================

-- Instrumento: CVZ 001 - Transmissor de vazão
INSERT INTO instrumentos (identificacao, nome, fabricante, modelo, numero_serie, descricao, periodicidade, departamento, responsavel, status, tipo_familia, serie_desenv, criticidade, motivo_calibracao, quantidade, user_id, responsavel_cadastro_id, created_at, updated_at)
VALUES ('CVZ 001', 'Transmissor de vazão', NULL, NULL, NULL, 'Transmissor de vazão', 12, 'Av. Unisinos, 950 - São Leopoldo - RS', 'OTIMIZARE SISTEMAS INTELIGENTE LTDA', 'Sem Calibração', 'Transmissor de vazão', NULL, NULL, 'Calibração Periódica', 1, 1, 1, '2026-01-20 17:30:14', '2026-01-20 17:30:14');

SET @instrumento_id_0 = LAST_INSERT_ID();


-- Grandezas do instrumento CVZ 001

INSERT INTO grandezas (instrumento_id, servicos, tolerancia_processo, tolerancia_simetrica, unidade, resolucao, criterio_aceitacao, regra_decisao_id, faixa_nominal, classe_norma, classificacao, faixa_uso, created_at, updated_at)
VALUES (@instrumento_id_0, '["A calibração foi realizada conforme procedimento PSQ-VAZ.04 revisões 006, pelo método comparativo com medidor de vazão de"]', '0,20', True, NULL, NULL, 'comparativo com medidor de vazão de', 1, NULL, NULL, NULL, NULL, '2026-01-20 17:30:14', '2026-01-20 17:30:14');


-- ======================================================================
-- Instrumento #2: Braço Articulado de Medição
-- =======================================================================

-- Instrumento: Braço Articulado de Medição - Braço Articulado de Medição
INSERT INTO instrumentos (identificacao, nome, fabricante, modelo, numero_serie, descricao, periodicidade, departamento, responsavel, status, tipo_familia, serie_desenv, criticidade, motivo_calibracao, quantidade, user_id, responsavel_cadastro_id, created_at, updated_at)
VALUES ('Braço Articulado de Medição', 'Braço Articulado de Medição', 'Hexagon', 'Absolute - 7335SEI', '7335SEI-5661-FA', 'Braço Articulado de Medição', 12, 'Rodovia RS-118, KM 11, 12701', 'Yapp Brasil Fab De Tanques E Reserv Veic Automo Ltda', 'Sem Calibração', 'Braço Articulado de Medição', NULL, NULL, 'Calibração Periódica', 1, 1, 1, '2026-01-20 17:30:14', '2026-01-20 17:30:14');

SET @instrumento_id_1 = LAST_INSERT_ID();


-- Grandezas do instrumento Braço Articulado de Medição

INSERT INTO grandezas (instrumento_id, servicos, tolerancia_processo, tolerancia_simetrica, unidade, resolucao, criterio_aceitacao, regra_decisao_id, faixa_nominal, classe_norma, classificacao, faixa_uso, created_at, updated_at)
VALUES (@instrumento_id_1, '[]', '7335', True, 'mm', '0.0001 mm', 'de calibração neste certificado).', 1, NULL, NULL, NULL, NULL, '2026-01-20 17:30:14', '2026-01-20 17:30:14');


-- ======================================================================
-- Instrumento #3: GMB032/23
-- =======================================================================

-- Instrumento: GMB032/23 - Braço de Medição Articulado
INSERT INTO instrumentos (identificacao, nome, fabricante, modelo, numero_serie, descricao, periodicidade, departamento, responsavel, status, tipo_familia, serie_desenv, criticidade, motivo_calibracao, quantidade, user_id, responsavel_cadastro_id, created_at, updated_at)
VALUES ('GMB032/23', 'Braço de Medição Articulado', 'Romer França', 'Sigma 2018', 'Sigma 2018 sn 3446', 'Braço de Medição Articulado - Sigma 2018', 12, 'Unisinos, 950 - Sala 108 - Edif. Unitec II - Cristo Rei - São Leopoldo - RS', 'Otimizare Sistemas Inteligentes Ltda', 'Sem Calibração', 'Braço de Medição Articulado', NULL, NULL, 'Calibração Periódica', 1, 1, 1, '2026-01-20 17:30:14', '2026-01-20 17:30:14');

SET @instrumento_id_2 = LAST_INSERT_ID();


-- Grandezas do instrumento GMB032/23

INSERT INTO grandezas (instrumento_id, servicos, tolerancia_processo, tolerancia_simetrica, unidade, resolucao, criterio_aceitacao, regra_decisao_id, faixa_nominal, classe_norma, classificacao, faixa_uso, created_at, updated_at)
VALUES (@instrumento_id_2, '[]', '0,20', True, 'mm', '0,001 mm', NULL, 1, NULL, NULL, NULL, NULL, '2026-01-20 17:30:14', '2026-01-20 17:30:14');


-- Finalização
COMMIT;
SET FOREIGN_KEY_CHECKS=1;


-- Resumo:
-- [OK] 3 instrumentos inseridos
-- [OK] 3 grandezas inseridas
