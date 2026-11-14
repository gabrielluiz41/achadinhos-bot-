"""Fontes de produtos. Toda fonte devolve uma lista de Produto com a mesma forma.

Hoje: feed do afiliado Shopee (CSV exportado do painel), lido pelas URLs dos secrets
SHOPEE_FEED_URL_OFICIAL (prioridade) e SHOPEE_FEED_URL_BRASIL.
Depois: Open API da Shopee entra como outra classe com o mesmo método `produtos()`.

Nunca imprimir, registrar ou gravar o valor das URLs dos secrets.
"""
from __future__ import annotations

import csv
import gzip
import io
import os
import zipfile
from dataclasses import dataclass, asdict, field

import requests

# Nomes de coluna aceitos (minúsculos, sem espaço extra). O feed da Shopee muda de nome
# de coluna entre versões; por isso cada campo aceita vários apelidos.
ALIASES = {
    "id": ["itemid", "item_id", "id", "product_id"],
    "loja_id": ["shopid", "shop_id"],
    "titulo": ["title", "item_name", "product_name", "name", "nome"],
    "preco_original": ["price", "original_price", "preco"],
    "preco": ["sale_price", "price_min", "discounted_price", "preco_promocional"],
    "desconto": ["discount_percentage", "discount", "desconto"],
    "imagem": ["image_link", "image", "image_url", "imagem"],
    "link": ["product_short link", "product_short_link", "short_link", "offer_link",
             "affiliate_link", "product_link", "link"],
    "categoria": ["global_category1", "category", "categoria", "global_category2"],
    "subcategoria": ["global_category2", "global_category3", "subcategory"],
    "loja": ["shop_name", "loja"],
    "oficial": ["is_official_shop", "shopee_verified_flag", "is_mall", "official"],
    "vendas": ["item_sold", "sold", "historical_sold", "vendas"],
    "nota": ["item_rating", "rating", "rating_star", "nota"],
    "estoque": ["stock", "estoque"],
}


@dataclass
class Produto:
    id: str
    titulo: str
    preco: float
    link: str
    imagem: str = ""
    preco_original: float = 0.0
    desconto: float = 0.0
    categoria: str = ""
    subcategoria: str = ""
    loja: str = ""
    oficial: bool = False
    vendas: int = 0
    nota: float = 0.0
    estoque: int = -1
    fonte: str = ""
    extras: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        d = asdict(self)
        d.pop("extras", None)
        return d


def _num(v, default=0.0) -> float:
    if v is None:
        return default
    s = str(v).strip().replace("R$", "").replace("%", "").replace(" ", "")
    if not s:
        return default
    # "1.234,56" -> 1234.56 ; "1234.56" fica igual
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return default


def _bool(v) -> bool:
    return str(v).strip().lower() in {"1", "true", "sim", "yes", "y", "t", "official", "mall"}


def _pega(row: dict, campo: str):
    for nome in ALIASES[campo]:
        if nome in row and str(row[nome]).strip() != "":
            return row[nome]
    return None


def _texto_csv(conteudo: bytes) -> str:
    """Aceita CSV puro, .gz ou .zip (pega o 1º .csv)."""
    if conteudo[:2] == b"\x1f\x8b":
        conteudo = gzip.decompress(conteudo)
    elif conteudo[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
            nome = next((n for n in z.namelist() if n.lower().endswith((".csv", ".txt"))), z.namelist()[0])
            conteudo = z.read(nome)
    for enc in ("utf-8-sig", "latin-1"):
        try:
            return conteudo.decode(enc)
        except UnicodeDecodeError:
            continue
    return conteudo.decode("utf-8", errors="replace")


def parse_csv(texto: str, fonte: str, forcar_oficial: bool = False) -> tuple[list[Produto], list[str]]:
    """Devolve (produtos, nomes_das_colunas). Nomes de coluna não são segredo."""
    amostra = texto[:4096]
    try:
        dialeto = csv.Sniffer().sniff(amostra, delimiters=",;\t|")
    except csv.Error:
        dialeto = csv.excel
    leitor = csv.DictReader(io.StringIO(texto), dialect=dialeto)
    colunas = [c.strip() for c in (leitor.fieldnames or [])]
    produtos: list[Produto] = []
    for bruto in leitor:
        row = {str(k).strip().lower(): (v or "").strip() for k, v in bruto.items() if k is not None}
        pid = _pega(row, "id")
        titulo = _pega(row, "titulo")
        link = _pega(row, "link")
        if not (pid and titulo and link):
            continue
        preco_original = _num(_pega(row, "preco_original"))
        preco = _num(_pega(row, "preco"), preco_original) or preco_original
        if preco <= 0:
            continue
        desconto = _num(_pega(row, "desconto"))
        if not desconto and preco_original > preco:
            desconto = round((1 - preco / preco_original) * 100)
        loja_id = _pega(row, "loja_id") or ""
        produtos.append(Produto(
            id=f"{loja_id}-{pid}" if loja_id else str(pid),
            titulo=" ".join(titulo.split()),
            preco=round(preco, 2),
            preco_original=round(max(preco_original, preco), 2),
            desconto=float(desconto),
            link=link,
            imagem=_pega(row, "imagem") or "",
            categoria=_pega(row, "categoria") or "",
            subcategoria=_pega(row, "subcategoria") or "",
            loja=_pega(row, "loja") or "",
            oficial=forcar_oficial or _bool(_pega(row, "oficial")),
            vendas=int(_num(_pega(row, "vendas"))),
            nota=_num(_pega(row, "nota")),
            estoque=int(_num(_pega(row, "estoque"), -1)),
            fonte=fonte,
        ))
    return produtos, colunas


class FonteFeedShopee:
    """Feed do afiliado. `env_url` é o NOME do secret, nunca o valor."""

    def __init__(self, nome: str, env_url: str, oficial: bool):
        self.nome = nome
        self.env_url = env_url
        self.oficial = oficial
        self.colunas: list[str] = []
        self.erro: str = ""

    def disponivel(self) -> bool:
        return bool(os.getenv(self.env_url, "").strip())

    def produtos(self, limite_bytes: int = 400 * 1024 * 1024) -> list[Produto]:
        url = os.getenv(self.env_url, "").strip()
        if not url:
            self.erro = f"secret {self.env_url} ausente"
            return []
        try:
            r = requests.get(url, timeout=180, stream=True, headers={"User-Agent": "achadinhos-bot/1.0"})
            r.raise_for_status()
            buf = io.BytesIO()
            for parte in r.iter_content(1024 * 1024):
                buf.write(parte)
                if buf.tell() > limite_bytes:
                    break
        except requests.RequestException as e:
            # Só o tipo do erro e o status: a mensagem pode conter a URL do secret.
            status = getattr(getattr(e, "response", None), "status_code", "")
            self.erro = f"falha ao baixar {self.env_url}: {type(e).__name__} {status}".strip()
            return []
        produtos, self.colunas = parse_csv(_texto_csv(buf.getvalue()), self.nome, self.oficial)
        return produtos


class FonteOpenAPIShopee:
    """Reservado: Open API do afiliado (ainda não liberada no painel). Mesma interface."""

    nome = "openapi"
    colunas: list[str] = []
    erro = ""

    def disponivel(self) -> bool:
        return bool(os.getenv("SHOPEE_APP_ID") and os.getenv("SHOPEE_APP_SECRET"))

    def produtos(self) -> list[Produto]:
        self.erro = "Open API ainda não implementada"
        return []


class FonteArquivo:
    """CSV local (testes e ensaio sem secrets)."""

    def __init__(self, caminho: str, nome: str = "arquivo", oficial: bool = False):
        self.caminho, self.nome, self.oficial = caminho, nome, oficial
        self.colunas: list[str] = []
        self.erro = ""

    def disponivel(self) -> bool:
        return os.path.exists(self.caminho)

    def produtos(self) -> list[Produto]:
        with open(self.caminho, "rb") as f:
            produtos, self.colunas = parse_csv(_texto_csv(f.read()), self.nome, self.oficial)
        return produtos


def fontes_padrao() -> list:
    return [
        FonteFeedShopee("oficial", "SHOPEE_FEED_URL_OFICIAL", oficial=True),
        FonteFeedShopee("brasil", "SHOPEE_FEED_URL_BRASIL", oficial=False),
        FonteOpenAPIShopee(),
    ]
