"""Capa 1080x1920 na identidade @acheiebarato.oficial.

Laranja #FF6A13, amarelo #FFD23F, texto #111111/branco, Montserrat Black (títulos)
e SemiBold (texto). Faixa amarela com o gancho (até 5 palavras), produto recortado,
preço em etiqueta laranja, rodapé "@acheiebarato.oficial · link de afiliado na bio".
"""
from __future__ import annotations

import io
import os

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

W, H = 1080, 1920
LARANJA = (255, 106, 19)
AMARELO = (255, 210, 63)
PRETO = (17, 17, 17)
BRANCO = (255, 255, 255)
PERFIL = "@acheiebarato.oficial"
RODAPE = f"{PERFIL} · link de afiliado na bio"
FALA_FINAL = "Achei, e é barato! Link na bio."

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTE_BLACK = os.path.join(_RAIZ, "assets", "fonts", "Montserrat-Black.ttf")
FONTE_SEMI = os.path.join(_RAIZ, "assets", "fonts", "Montserrat-SemiBold.ttf")


def fonte(peso: str, tamanho: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONTE_BLACK if peso == "black" else FONTE_SEMI, tamanho)


def gancho_curto(gancho: str, max_palavras: int = 5) -> str:
    palavras = gancho.split()
    return " ".join(palavras[:max_palavras])


def preco_br(v: float) -> str:
    inteiro, cent = f"{v:,.2f}".split(".")
    return f"R$ {inteiro.replace(',', '.')},{cent}"


def _quebra(draw, texto, f, largura_max, max_linhas):
    linhas, atual = [], ""
    for p in texto.split():
        teste = f"{atual} {p}".strip()
        if draw.textlength(teste, font=f) <= largura_max:
            atual = teste
        else:
            if atual:
                linhas.append(atual)
            atual = p
    if atual:
        linhas.append(atual)
    if len(linhas) > max_linhas:
        linhas = linhas[:max_linhas]
        while linhas[-1] and draw.textlength(linhas[-1] + "…", font=f) > largura_max:
            linhas[-1] = linhas[-1][:-1]
        linhas[-1] = linhas[-1].rstrip() + "…"
    return linhas


def _ajusta(draw, texto, peso, largura_max, max_linhas, tam_ini, tam_min):
    tam = tam_ini
    while tam > tam_min:
        f = fonte(peso, tam)
        linhas = _quebra(draw, texto, f, largura_max, 99)
        if len(linhas) <= max_linhas:
            return f, linhas
        tam -= 4
    f = fonte(peso, tam_min)
    return f, _quebra(draw, texto, f, largura_max, max_linhas)


def baixar_imagem(url: str, timeout: int = 30) -> Image.Image | None:
    if not url:
        return None
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": "achadinhos-bot/1.0"})
        r.raise_for_status()
        return Image.open(io.BytesIO(r.content)).convert("RGBA")
    except Exception:
        return None


def recortar(img: Image.Image) -> Image.Image:
    """Tira o fundo: usa rembg se instalado (RECORTE=rembg); senão remove fundo branco liso."""
    if os.getenv("RECORTE", "") == "rembg":
        try:
            from rembg import remove  # type: ignore
            return remove(img)
        except Exception:
            pass
    rgba = img.convert("RGBA")
    px = rgba.getdata()
    # Fundo branco liso (comum nas fotos de produto) vira transparente.
    cantos = [rgba.getpixel((0, 0)), rgba.getpixel((rgba.width - 1, 0)),
              rgba.getpixel((0, rgba.height - 1)), rgba.getpixel((rgba.width - 1, rgba.height - 1))]
    if all(min(c[:3]) >= 240 for c in cantos):
        rgba.putdata([(r, g, b, 0) if min(r, g, b) >= 245 else (r, g, b, a) for r, g, b, a in px])
        return rgba
    return rgba  # foto com cenário: vai num cartão branco arredondado


def _tem_transparencia(img: Image.Image) -> bool:
    return img.mode == "RGBA" and img.getextrema()[3][0] < 255


def _etiqueta(preco: str, antes: str | None) -> Image.Image:
    f = fonte("black", 104)
    fa = fonte("semi", 42)
    tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    lw = int(tmp.textlength(preco, font=f))
    larg = max(lw, int(tmp.textlength(antes or "", font=fa))) + 120
    alt = 190 if antes else 150
    tag = Image.new("RGBA", (larg + 20, alt + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(tag)
    d.rounded_rectangle((10, 10, larg + 10, alt + 10), radius=36, fill=LARANJA, outline=BRANCO, width=8)
    y = 26
    if antes:
        aw = d.textlength(antes, font=fa)
        ax = (larg + 20 - aw) / 2
        d.text((ax, y), antes, font=fa, fill=BRANCO)
        d.line((ax - 4, y + 26, ax + aw + 4, y + 26), fill=BRANCO, width=5)
        y += 50
    d.text(((larg + 20 - lw) / 2, y), preco, font=f, fill=BRANCO)
    return tag.rotate(-6, expand=True, resample=Image.BICUBIC)


def gerar_capa(produto: dict, gancho: str, imagem: Image.Image | None, destino: str) -> str:
    capa = Image.new("RGB", (W, H), LARANJA)
    d = ImageDraw.Draw(capa)

    # Faixa amarela com o gancho
    texto_gancho = gancho_curto(gancho).upper()
    fg, linhas = _ajusta(d, texto_gancho, "black", W - 140, 2, 120, 64)
    alt_linha = int(fg.size * 1.12)
    alt_faixa = alt_linha * len(linhas) + 90
    y0 = 150
    d.rectangle((0, y0, W, y0 + alt_faixa), fill=AMARELO)
    y = y0 + 45
    for ln in linhas:
        d.text(((W - d.textlength(ln, font=fg)) / 2, y), ln, font=fg, fill=PRETO)
        y += alt_linha

    # Produto
    area = (90, y0 + alt_faixa + 70, W - 90, 1420)
    aw, ah = area[2] - area[0], area[3] - area[1]
    if imagem is not None:
        img = recortar(imagem)
        transp = _tem_transparencia(img)
        if not transp:
            cartao = Image.new("RGBA", (aw, ah), (0, 0, 0, 0))
            ImageDraw.Draw(cartao).rounded_rectangle((0, 0, aw, ah), radius=48, fill=BRANCO)
            capa.paste(cartao, (area[0], area[1]), cartao)
            img = ImageOps.contain(img, (aw - 60, ah - 60))
        else:
            bbox = img.getbbox()
            if bbox:
                img = img.crop(bbox)
            img = ImageOps.contain(img, (aw, ah))
            sombra = Image.new("RGBA", img.size, (0, 0, 0, 0))
            sombra.putalpha(img.getchannel("A").point(lambda a: int(a * 0.35)))
            sombra = sombra.filter(ImageFilter.GaussianBlur(18))
            capa.paste(sombra, (area[0] + (aw - img.width) // 2 + 14, area[1] + (ah - img.height) // 2 + 22), sombra)
        capa.paste(img, (area[0] + (aw - img.width) // 2, area[1] + (ah - img.height) // 2), img)
    else:
        ImageDraw.Draw(capa).rounded_rectangle(area, radius=48, fill=BRANCO)

    # Etiqueta de preço sobre o canto inferior direito do produto
    antes = None
    if produto.get("preco_original", 0) > produto["preco"] * 1.05:
        antes = preco_br(produto["preco_original"])
    tag = _etiqueta(preco_br(produto["preco"]), antes)
    capa.paste(tag, (W - tag.width - 40, area[3] - tag.height + 70), tag)

    # Nome do produto
    ft, linhas_t = _ajusta(d, produto["titulo"], "semi", W - 160, 2, 54, 40)
    y = 1530
    for ln in linhas_t:
        d.text(((W - d.textlength(ln, font=ft)) / 2, y), ln, font=ft, fill=BRANCO)
        y += int(ft.size * 1.25)

    # Rodapé
    fr = fonte("semi", 38)
    d.text(((W - d.textlength(RODAPE, font=fr)) / 2, 1740), RODAPE, font=fr, fill=BRANCO)

    capa.save(destino, "PNG", optimize=True)
    return destino


def gerar_final(destino: str) -> str:
    """Cartão de fechamento com a fala final."""
    img = Image.new("RGB", (W, H), LARANJA)
    d = ImageDraw.Draw(img)
    f1 = fonte("black", 130)
    for i, ln in enumerate(["ACHEI,", "E É", "BARATO!"]):
        y = 560 + i * 165
        if i == 2:
            d.rectangle((0, y - 20, W, y + 165), fill=AMARELO)
            cor = PRETO
        else:
            cor = BRANCO
        d.text(((W - d.textlength(ln, font=f1)) / 2, y), ln, font=f1, fill=cor)
    f2 = fonte("semi", 64)
    t = "Link na bio 👆".replace(" 👆", "")
    d.text(((W - d.textlength(t, font=f2)) / 2, 1140), t, font=f2, fill=BRANCO)
    fr = fonte("semi", 38)
    d.text(((W - d.textlength(RODAPE, font=fr)) / 2, 1740), RODAPE, font=fr, fill=BRANCO)
    img.save(destino, "PNG", optimize=True)
    return destino
