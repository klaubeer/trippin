"""
Script de seed: cria o usuário demo com roteiros pré-gerados.
Executar uma vez após as migrações: python seed_demo.py
"""
import asyncio
import uuid
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import configuracoes
from autenticacao.modelos import Usuario
from viagens.modelos import (
    Atividade,
    Hospedagem,
    NivelRoteiro,
    Roteiro,
    SolicitacaoViagem,
    StatusSolicitacao,
    Voo,
)

EMAIL_DEMO = "demo@trippin.com"
SENHA_DEMO = "demo123"


async def criar_seed():
    motor = create_async_engine(configuracoes.database_url)
    fabrica = async_sessionmaker(motor, expire_on_commit=False)

    async with fabrica() as sessao:
        # Verifica se usuário demo já existe
        from sqlalchemy import select
        resultado = await sessao.execute(select(Usuario).where(Usuario.email == EMAIL_DEMO))
        usuario_existente = resultado.scalar_one_or_none()

        if usuario_existente:
            print(f"Usuário demo já existe: {EMAIL_DEMO}")
            return

        # Cria usuário demo
        from fastapi_users.password import PasswordHelper
        helper = PasswordHelper()
        senha_hash = helper.hash(SENHA_DEMO)

        usuario_demo = Usuario(
            id=uuid.uuid4(),
            email=EMAIL_DEMO,
            hashed_password=senha_hash,
            nome="Demo User",
            is_active=True,
            is_verified=True,
            is_superuser=False,
        )
        sessao.add(usuario_demo)
        await sessao.flush()

        # Cria solicitação de viagem para Paris
        solicitacao = SolicitacaoViagem(
            usuario_id=usuario_demo.id,
            destino="Paris",
            iata_destino="CDG",
            data_inicio=date(2025, 7, 10),
            data_fim=date(2025, 7, 17),
            num_viajantes=2,
            status=StatusSolicitacao.concluido,
            slug=uuid.uuid4(),
            criado_em=datetime.utcnow(),
        )
        sessao.add(solicitacao)
        await sessao.flush()

        # Cria 3 roteiros
        dados_roteiros = [
            {
                "nivel": NivelRoteiro.economico,
                "resumo": "Roteiro econômico para Paris com as melhores opções de custo-benefício. Ideal para viajantes que querem aproveitar a cidade luz sem gastar muito.",
                "custo_total": Decimal("8900.00"),
                "voo": {"companhia": "Gol Airlines", "partida": datetime(2025, 7, 10, 14, 0), "chegada": datetime(2025, 7, 11, 6, 0), "preco": Decimal("2200.00"), "link_reserva": "https://voegol.com.br"},
                "hotel": {"nome": "Ibis Budget Paris Montmartre", "tipo": "Econômico", "preco_por_noite": Decimal("180.00"), "avaliacao": 3.7, "link_reserva": "https://ibis.com"},
            },
            {
                "nivel": NivelRoteiro.conforto,
                "resumo": "Roteiro conforto com hospedagem bem localizada e as principais atrações de Paris. Equilíbrio perfeito entre qualidade e preço.",
                "custo_total": Decimal("15400.00"),
                "voo": {"companhia": "LATAM Airlines", "partida": datetime(2025, 7, 10, 22, 0), "chegada": datetime(2025, 7, 11, 14, 0), "preco": Decimal("3800.00"), "link_reserva": "https://latam.com"},
                "hotel": {"nome": "Novotel Paris Centre Tour Eiffel", "tipo": "Superior", "preco_por_noite": Decimal("420.00"), "avaliacao": 4.2, "link_reserva": "https://novotel.com"},
            },
            {
                "nivel": NivelRoteiro.premium,
                "resumo": "Roteiro premium com o melhor que Paris tem a oferecer. Hotel de luxo, voos com mais conforto e experiências exclusivas.",
                "custo_total": Decimal("32000.00"),
                "voo": {"companhia": "Air France", "partida": datetime(2025, 7, 10, 23, 30), "chegada": datetime(2025, 7, 11, 16, 0), "preco": Decimal("8500.00"), "link_reserva": "https://airfrance.com"},
                "hotel": {"nome": "Sofitel Paris Le Faubourg", "tipo": "Luxo", "preco_por_noite": Decimal("1200.00"), "avaliacao": 4.8, "link_reserva": "https://sofitel.com"},
            },
        ]

        atividades_base = [
            {"nome": "Torre Eiffel", "dia": 1, "horario": time(9, 0), "descricao": "O símbolo de Paris. Suba até o topo para uma vista incrível da cidade.", "custo_estimado": Decimal("60.00"), "latitude": 48.8584, "longitude": 2.2945},
            {"nome": "Museu do Louvre", "dia": 2, "horario": time(10, 0), "descricao": "O maior museu de arte do mundo. Reserve ao menos 3 horas.", "custo_estimado": Decimal("22.00"), "latitude": 48.8606, "longitude": 2.3376},
            {"nome": "Notre-Dame de Paris", "dia": 2, "horario": time(15, 0), "descricao": "A icônica catedral gótica em processo de restauração.", "custo_estimado": Decimal("0.00"), "latitude": 48.8530, "longitude": 2.3499},
            {"nome": "Champs-Élysées", "dia": 3, "horario": time(11, 0), "descricao": "A avenida mais famosa do mundo, perfeita para compras e passeios.", "custo_estimado": Decimal("0.00"), "latitude": 48.8698, "longitude": 2.3078},
            {"nome": "Arco do Triunfo", "dia": 3, "horario": time(14, 0), "descricao": "Monumento histórico com vista panorâmica de Paris.", "custo_estimado": Decimal("16.00"), "latitude": 48.8738, "longitude": 2.2950},
            {"nome": "Sacré-Cœur", "dia": 4, "horario": time(9, 0), "descricao": "Basílica no alto de Montmartre com vista deslumbrante.", "custo_estimado": Decimal("0.00"), "latitude": 48.8867, "longitude": 2.3431},
            {"nome": "Museu d'Orsay", "dia": 5, "horario": time(10, 0), "descricao": "Impressionismo francês — Van Gogh, Monet, Renoir.", "custo_estimado": Decimal("16.00"), "latitude": 48.8600, "longitude": 2.3266},
            {"nome": "Palácio de Versalhes", "dia": 6, "horario": time(9, 0), "descricao": "O grandioso palácio real a 20 km de Paris. Reserve o dia inteiro.", "custo_estimado": Decimal("20.00"), "latitude": 48.8049, "longitude": 2.1204},
            {"nome": "Cruzeiro no Sena", "dia": 7, "horario": time(18, 0), "descricao": "Passeio de barco com vista noturna dos monumentos iluminados.", "custo_estimado": Decimal("25.00"), "latitude": 48.8566, "longitude": 2.3522},
        ]

        for dados in dados_roteiros:
            roteiro = Roteiro(
                solicitacao_id=solicitacao.id,
                nivel=dados["nivel"],
                custo_total_estimado=dados["custo_total"],
                resumo=dados["resumo"],
            )
            sessao.add(roteiro)
            await sessao.flush()

            sessao.add(Voo(roteiro_id=roteiro.id, **dados["voo"]))
            sessao.add(Hospedagem(roteiro_id=roteiro.id, **dados["hotel"]))

            for ativ in atividades_base:
                sessao.add(Atividade(roteiro_id=roteiro.id, **ativ))

        await sessao.commit()
        print(f"✓ Usuário demo criado: {EMAIL_DEMO} / {SENHA_DEMO}")
        print(f"✓ Solicitação demo criada: Paris (7 dias)")

    await motor.dispose()


if __name__ == "__main__":
    asyncio.run(criar_seed())
