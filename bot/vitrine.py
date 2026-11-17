"""Vitrine pública (link da bio) + Política de Privacidade e Termos de Uso.

Gera arquivos estáticos em docs/ a cada rodada, a partir de data/historico.json.
Sem segredos, sem cookies, sem rastreamento: só HTML/CSS. Publicável no GitHub Pages
(Settings > Pages > branch main, pasta /docs).
"""
from __future__ import annotations

import html
import os
from datetime import datetime, timedelta, timezone

from .arte import mostrar_preco_de, preco_br
from .filtro import motivo_bloqueio

PERFIL = "@acheiebarato.oficial"
NOME = "Achei e Barato"
DIAS_VITRINE = 14
MAX_ITENS = 60

CSS = """
:root{--laranja:#FF6A13;--amarelo:#FFD23F;--texto:#111111;--fundo:#FFF8F2;--card:#FFFFFF;--suave:#5b5b5b}
@media (prefers-color-scheme:dark){:root{--texto:#F5F5F5;--fundo:#141414;--card:#1F1F1F;--suave:#bdbdbd}}
*{box-sizing:border-box}
body{margin:0;font-family:Montserrat,system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:var(--fundo);color:var(--texto);line-height:1.45}
header{background:var(--laranja);color:#fff;padding:20px 16px 16px;text-align:center}
header h1{margin:0;font-weight:900;font-size:1.6rem;letter-spacing:-.02em}
header p{margin:6px 0 0;font-weight:600}
.faixa{background:var(--amarelo);color:#111;text-align:center;font-weight:800;padding:8px 16px;font-size:.95rem}
main{max-width:720px;margin:0 auto;padding:16px}
.grade{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
@media (min-width:600px){.grade{grid-template-columns:repeat(3,minmax(0,1fr))}}
.card{background:var(--card);border-radius:14px;overflow:hidden;display:flex;flex-direction:column;text-decoration:none;color:inherit;box-shadow:0 1px 3px rgba(0,0,0,.12)}
.card img{width:100%;aspect-ratio:1/1;object-fit:cover;background:#fff}
.card .sem{width:100%;aspect-ratio:1/1;background:var(--amarelo)}
.card .info{padding:10px;display:flex;flex-direction:column;gap:6px;flex:1}
.card .t{font-weight:600;font-size:.85rem;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.card .p{background:var(--laranja);color:#fff;font-weight:900;border-radius:8px;padding:4px 8px;align-self:flex-start}
.card .a{font-size:.75rem;color:var(--suave);text-decoration:line-through}
.card .b{margin-top:auto;font-weight:800;color:var(--laranja);font-size:.85rem}
.vazio{text-align:center;padding:40px 0;color:var(--suave)}
footer{max-width:720px;margin:0 auto;padding:24px 16px 40px;font-size:.8rem;color:var(--suave);text-align:center}
footer a{color:inherit}
article{max-width:720px;margin:0 auto;padding:16px}
article h2{font-weight:900;margin-top:28px}
article h3{margin-top:20px}
"""


def _pagina(titulo: str, corpo: str, descricao: str) -> str:
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(titulo)}</title>
<meta name="description" content="{html.escape(descricao)}">
<meta name="robots" content="index,follow">
<style>{CSS}</style>
</head>
<body>
{corpo}
<footer>
<p>{NOME} · {PERFIL} no TikTok e no Instagram</p>
<p>Links de afiliado: podemos ganhar comissão, sem custo extra para você. Preço e estoque podem mudar na loja.</p>
<p><a href="index.html">Vitrine</a> · <a href="privacidade.html">Privacidade / Privacy</a> · <a href="termos.html">Termos / Terms</a></p>
</footer>
</body>
</html>
"""


def _seguro(url: str) -> str:
    url = (url or "").strip()
    return url if url.startswith("https://") else ""


def itens_vitrine(historico: list[dict], agora: datetime) -> list[dict]:
    limite = agora - timedelta(days=DIAS_VITRINE)
    vistos, saida = set(), []
    for h in sorted(historico, key=lambda x: x.get("quando", ""), reverse=True):
        try:
            quando = datetime.fromisoformat(h["quando"])
        except (KeyError, ValueError):
            continue
        if (quando < limite or h.get("id") in vistos or not _seguro(h.get("link", ""))
                or not _seguro(h.get("imagem", "")) or motivo_bloqueio(h.get("titulo", ""))):
            continue
        vistos.add(h.get("id"))
        saida.append(h)
        if len(saida) >= MAX_ITENS:
            break
    return saida


def _card(h: dict) -> str:
    link = html.escape(_seguro(h["link"]), quote=True)
    img = _seguro(h.get("imagem", ""))
    foto = (f'<img src="{html.escape(img, quote=True)}" alt="" loading="lazy" referrerpolicy="no-referrer">'
            if img else '<div class="sem"></div>')
    antes = ""
    po = float(h.get("preco_original") or 0)
    if mostrar_preco_de(float(h["preco"]), po):
        antes = f'<span class="a">{preco_br(po)}</span>'
    return (f'<a class="card" href="{link}" target="_blank" rel="sponsored noopener nofollow">{foto}'
            f'<div class="info"><span class="t">{html.escape(h.get("titulo", ""))}</span>{antes}'
            f'<span class="p">{preco_br(float(h["preco"]))}</span><span class="b">Ver na Shopee →</span></div></a>')


def gerar_vitrine(historico: list[dict], agora: datetime) -> str:
    itens = itens_vitrine(historico, agora)
    grade = ("<div class=\"grade\">" + "".join(_card(h) for h in itens) + "</div>") if itens else \
        '<p class="vazio">Novos achadinhos chegam 3x por dia. Volte já já!</p>'
    corpo = (f'<header><h1>Achei, e é barato!</h1><p>Os achadinhos dos vídeos de {PERFIL}</p></header>'
             f'<div class="faixa">Do mais novo para o mais antigo · atualizado 3x por dia</div>'
             f'<main>{grade}</main>')
    return _pagina(f"{NOME} | achadinhos", corpo,
                   "Os achadinhos baratos dos vídeos de @acheiebarato.oficial, com link direto para a loja.")


PRIVACIDADE = f"""<article>
<h1>Política de Privacidade</h1>
<p><em>Última atualização: 15 de novembro de 2026</em></p>
<p>{NOME} ({PERFIL}) é um perfil de recomendações de produtos com links de afiliado. Esta política
explica quais dados tratamos no site da vitrine e no nosso aplicativo de publicação ("App {NOME}").</p>
<h2>1. Visitantes da vitrine</h2>
<p>A vitrine é uma página estática. Não usamos cookies, formulários, pixels de anúncio nem ferramentas de
análise, e não coletamos dados pessoais de quem visita. Ao clicar em um produto você vai para a loja
(Shopee), que tem a própria política de privacidade.</p>
<h2>2. App {NOME} (publicação automática)</h2>
<p>O App {NOME} é usado apenas para publicar vídeos de produtos na nossa própria conta de TikTok e de
Instagram. Com a sua autorização (do titular da conta), ele recebe tokens de acesso e informações básicas
do perfil (identificador e nome de exibição) somente para publicar os vídeos e verificar o status da
publicação. O app não lê mensagens, não acessa seguidores e não coleta dados de outros usuários.</p>
<p>Os tokens ficam guardados criptografados como segredos no ambiente de automação (GitHub Actions),
não são compartilhados com terceiros e podem ser revogados a qualquer momento nas configurações do
TikTok ou do Instagram, o que interrompe o uso imediatamente.</p>
<h2>3. Base legal e direitos (LGPD)</h2>
<p>Tratamos apenas os dados mínimos, com base no legítimo interesse e na execução do serviço pedido pelo
titular da conta. Você pode pedir acesso, correção ou exclusão de dados pelo Direct do Instagram
{PERFIL}. Respondemos em até 15 dias.</p>
<h2>4. Alterações</h2>
<p>Se esta política mudar, a data acima será atualizada nesta página.</p>

<hr>
<h1 lang="en">Privacy Policy</h1>
<div lang="en">
<p><em>Last updated: November 15, 2026</em></p>
<p>{NOME} ({PERFIL}) is a product-recommendation profile that uses affiliate links. This policy explains
what data we handle on the showcase website and in our publishing app ("{NOME} App").</p>
<h2>1. Showcase visitors</h2>
<p>The showcase is a static page. We use no cookies, forms, ad pixels or analytics tools, and we do not
collect personal data from visitors. Clicking a product takes you to the store (Shopee), which has its own
privacy policy.</p>
<h2>2. {NOME} App (automated publishing)</h2>
<p>The {NOME} App is used only to publish product videos to our own TikTok and Instagram accounts. With
the account owner's authorization, it receives access tokens and basic profile information (identifier and
display name) solely to publish videos and check publishing status. The app does not read messages,
access followers or collect data about other users.</p>
<p>Tokens are stored encrypted as secrets in our automation environment (GitHub Actions), are not shared
with third parties and can be revoked at any time in TikTok or Instagram settings, which stops all use
immediately.</p>
<h2>3. Your rights</h2>
<p>We process only the minimum data needed. You may request access, correction or deletion through a
direct message to {PERFIL} on Instagram. We reply within 15 days.</p>
<h2>4. Changes</h2>
<p>If this policy changes, the date above will be updated on this page.</p>
</div>
</article>"""

TERMOS = f"""<article>
<h1>Termos de Uso</h1>
<p><em>Última atualização: 15 de novembro de 2026</em></p>
<h2>1. O que é</h2>
<p>{NOME} ({PERFIL}) divulga produtos de lojas parceiras por meio de vídeos e desta vitrine. Não vendemos
produtos: a compra, o pagamento, a entrega, a troca e a garantia são feitos diretamente com a loja
(Shopee e seus vendedores), segundo as regras dela.</p>
<h2>2. Links de afiliado</h2>
<p>Os links são de afiliado: podemos receber comissão quando você compra por eles, sem custo extra para
você.</p>
<h2>3. Preços e disponibilidade</h2>
<p>Preços, descontos e estoque mostrados nos vídeos e na vitrine são os da loja no momento da publicação
e podem mudar a qualquer momento. Sempre confira o valor final na loja antes de comprar.</p>
<h2>4. App {NOME}</h2>
<p>O App {NOME} é uma ferramenta interna que publica vídeos apenas nas nossas próprias contas de TikTok e
Instagram, conforme os termos dessas plataformas. Não é oferecido ao público.</p>
<h2>5. Responsabilidade</h2>
<p>Escolhemos produtos com cuidado, mas não garantimos a qualidade, a entrega ou o funcionamento dos
produtos de terceiros. Problemas com o pedido devem ser tratados com a loja.</p>
<h2>6. Contato</h2>
<p>Pelo Direct do Instagram {PERFIL}. Estes termos seguem a lei brasileira.</p>

<hr>
<h1 lang="en">Terms of Use</h1>
<div lang="en">
<p><em>Last updated: November 15, 2026</em></p>
<h2>1. What this is</h2>
<p>{NOME} ({PERFIL}) promotes products from partner stores through videos and this showcase. We do not
sell products: purchase, payment, delivery, returns and warranty are handled directly by the store (Shopee
and its sellers) under its own rules.</p>
<h2>2. Affiliate links</h2>
<p>Links are affiliate links: we may earn a commission when you buy through them, at no extra cost to you.</p>
<h2>3. Prices and availability</h2>
<p>Prices, discounts and stock shown are the store's at the time of posting and may change at any time.
Always check the final price in the store before buying.</p>
<h2>4. {NOME} App</h2>
<p>The {NOME} App is an internal tool that publishes videos only to our own TikTok and Instagram accounts,
in accordance with those platforms' terms. It is not offered to the public.</p>
<h2>5. Liability</h2>
<p>We choose products carefully but do not guarantee the quality, delivery or operation of third-party
products. Order issues must be handled with the store.</p>
<h2>6. Contact</h2>
<p>Direct message to {PERFIL} on Instagram. These terms are governed by Brazilian law.</p>
</div>
</article>"""


def gerar_site(historico: list[dict], destino: str, agora: datetime | None = None) -> list[str]:
    agora = agora or datetime.now(timezone.utc)
    os.makedirs(destino, exist_ok=True)
    paginas = {
        "index.html": gerar_vitrine(historico, agora),
        "privacidade.html": _pagina(f"Política de Privacidade | {NOME}", PRIVACIDADE,
                                    "Política de Privacidade / Privacy Policy - Achei e Barato"),
        "termos.html": _pagina(f"Termos de Uso | {NOME}", TERMOS,
                               "Termos de Uso / Terms of Use - Achei e Barato"),
    }
    escritos = []
    for nome, conteudo in paginas.items():
        caminho = os.path.join(destino, nome)
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(conteudo)
        escritos.append(caminho)
    # GitHub Pages sem Jekyll
    open(os.path.join(destino, ".nojekyll"), "w").close()
    return escritos
