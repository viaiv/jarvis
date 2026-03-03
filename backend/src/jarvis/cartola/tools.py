"""Ferramentas do Cartola FC para o agente Jarvis."""

from __future__ import annotations

from datetime import datetime, timezone

from langchain_core.tools import tool

from . import client, scraper


@tool
def cartola_market_status() -> str:
    """Retorna o status atual do mercado do Cartola FC: rodada, estado, fechamento e times escalados."""
    try:
        data = client.fetch_market_status()
    except Exception as e:
        return f"Erro ao consultar mercado: {e}"

    rodada = data.get("rodada_atual", "?")
    status_id = data.get("status_mercado")
    status_map = {1: "Aberto", 2: "Fechado", 4: "Em manutencao", 6: "Final de temporada"}
    status = status_map.get(status_id, f"Desconhecido ({status_id})")

    fechamento_ts = data.get("fechamento", {}).get("timestamp")
    if fechamento_ts:
        dt = datetime.fromtimestamp(fechamento_ts, tz=timezone.utc)
        fechamento = dt.strftime("%d/%m/%Y %H:%M UTC")
    else:
        fechamento = "Nao informado"

    times = data.get("times_escalados", "?")

    return (
        f"Rodada: {rodada}\n"
        f"Status: {status}\n"
        f"Fechamento: {fechamento}\n"
        f"Times escalados: {times}"
    )


@tool
def cartola_players(
    position: str = "",
    club: str = "",
    max_price: float = 0,
    min_average: float = 0,
    status: str = "provavel",
    order_by: str = "media",
    limit: int = 20,
) -> str:
    """Busca jogadores no mercado do Cartola FC com filtros.

    Args:
        position: Posicao (GOL, LAT, ZAG, MEI, ATA, TEC). Vazio = todas.
        club: Nome ou parte do nome do clube. Vazio = todos.
        max_price: Preco maximo em cartoletas. 0 = sem limite.
        min_average: Media minima de pontos. 0 = sem filtro.
        status: Status do jogador (provavel, duvida, suspenso, contundido, todos). Default: provavel.
        order_by: Ordenar por 'media' ou 'preco'. Default: media.
        limit: Numero maximo de resultados (1-50). Default: 20.
    """
    try:
        data = client.fetch_players()
    except Exception as e:
        return f"Erro ao consultar jogadores: {e}"

    atletas = data.get("atletas", [])
    clubes = data.get("clubes", {})
    posicoes = data.get("posicoes", {})

    # Filtro por status
    if status.lower() != "todos":
        status_key = status.lower()
        status_id = client.POSICAO_SIGLA_TO_ID.get(status_key)
        if status_id is None:
            # Busca no STATUS_MAP pelo nome
            status_id = next(
                (k for k, v in client.STATUS_MAP.items() if v.lower() == status_key),
                None,
            )
        if status_id is not None:
            atletas = [a for a in atletas if a.get("status_id") == status_id]
        elif status_key == "provavel":
            atletas = [a for a in atletas if a.get("status_id") == 7]

    # Filtro por posicao
    if position:
        pos_upper = position.upper()
        pos_id = client.POSICAO_SIGLA_TO_ID.get(pos_upper) or client.POSICAO_SIGLA_TO_ID.get(position.lower())
        if pos_id is None:
            opcoes = ", ".join(sorted(set(
                k for k in client.POSICAO_SIGLA_TO_ID if k.isupper()
            )))
            return f"Posicao invalida: '{position}'. Use: {opcoes}"
        atletas = [a for a in atletas if a.get("posicao_id") == pos_id]

    # Filtro por clube
    if club:
        club_lower = club.lower()
        matching_club_ids = set()
        for cid, cinfo in clubes.items():
            nome = cinfo.get("nome", "")
            abreviacao = cinfo.get("abreviacao", "")
            if club_lower in nome.lower() or club_lower in abreviacao.lower():
                matching_club_ids.add(int(cid))
        atletas = [a for a in atletas if a.get("clube_id") in matching_club_ids]

    # Filtro por preco
    if max_price > 0:
        atletas = [a for a in atletas if a.get("preco_num", 0) <= max_price]

    # Filtro por media
    if min_average > 0:
        atletas = [a for a in atletas if a.get("media_num", 0) >= min_average]

    if not atletas:
        return "Nenhum jogador encontrado com os filtros informados."

    # Ordenacao
    if order_by == "preco":
        atletas.sort(key=lambda a: a.get("preco_num", 0), reverse=True)
    else:
        atletas.sort(key=lambda a: a.get("media_num", 0), reverse=True)

    # Limitar resultados
    limit = max(1, min(limit, 50))
    atletas = atletas[:limit]

    # Formatar resultado
    lines = []
    for i, a in enumerate(atletas, 1):
        apelido = a.get("apelido", "?")
        pos_id = a.get("posicao_id", 0)
        pos_nome = posicoes.get(str(pos_id), {}).get("abreviacao", client.POSICAO_MAP.get(pos_id, "?"))
        clube_id = a.get("clube_id", 0)
        clube_nome = clubes.get(str(clube_id), {}).get("abreviacao", "?")
        media = a.get("media_num", 0)
        preco = a.get("preco_num", 0)
        ult = a.get("pontos_num", 0)
        lines.append(
            f"{i}. {apelido} ({pos_nome}/{clube_nome}) "
            f"-- Media: {media:.1f} | Preco: C${preco:.1f} | Ult: {ult:.1f}"
        )

    return "\n".join(lines)


@tool
def cartola_round_scores(round_number: int = 0) -> str:
    """Retorna os jogadores que mais pontuaram em uma rodada do Cartola FC.

    Args:
        round_number: Numero da rodada. 0 = rodada atual.
    """
    try:
        rnd = round_number if round_number > 0 else None
        data = client.fetch_scored(rnd)
    except Exception as e:
        return f"Erro ao consultar pontuacoes: {e}"

    atletas = data.get("atletas", {})
    if not atletas:
        return "Nenhum jogador pontuado encontrado para esta rodada."

    # atletas e um dict {id: {apelido, pontuacao, scout, ...}}
    jogadores = []
    for _aid, info in atletas.items():
        jogadores.append({
            "apelido": info.get("apelido", "?"),
            "pontuacao": info.get("pontuacao", 0),
            "scout": info.get("scout", {}),
        })

    jogadores.sort(key=lambda j: j["pontuacao"], reverse=True)
    top = jogadores[:20]

    lines = []
    for i, j in enumerate(top, 1):
        scouts_str = ", ".join(f"{k}:{v}" for k, v in j["scout"].items()) if j["scout"] else "sem scouts"
        lines.append(
            f"{i}. {j['apelido']} -- {j['pontuacao']:.1f} pts ({scouts_str})"
        )

    return "\n".join(lines)


@tool
def cartola_matches(round_number: int = 0) -> str:
    """Retorna as partidas de uma rodada do Cartola FC.

    Args:
        round_number: Numero da rodada. 0 = rodada atual.
    """
    try:
        rnd = round_number if round_number > 0 else None
        data = client.fetch_matches(rnd)
    except Exception as e:
        return f"Erro ao consultar partidas: {e}"

    clubes = data.get("clubes", {})
    partidas = data.get("partidas", [])

    if not partidas:
        return "Nenhuma partida encontrada para esta rodada."

    lines = []
    for p in partidas:
        mandante_id = str(p.get("clube_casa_id", 0))
        visitante_id = str(p.get("clube_visitante_id", 0))
        mandante = clubes.get(mandante_id, {}).get("nome", "?")
        visitante = clubes.get(visitante_id, {}).get("nome", "?")

        placar_m = p.get("placar_oficial_mandante")
        placar_v = p.get("placar_oficial_visitante")

        if placar_m is not None and placar_v is not None:
            placar = f"{placar_m} x {placar_v}"
        else:
            placar = "A definir"

        local = p.get("local", "")
        timestamp = p.get("timestamp")
        if timestamp:
            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            horario = dt.strftime("%d/%m %H:%M")
        else:
            horario = ""

        info = f"{mandante} {placar} {visitante}"
        if local:
            info += f" | {local}"
        if horario:
            info += f" | {horario}"

        lines.append(info)

    return "\n".join(lines)


@tool
def cartola_expert_tips(source: str = "cartolafcbrasil") -> str:
    """Busca dicas de especialistas para o Cartola FC via scraping.

    Args:
        source: Fonte das dicas. Opcoes: cartolafcbrasil, cartolafcmix. Default: cartolafcbrasil.
    """
    return scraper.scrape_tips(source)


CARTOLA_TOOLS = [
    cartola_market_status,
    cartola_players,
    cartola_round_scores,
    cartola_matches,
    cartola_expert_tips,
]
