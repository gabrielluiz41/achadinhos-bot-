"""Categorias proibidas: saúde/remédio/suplemento/emagrecedor, armas/facas, adulto,
réplica de marca, vape/cigarro, cadeirinha/bebê conforto; e produto com defeito/outlet
(pedido do Garimpeiro 17/11).

Cada termo casa como palavra inteira (aceita plural com s/es). Termo terminado em "*"
casa como começo de palavra (ex.: "emagrec*" pega emagrecer, emagrecedor).
"""
from __future__ import annotations

import re
import unicodedata

PROIBIDOS = {
    "saude": ["remedio", "medicamento", "suplemento", "emagrec*", "termogenic*", "whey", "creatina",
              "capsula", "colageno", "vitamina", "detox", "queima gordura", "seca barriga",
              "cha secante", "anabolizante", "farmacia", "manipulado", "fitoterapico", "ozempic",
              "sibutramina", "laxante", "pomada", "colirio", "antibiotico", "anti-inflamatorio",
              "melatonina", "inibidor de apetite", "moderador de apetite"],
    "armas": ["faca", "canivete", "punhal", "adaga", "facao", "machete", "arma", "arma de fogo",
              "pistola", "revolver", "espingarda", "airsoft", "municao", "taser", "arma de choque",
              "soco ingles", "spray de pimenta", "estilingue", "arco e flecha", "cassetete", "tonfa",
              "nunchaku", "katana", "espada", "kit churrasco"],
    "adulto": ["sex shop", "sexy", "sexual", "erotic*", "vibrador", "lubrificante intimo",
               "lingerie sensual", "fetiche", "consolo", "plug anal", "preservativo", "camisinha",
               "produto adulto", "18+"],
    "replica": ["replica", "primeira linha", "1a linha", "inspired", "inspirado", "similar ao original",
                "tipo original", "master copy", "espelhado", "aaa"],
    "fumo": ["vape", "pod descartavel", "cigarro", "cigarro eletronico", "narguile", "essencia para narguile",
             "tabaco", "seda", "dichavador", "piteira", "juul", "ignite", "pod"],
    "qualidade": ["outlet", "defeito*", "defeituos*", "avaria*", "mostruario", "pequenos defeitos",
                  "segunda linha", "2a linha"],
    "bebe_seguranca": ["cadeirinha", "bebe conforto", "assento infantil", "booster", "cadeira para auto",
                       "cadeira auto", "assento de elevacao"],
}

CATEGORIAS_PROIBIDAS = ["saude", "health", "medic*", "suplemento", "adult*", "farmac*", "pharmacy",
                        "weapon", "tabaco", "tobacco"]


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", s).strip()


def _regex(termo: str) -> re.Pattern:
    t = _norm(termo)
    if t.endswith("*"):
        return re.compile(r"(?<![a-z0-9])" + re.escape(t[:-1]))
    return re.compile(r"(?<![a-z0-9])" + re.escape(t) + r"(?:s|es)?(?![a-z0-9])")


_PADROES = {g: [_regex(p) for p in ps] for g, ps in PROIBIDOS.items()}
_CATS = [_regex(c) for c in CATEGORIAS_PROIBIDAS]


def motivo_bloqueio(titulo: str, categoria: str = "", subcategoria: str = "") -> str | None:
    """Devolve o grupo proibido que bateu, ou None se o produto pode ir ao ar."""
    t = _norm(titulo)
    cat = _norm(f"{categoria} {subcategoria}")
    for c in _CATS:
        if c.search(cat):
            return "categoria"
    for grupo, padroes in _PADROES.items():
        if any(p.search(t) for p in padroes):
            return grupo
    return None
