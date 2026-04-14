# PRD — Trippin'
### Documento de Requisitos do Produto
**Versão:** 1.0 | **Data:** 2026-04-11 | **Status:** APROVADO

---

## 1. Objetivo

Trippin' é um aplicativo web de planejamento de viagens com IA para portfólio. O usuário informa um destino e período, e agentes de IA pesquisam e geram 3 roteiros completos (econômico, conforto, premium) incluindo voos, hospedagem e atividades.

**Problema que resolve:** Planejamento de viagens é fragmentado — o usuário precisa pesquisar voos, hotéis e atividades em plataformas separadas. Trippin' centraliza tudo e apresenta opções organizadas por orçamento.

---

## 2. Requisitos Funcionais

| ID | Requisito | Prioridade |
|----|-----------|-----------|
| RF-01 | Usuário pode se registrar com e-mail + senha (confirmação por e-mail) | Alta |
| RF-02 | Login/logout com JWT | Alta |
| RF-03 | Usuário demo pré-criado: `demo@trippin.com` / `demo123` com roteiros já gerados | Alta |
| RF-04 | Usuário informa: destino, data início, data fim, nº de viajantes | Alta |
| RF-05 | Origem fixada em São Paulo (GRU) — exibido na UI | Alta |
| RF-06 | Sistema gera 3 roteiros: econômico, conforto, premium | Alta |
| RF-07 | Progresso de geração exibido em tempo real via SSE (4 agentes) | Alta |
| RF-08 | Cada roteiro contém: voos, hospedagem e atividades dia a dia | Alta |
| RF-09 | Tela "Minhas Viagens" com histórico de solicitações do usuário | Média |
| RF-10 | Link público para compartilhar um roteiro sem login | Média |
| RF-11 | Export do roteiro como PDF | Média |
| RF-12 | Mapa visual das atividades (Leaflet + OpenStreetMap) | Média |
| RF-13 | UI em pt-BR e en com toggle de idioma (next-intl) | Alta |
| RF-14 | Banner indicando "Dados via Amadeus Sandbox" | Média |

---

## 3. Requisitos Não-Funcionais

| ID | Requisito |
|----|-----------|
| RNF-01 | Timeout de 5 minutos para tarefas dos agentes |
| RNF-02 | Rate limit: máx 5 requisições/hora por usuário no POST /api/viagens/ |
| RNF-03 | Cache Redis de 2h para respostas Amadeus (mesmo par origem-destino + datas) |
| RNF-04 | Deploy via Docker Compose em VPS |
| RNF-05 | Zero custos: usar tiers gratuitos de todas as APIs externas |

---

## 4. Casos de Uso Principais

### UC-01 — Gerar roteiro (happy path)
- **Dado:** usuário autenticado, destino válido, datas futuras, duração ≤ 30 dias
- **Quando:** submete o formulário de planejamento
- **Então:** SSE transmite progresso dos 4 agentes → 3 roteiros completos exibidos em tabs

### UC-02 — Erros de validação
- **Dado:** datas passadas, destino inválido ou duração > 30 dias
- **Quando:** submete o formulário
- **Então:** erro inline no campo correspondente, sem chamar agentes

### UC-03 — Compartilhar roteiro
- **Dado:** roteiro gerado com sucesso
- **Quando:** usuário clica em "Compartilhar"
- **Então:** URL pública `/share/{slug}` acessível sem login

### UC-04 — Acesso demo
- **Dado:** recrutador acessa a landing page
- **Quando:** clica em "Ver Demo"
- **Então:** login automático com usuário demo, roteiros pré-gerados visíveis imediatamente

### UC-05 — Timeout de agente
- **Dado:** agente demora mais de 5 minutos
- **Quando:** timeout é atingido
- **Então:** status atualizado para "falhou", mensagem exibida ao usuário via SSE

---

## 5. Fora do Escopo

- Pagamento real ou integração com sistemas de reserva
- Origem variável (fixada em São Paulo/GRU)
- App mobile nativo
- Suporte a múltiplos idiomas além de pt-BR e en
