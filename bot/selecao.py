"""Escolhe os produtos do dia: nichos do Garimpeiro, filtro, sem repetir em 14 dias."""
from __future__ import annotations

import math
import random
import re
import unicodedata
from datetime import datetime, timedelta, timezone

from .filtro import motivo_bloqueio
from .fontes import Produto

DIAS_SEM_REPETIR = 14
DESCONTO_MAX = 70  # desconto acima disso = preço "de" inflado (Garimpeiro/Diretor 16-17/11)


def _norm(s: str) -> str:
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()


def ids_recentes(historico: list[dict], agora: datetime, dias: int = DIAS_SEM_REPETIR) -> set[str]:
    limite = agora - timedelta(days=dias)
    out = set()
    for h in historico:
        try:
            quando = datetime.fromisoformat(h["quando"])
        except (KeyError, ValueError):
            continue
        if quando.tzinfo is None:
            quando = quando.replace(tzinfo=timezone.utc)
        if quando >= limite:
            out.add(str(h.get("id")))
    return out


def nicho_do_produto(p: Produto, nichos: list[dict]) -> dict | None:
    texto = _norm(f"{p.titulo} {p.categoria} {p.subcategoria}")
    for n in nichos:
        for termo in n.get("termos", []):
            if re.search(r"(?<![a-z])" + re.escape(_norm(termo)), texto):
                return n
    return None


def pontuar(p: Produto, nicho: dict | None) -> float:
    s = 0.0
    s += 3.0 if p.oficial else 0.0
    s += min(p.desconto, 80) / 10.0
    s += math.log10(p.vendas + 1)
    s += max(p.nota - 4.0, 0) * 2 if p.nota else 0
    if nicho:
        s += 2.0 * float(nicho.get("peso", 1.0))
    if p.preco <= 30:
        s += 1.5
    elif p.preco > 150:
        s -= 2.0
    if not p.imagem:
        s -= 5.0
    return s


def escolher(produtos: list[Produto], nichos: list[dict], historico: list[dict], quantidade: int,
             agora: datetime | None = None, preco_max: float = 200.0, seed: int | None = None):
    """Devolve (escolhidos[(produto, nicho)], contagem_de_bloqueios)."""
    agora = agora or datetime.now(timezone.utc)
    recentes = ids_recentes(historico, agora)
    bloqueios: dict[str, int] = {}
    vistos: set[str] = set()
    candidatos = []
    for p in produtos:
        if p.id in vistos:
            continue
        vistos.add(p.id)
        if p.id in recentes:
            bloqueios["repetido_14d"] = bloqueios.get("repetido_14d", 0) + 1
            continue
        motivo = motivo_bloqueio(p.titulo, p.categoria, p.subcategoria)
        if motivo:
            chave = motivo.split(":")[0]
            bloqueios[chave] = bloqueios.get(chave, 0) + 1
            continue
        if p.desconto > DESCONTO_MAX or (p.preco_original and p.preco_original > p.preco
                                         and (1 - p.preco / p.preco_original) * 100 > DESCONTO_MAX):
            bloqueios["desconto_suspeito"] = bloqueios.get("desconto_suspeito", 0) + 1
            continue
        if p.preco > preco_max or p.estoque == 0:
            bloqueios["preco_ou_estoque"] = bloqueios.get("preco_ou_estoque", 0) + 1
            continue
        nicho = nicho_do_produto(p, nichos)
        candidatos.append((pontuar(p, nicho), p, nicho))
    candidatos.sort(key=lambda x: x[0], reverse=True)
    # Variedade: no máximo 1 produto por nicho por rodada, depois completa com o resto.
    rnd = random.Random(seed)
    topo = candidatos[: max(quantidade * 10, 30)]
    rnd.shuffle(topo)
    topo.sort(key=lambda x: x[0], reverse=True)
    escolhidos, nichos_usados = [], set()
    for _, p, n in topo:
        chave = (n or {}).get("nome", "sem_nicho")
        if chave in nichos_usados:
            continue
        escolhidos.append((p, n))
        nichos_usados.add(chave)
        if len(escolhidos) == quantidade:
            break
    if len(escolhidos) < quantidade:
        ja = {p.id for p, _ in escolhidos}
        for _, p, n in topo:
            if p.id not in ja:
                escolhidos.append((p, n))
                if len(escolhidos) == quantidade:
                    break
    return escolhidos, bloqueios
