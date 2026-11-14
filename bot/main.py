"""Rodada do robô: busca produtos, filtra, escolhe, gera capa + vídeo + legenda.

Uso:
  python -m bot.main                       # fontes reais (secrets do Actions)
  python -m bot.main --csv tests/fixtures/feed_exemplo.csv --sem-imagem   # ensaio local

Publicação no TikTok/Instagram fica DESLIGADA até existirem as credenciais das contas
comerciais (PUBLICAR=1 + tokens). Até lá os arquivos saem em saida/ e viram artefato do Actions.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
from datetime import datetime, timezone

from . import arte, video
from .fontes import FonteArquivo, fontes_padrao
from .selecao import escolher

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(RAIZ, "data")


def ler_json(nome, padrao):
    caminho = os.path.join(DATA, nome)
    if not os.path.exists(caminho):
        return padrao
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def gravar_json(nome, dados):
    with open(os.path.join(DATA, nome), "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
        f.write("\n")


def titulo_curto(titulo: str, max_palavras: int = 6) -> str:
    t = re.sub(r"[\[\(\{].*?[\]\)\}]", " ", titulo)
    t = re.sub(r"[^\w\s\-,áéíóúâêôãõçÁÉÍÓÚÂÊÔÃÕÇ]", " ", t)
    palavras = [p for p in t.split() if len(p) > 1 or p.isdigit()]
    return " ".join(palavras[:max_palavras]) or titulo[:40]


def escolher_gancho(nicho: dict | None, ganchos: dict, usados: set[str], rnd: random.Random) -> str:
    opcoes = list((nicho or {}).get("ganchos", [])) + list(ganchos.get("gerais", []))
    sazonais = ganchos.get("sazonais", {})
    hoje = datetime.now(timezone.utc).strftime("%m-%d")
    for faixa, lista in sazonais.items():
        ini, _, fim = faixa.partition("_")
        if ini <= hoje <= fim:
            opcoes = list(lista) + opcoes
    opcoes = [g for g in opcoes if g] or ["Achei e é barato"]
    livres = [g for g in opcoes if g not in usados] or opcoes
    return arte.gancho_curto(livres[0] if rnd.random() < 0.5 else rnd.choice(livres))


def legenda(gancho: str, p: dict, nicho: dict | None) -> str:
    tags = ["#achadinhos", "#achadinhosshopee", "#achadosbaratos", "#comprinhas"]
    tags += [t for t in (nicho or {}).get("hashtags", []) if t not in tags]
    preco = arte.preco_br(p["preco"])
    antes = f" (era {arte.preco_br(p['preco_original'])})" if p.get("preco_original", 0) > p["preco"] * 1.05 else ""
    return (f"{gancho} 👀\n{titulo_curto(p['titulo'], 10)} por {preco}{antes}.\n"
            f"{arte.FALA_FINAL}\n\nLink de afiliado: posso ganhar comissão sem custo extra para você.\n"
            f"Preço e estoque podem mudar.\n\n{' '.join(tags[:8])}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", help="CSV local no lugar dos feeds (ensaio)")
    ap.add_argument("--quantidade", type=int, default=int(os.getenv("POSTS_POR_RODADA", "1")))
    ap.add_argument("--saida", default=os.path.join(RAIZ, "saida"))
    ap.add_argument("--sem-video", action="store_true")
    ap.add_argument("--sem-imagem", action="store_true", help="não baixa foto (teste offline)")
    ap.add_argument("--nao-gravar", action="store_true", help="não atualiza historico/relatorio")
    args = ap.parse_args(argv)

    agora = datetime.now(timezone.utc)
    os.makedirs(args.saida, exist_ok=True)
    nichos = ler_json("nichos.json", {"nichos": []})["nichos"]
    ganchos = ler_json("ganchos.json", {})
    historico = ler_json("historico.json", [])

    fontes = [FonteArquivo(args.csv, "arquivo")] if args.csv else fontes_padrao()
    produtos, rel_fontes = [], {}
    for fonte in fontes:
        if not fonte.disponivel():
            rel_fontes[fonte.nome] = {"ok": False, "produtos": 0, "erro": "não configurada"}
            continue
        lista = fonte.produtos()
        produtos.extend(lista)
        rel_fontes[fonte.nome] = {"ok": bool(lista), "produtos": len(lista),
                                  "colunas": fonte.colunas[:60], "erro": fonte.erro}
        # Só o resumo: nunca a URL do feed.
        print(f"fonte {fonte.nome}: {len(lista)} produtos; colunas={fonte.colunas[:60]}"
              + (f"; erro={fonte.erro}" if fonte.erro else ""))

    escolhidos, bloqueios = escolher(produtos, nichos, historico, args.quantidade, agora)
    print(f"candidatos={len(produtos)} bloqueios={bloqueios} escolhidos={len(escolhidos)}")

    rnd = random.Random()
    usados = {h.get("gancho") for h in historico[-30:]}
    gerados = []
    carimbo = agora.strftime("%Y%m%d-%H%M")
    for i, (p, nicho) in enumerate(escolhidos, 1):
        pd = p.as_dict()
        gancho = escolher_gancho(nicho, ganchos, usados, rnd)
        usados.add(gancho)
        base = os.path.join(args.saida, f"{carimbo}-{i}")
        img = None if args.sem_imagem else arte.baixar_imagem(p.imagem)
        capa = arte.gerar_capa(pd, gancho, img, base + "-capa.png")
        final = arte.gerar_final(base + "-final.png")
        mp4 = None
        if not args.sem_video:
            fala = video.roteiro(gancho, titulo_curto(p.titulo), arte.preco_br(p.preco))
            audio = base + "-voz.mp3"
            tem_voz = video.locucao(fala, audio)
            mp4 = video.gerar_video(capa, final, base + ".mp4", audio if tem_voz else None)
            os.remove(final)
            if tem_voz:
                os.remove(audio)
        with open(base + "-legenda.txt", "w", encoding="utf-8") as f:
            f.write(legenda(gancho, pd, nicho) + f"\n\nLINK PARA A BIO: {p.link}\n")
        item = {"id": p.id, "quando": agora.isoformat(timespec="seconds"), "titulo": p.titulo,
                "preco": p.preco, "nicho": (nicho or {}).get("nome", ""), "gancho": gancho,
                "fonte": p.fonte, "oficial": p.oficial, "link": p.link,
                "arquivos": [os.path.basename(x) for x in (capa, mp4) if x], "publicado": False}
        gerados.append(item)
        print(f"gerado: {item['nicho'] or '-'} | {gancho} | {arte.preco_br(p.preco)} | {p.titulo[:60]}")

    publicar = os.getenv("PUBLICAR", "0") == "1"
    status_pub = "desligada (aguardando credenciais das contas comerciais)"
    if publicar:
        status_pub = "PUBLICAR=1, mas o módulo de publicação ainda não existe: nada foi postado"

    relatorio = {
        "quando": agora.isoformat(timespec="seconds"),
        "fontes": rel_fontes,
        "candidatos": len(produtos),
        "bloqueios": bloqueios,
        "gerados": [{k: v for k, v in g.items() if k != "link"} for g in gerados],
        "publicacao": status_pub,
    }
    if not args.nao_gravar:
        historico.extend(gerados)
        # guarda só 60 dias
        historico = [h for h in historico if (agora - datetime.fromisoformat(h["quando"])).days <= 60]
        gravar_json("historico.json", historico)
        gravar_json("relatorio.json", relatorio)
    with open(os.path.join(args.saida, "relatorio.json"), "w", encoding="utf-8") as f:
        json.dump(relatorio, f, ensure_ascii=False, indent=2)

    if not produtos:
        print("ERRO: nenhuma fonte trouxe produtos", file=sys.stderr)
        return 2
    if not gerados:
        print("ERRO: nenhum produto passou nos filtros", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
