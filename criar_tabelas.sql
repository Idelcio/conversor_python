-- Script para criar as tabelas necessárias no banco de dados

CREATE DATABASE IF NOT EXISTS instrumentos CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE instrumentos;

-- Tabela de instrumentos
CREATE TABLE IF NOT EXISTS instrumentos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    identificacao VARCHAR(255),
    nome VARCHAR(255),
    fabricante VARCHAR(255),
    modelo VARCHAR(255),
    numero_serie VARCHAR(255),
    descricao TEXT,
    periodicidade INT DEFAULT 12,
    departamento VARCHAR(255),
    responsavel VARCHAR(255),
    status VARCHAR(50) DEFAULT 'Sem Calibração',
    tipo_familia VARCHAR(255),
    serie_desenv VARCHAR(255),
    criticidade VARCHAR(100),
    motivo_calibracao VARCHAR(255),
    quantidade INT DEFAULT 1,
    user_id INT NOT NULL DEFAULT 1,
    responsavel_cadastro_id INT NOT NULL DEFAULT 1,
    data_calibracao DATE,
    data_emissao DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_identificacao (identificacao),
    INDEX idx_numero_serie (numero_serie),
    INDEX idx_status (status),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabela de grandezas
CREATE TABLE IF NOT EXISTS grandezas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    instrumento_id INT NOT NULL,
    servicos JSON,
    tolerancia_processo VARCHAR(255),
    tolerancia_simetrica BOOLEAN DEFAULT TRUE,
    unidade VARCHAR(50),
    resolucao VARCHAR(100),
    criterio_aceitacao TEXT,
    regra_decisao_id INT DEFAULT 1,
    faixa_nominal VARCHAR(255),
    classe_norma VARCHAR(100),
    classificacao VARCHAR(100),
    faixa_uso VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (instrumento_id) REFERENCES instrumentos(id) ON DELETE CASCADE,
    INDEX idx_instrumento_id (instrumento_id),
    INDEX idx_unidade (unidade)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Inserir regra de decisão padrão (caso a tabela exista)
-- CREATE TABLE IF NOT EXISTS regras_decisao (
--     id INT AUTO_INCREMENT PRIMARY KEY,
--     nome VARCHAR(255) NOT NULL,
--     padrao BOOLEAN DEFAULT FALSE
-- ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- INSERT IGNORE INTO regras_decisao (id, nome, padrao) VALUES (1, 'Padrão', TRUE);
