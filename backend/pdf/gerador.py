"""
Gerador de PDF de roteiros — ReportLab

Por que ReportLab?
- Biblioteca Python madura (desde 1998) para geração de PDF programático
- Não depende de browser, Chromium ou display — roda puro no servidor
- API de baixo nível com platypus (flowables) para controle fino do layout
- Suficiente para o nível de formatação necessário no portfólio

Por que não WeasyPrint ou Puppeteer?
- WeasyPrint requer dependências de sistema (Cairo, Pango) — complicado em Docker Alpine
- Puppeteer/Playwright adiciona ~200MB à imagem Docker só para PDF
- ReportLab é Python puro, sem dependências de sistema

Estrutura do PDF gerado:
  1. Cabeçalho (título + metadados da viagem)
  2. Linha divisória colorida (cor varia por nível: azul/índigo/violeta)
  3. Resumo do roteiro (texto gerado pelo GPT-4o-mini)
  4. Custo total estimado
  5. Tabela de voos (companhia, partida, chegada, preço)
  6. Hospedagem (nome, tipo, avaliação, preço/noite)
  7. Atividades dia a dia
  8. Rodapé com créditos
"""
import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from viagens.modelos import NivelRoteiro, Roteiro, SolicitacaoViagem

# Cor principal de cada nível — aplicada no cabeçalho, títulos de seção e tabela de voos
CORES = {
    NivelRoteiro.economico: colors.HexColor("#1d4ed8"),  # azul
    NivelRoteiro.conforto:  colors.HexColor("#4338ca"),  # índigo
    NivelRoteiro.premium:   colors.HexColor("#6d28d9"),  # violeta
}

LABELS_NIVEL = {
    NivelRoteiro.economico: "Econômico",
    NivelRoteiro.conforto:  "Conforto",
    NivelRoteiro.premium:   "Premium",
}


def gerar_pdf_roteiro(solicitacao: SolicitacaoViagem, roteiro: Roteiro) -> bytes:
    """
    Gera o PDF completo de um roteiro e retorna os bytes para download.

    Usa io.BytesIO como buffer em memória — mais simples do que escrever
    em disco e depois ler, especialmente em ambientes containerizados.

    SimpleDocTemplate cuida da paginação automática — os flowables são
    distribuídos pelas páginas conforme o espaço disponível.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    estilos = getSampleStyleSheet()
    cor_principal = CORES[roteiro.nivel]

    # Estilos customizados — herdamos do base e sobrescrevemos propriedades específicas
    estilo_titulo = ParagraphStyle(
        "Titulo",
        parent=estilos["Heading1"],
        textColor=cor_principal,
        fontSize=22,
        spaceAfter=4,
    )
    estilo_subtitulo = ParagraphStyle(
        "Subtitulo",
        parent=estilos["Normal"],
        textColor=colors.HexColor("#6b7280"),
        fontSize=11,
        spaceAfter=16,
    )
    estilo_secao = ParagraphStyle(
        "Secao",
        parent=estilos["Heading2"],
        textColor=cor_principal,
        fontSize=14,
        spaceBefore=16,
        spaceAfter=8,
    )
    estilo_normal = estilos["Normal"]
    estilo_normal.fontSize = 10

    # Lista de flowables — ReportLab os distribui pelas páginas automaticamente
    conteudo = []

    # ── Cabeçalho ─────────────────────────────────────────────────────────────
    conteudo.append(Paragraph("Trippin' — Seu Roteiro de Viagem", estilo_titulo))
    conteudo.append(
        Paragraph(
            f"{solicitacao.destino} · "
            f"{solicitacao.data_inicio.strftime('%d/%m/%Y')} a {solicitacao.data_fim.strftime('%d/%m/%Y')} · "
            f"{solicitacao.num_viajantes} viajante(s) · "
            f"Perfil: <b>{LABELS_NIVEL[roteiro.nivel]}</b>",
            estilo_subtitulo,
        )
    )
    conteudo.append(HRFlowable(width="100%", color=cor_principal, thickness=1))
    conteudo.append(Spacer(1, 0.3 * cm))

    # ── Resumo ────────────────────────────────────────────────────────────────
    if roteiro.resumo:
        conteudo.append(Paragraph("Sobre este roteiro", estilo_secao))
        conteudo.append(Paragraph(roteiro.resumo, estilo_normal))

    # ── Custo Total ───────────────────────────────────────────────────────────
    if roteiro.custo_total_estimado:
        conteudo.append(Spacer(1, 0.3 * cm))
        # Formatação brasileira: 1.234,56 — replace em cadeia para evitar regex
        custo_fmt = f"R$ {float(roteiro.custo_total_estimado):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        conteudo.append(
            Paragraph(f"<b>Custo total estimado:</b> {custo_fmt}", estilo_normal)
        )

    # ── Voos ──────────────────────────────────────────────────────────────────
    if roteiro.voos:
        conteudo.append(Paragraph("✈ Voos", estilo_secao))
        dados_tabela = [["Companhia", "Partida", "Chegada", "Preço"]]  # linha de cabeçalho
        for voo in roteiro.voos:
            preco_fmt = f"R$ {float(voo.preco):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            dados_tabela.append([
                voo.companhia,
                str(voo.partida)[:16].replace("T", " "),   # "2025-07-01T14:00" → "2025-07-01 14:00"
                str(voo.chegada)[:16].replace("T", " "),
                preco_fmt,
            ])
        tabela = Table(dados_tabela, colWidths=[4 * cm, 4.5 * cm, 4.5 * cm, 3 * cm])
        tabela.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), cor_principal),      # cabeçalho colorido
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),  # linhas alternadas
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        conteudo.append(tabela)

    # ── Hospedagem ────────────────────────────────────────────────────────────
    if roteiro.hospedagens:
        conteudo.append(Paragraph("🏨 Hospedagem", estilo_secao))
        for h in roteiro.hospedagens:
            preco_fmt = f"R$ {float(h.preco_por_noite):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            avaliacao = f" · ★ {h.avaliacao}" if h.avaliacao else ""
            conteudo.append(
                Paragraph(f"<b>{h.nome}</b> — {h.tipo or ''}{avaliacao} · {preco_fmt}/noite", estilo_normal)
            )

    # ── Atividades por Dia ────────────────────────────────────────────────────
    if roteiro.atividades:
        conteudo.append(Paragraph("🗺 Atividades por Dia", estilo_secao))
        dias = sorted(set(a.dia for a in roteiro.atividades))
        for dia in dias:
            conteudo.append(Paragraph(f"<b>Dia {dia}</b>", estilo_normal))
            for ativ in [a for a in roteiro.atividades if a.dia == dia]:
                horario = f"{str(ativ.horario)[:5]} · " if ativ.horario else ""
                custo = ""
                if ativ.custo_estimado and float(ativ.custo_estimado) > 0:
                    custo_fmt = f"R$ {float(ativ.custo_estimado):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    custo = f" · {custo_fmt}"
                desc = f" — {ativ.descricao}" if ativ.descricao else ""
                conteudo.append(
                    Paragraph(f"  {horario}<b>{ativ.nome}</b>{desc}{custo}", estilo_normal)
                )
            conteudo.append(Spacer(1, 0.2 * cm))

    # ── Rodapé ────────────────────────────────────────────────────────────────
    conteudo.append(Spacer(1, 0.5 * cm))
    conteudo.append(HRFlowable(width="100%", color=colors.HexColor("#e5e7eb"), thickness=0.5))
    conteudo.append(
        Paragraph(
            "Gerado por Trippin' · Dados via Amadeus Sandbox (demonstração)",
            ParagraphStyle("Rodape", parent=estilos["Normal"], fontSize=8, textColor=colors.HexColor("#9ca3af")),
        )
    )

    # Constrói o PDF e escreve no buffer
    doc.build(conteudo)
    return buffer.getvalue()
