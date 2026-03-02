# CLAUDE.md — Instruções para o Assistente

## Leitura obrigatória ao iniciar

Sempre ler os arquivos em `.agents/workflows/` **antes de qualquer tarefa**.
Eles contêm os padrões, fluxos e regras deste projeto.

Arquivos principais:
- `.agents/workflows/servidor.md` — como ligar, verificar e parar o servidor
- `.agents/workflows/desenvolvimento.md` — regras de desenvolvimento seguro

---

## Projeto

**Metron** — Assistente de extração de certificados de calibração com GPT-4o Vision.
Integrado ao sistema **Gocal** (Laravel) via widget iframe.

- Servidor Flask na porta **5001**
- Banco MySQL: `laboratorios` (mesmo banco do Gocal)
- Frontend: widget embeddado via `widget_loader.js`

---

## Preferências

- Alterações **somente local** por padrão — nunca subir para o VPS automaticamente
- Usuário decide quando e como fazer o deploy
