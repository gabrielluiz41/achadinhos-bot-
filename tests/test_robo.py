import json
import os
from datetime import datetime, timedelta, timezone

from PIL import Image

from bot import arte
from bot.filtro import motivo_bloqueio
from bot.fontes import FonteArquivo, parse_csv
from bot.main import main
from bot.selecao import escolher

AQUI = os.path.dirname(__file__)
CSV = os.path.join(AQUI, "fixtures", "feed_exemplo.csv")


def _produtos():
    return FonteArquivo(CSV).produtos()


def test_parse_feed_colunas_e_campos():
    ps = _produtos()
    assert len(ps) == 8
    p = ps[0]
    assert p.id == "9-1001" and p.preco == 24.90 and p.preco_original == 59.90
    assert p.oficial is True and p.link.startswith("https://s.shopee.com.br/")


def test_parse_ponto_e_virgula_e_virgula_decimal():
    txt = "item_id;item_name;price;sale_price;product_link\n1;Mop giratório;49,90;29,90;https://x/1\n"
    ps, cols = parse_csv(txt, "t")
    assert cols[0] == "item_id" and ps[0].preco == 29.9 and ps[0].desconto == 40


def test_filtro_proibidos():
    assert motivo_bloqueio("Suplemento Termogênico Emagrecedor") == "saude"
    assert motivo_bloqueio("Faca Tática Inox") == "armas"
    assert motivo_bloqueio("Vape Pod Descartável") == "fumo"
    assert motivo_bloqueio("Cadeirinha Infantil Para Carro") == "bebe_seguranca"
    assert motivo_bloqueio("Bolsa Réplica Primeira Linha") == "replica"
    assert motivo_bloqueio("Conjunto Lingerie Sensual") == "adulto"
    # falsos positivos que não podem bloquear
    assert motivo_bloqueio("Armário Organizador de Sapatos") is None
    assert motivo_bloqueio("Camiseta Sexta-feira Feliz") is None
    assert motivo_bloqueio("Tapete Fácil de Lavar") is None
    assert motivo_bloqueio("Copo Térmico Inox") is None


def test_escolha_sem_repetir_14_dias():
    agora = datetime(2026, 11, 20, tzinfo=timezone.utc)
    ps = _produtos()
    hist = [{"id": "9-1004", "quando": (agora - timedelta(days=3)).isoformat()},
            {"id": "9-1001", "quando": (agora - timedelta(days=20)).isoformat()}]
    nichos = json.load(open(os.path.join(AQUI, "..", "data", "nichos.json"), encoding="utf-8"))["nichos"]
    esc, bloq = escolher(ps, nichos, hist, 10, agora, seed=1)
    ids = {p.id for p, _ in esc}
    assert "9-1004" not in ids  # postado há 3 dias
    assert "9-1001" in ids      # há 20 dias pode voltar
    assert not ids & {"9-1002", "9-1003", "9-1007", "9-1008"}
    assert bloq["repetido_14d"] == 1


def test_capa_1080x1920(tmp_path):
    img = Image.new("RGBA", (800, 800), (255, 255, 255, 255))
    img.paste((30, 120, 220, 255), (200, 200, 600, 600))
    p = {"titulo": "Fita LED 5m RGB com Controle Remoto Bluetooth", "preco": 24.9, "preco_original": 59.9}
    out = arte.gerar_capa(p, "Casa de Natal gastando pouco hoje mesmo", img, str(tmp_path / "c.png"))
    im = Image.open(out)
    assert im.size == (1080, 1920)
    assert im.getpixel((5, 5)) == arte.LARANJA
    assert arte.gancho_curto("um dois tres quatro cinco seis") == "um dois tres quatro cinco"
    assert arte.preco_br(1499.0) == "R$ 1.499,00"


def test_rodada_completa_offline(tmp_path, monkeypatch):
    monkeypatch.setenv("TTS", "0")
    rc = main(["--csv", CSV, "--quantidade", "2", "--saida", str(tmp_path), "--sem-imagem", "--nao-gravar"])
    assert rc == 0
    arquivos = sorted(os.listdir(tmp_path))
    assert sum(a.endswith(".mp4") for a in arquivos) == 2
    assert sum(a.endswith("-capa.png") for a in arquivos) == 2
    leg = open(tmp_path / [a for a in arquivos if a.endswith("-legenda.txt")][0], encoding="utf-8").read()
    assert "Achei, e é barato! Link na bio." in leg and "afiliado" in leg
    rel = json.load(open(tmp_path / "relatorio.json", encoding="utf-8"))
    assert rel["publicacao"].startswith("desligada")


def test_feed_com_quebra_de_linha_e_crlf():
    txt = ('itemid,shopid,title,description,price,sale_price,product_link\r\n'
           '1,2,"Mop Giratório","linha 1\r\nlinha 2, com vírgula",49.90,29.90,https://x/1\r\n'
           "3,4,Escorredor d'água,\"desc 'aspas'\",19.90,9.90,https://x/3\r\n")
    ps, cols = parse_csv(txt, "t")
    assert cols[3] == "description" and [p.id for p in ps] == ["2-1", "4-3"]


def test_vitrine_e_politicas(tmp_path):
    from bot import vitrine
    agora = datetime(2026, 11, 15, 12, tzinfo=timezone.utc)
    hist = [
        {"id": "1", "quando": (agora - timedelta(days=1)).isoformat(), "titulo": "Pisca <b>pisca</b>",
         "preco": 19.9, "preco_original": 39.9, "link": "https://s.shopee.com.br/abc", "imagem": "https://cf.shopee/x.jpg"},
        {"id": "2", "quando": (agora - timedelta(days=20)).isoformat(), "titulo": "Velho",
         "preco": 9.9, "link": "https://s.shopee.com.br/old"},
        {"id": "3", "quando": agora.isoformat(), "titulo": "Sem link seguro", "preco": 5.0,
         "link": "javascript:alert(1)"},
    ]
    arquivos = vitrine.gerar_site(hist, str(tmp_path), agora)
    assert len(arquivos) == 3
    idx = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "https://s.shopee.com.br/abc" in idx and 'rel="sponsored noopener nofollow"' in idx
    assert "Velho" not in idx and "javascript:" not in idx
    assert "<b>pisca</b>" not in idx and "&lt;b&gt;" in idx
    assert "R$ 19,90" in idx
    priv = (tmp_path / "privacidade.html").read_text(encoding="utf-8")
    assert "Privacy Policy" in priv and "Política de Privacidade" in priv
    assert "Terms of Use" in (tmp_path / "termos.html").read_text(encoding="utf-8")
    assert (tmp_path / ".nojekyll").exists()


def test_qualidade_outlet_defeito_e_desconto_suspeito():
    assert motivo_bloqueio("Outlet Necessaire Gocase Makeup Pequenos Defeitos") == "qualidade"
    assert motivo_bloqueio("Panela com avaria na embalagem") == "qualidade"
    assert motivo_bloqueio("Luminária de mostruário") == "qualidade"
    assert motivo_bloqueio("Vestido com detalhes dourados") is None
    from bot.fontes import Produto
    agora = datetime(2026, 11, 20, tzinfo=timezone.utc)
    inflado = Produto(id="1-1", titulo="Strobo Pisca Pisca 300 Leds", preco=99.99, preco_original=699.9,
                      link="https://s.shopee.com.br/a", imagem="https://x/1.jpg")
    normal = Produto(id="1-2", titulo="Pisca Pisca 100 Leds", preco=19.9, preco_original=39.9,
                     link="https://s.shopee.com.br/b", imagem="https://x/2.jpg")
    esc, bloq = escolher([inflado, normal], [], [], 2, agora, seed=1)
    assert [p.id for p, _ in esc] == ["1-2"] and bloq["desconto_suspeito"] == 1


def test_preco_de_e_foto_boa():
    assert arte.mostrar_preco_de(19.9, 39.9) is True
    assert arte.mostrar_preco_de(99.99, 699.9) is False   # 86%: parece inflado
    assert arte.mostrar_preco_de(19.9, 0) is False
    assert arte.foto_boa(Image.new("RGB", (800, 600))) is True
    assert arte.foto_boa(Image.new("RGB", (800, 400))) is False
    assert arte.foto_boa(None) is False


def test_portao_de_foto_troca_produto(tmp_path, monkeypatch):
    monkeypatch.setenv("TTS", "0")
    from bot import main as m
    chamadas = []

    def falsa(url, timeout=30):
        chamadas.append(url)
        return Image.new("RGBA", (300, 300)) if len(chamadas) == 1 else Image.new("RGBA", (900, 900))
    monkeypatch.setattr(m.arte, "baixar_imagem", falsa)
    rc = m.main(["--csv", CSV, "--quantidade", "1", "--saida", str(tmp_path), "--sem-video", "--nao-gravar"])
    assert rc == 0 and len(chamadas) == 2
    rel = json.load(open(tmp_path / "relatorio.json", encoding="utf-8"))
    assert rel["bloqueios"]["sem_foto_boa"] == 1 and len(rel["gerados"]) == 1


def test_vitrine_sem_foto_e_sem_preco_inflado(tmp_path):
    from bot import vitrine
    agora = datetime(2026, 11, 15, 12, tzinfo=timezone.utc)
    hist = [
        {"id": "3", "quando": agora.isoformat(), "titulo": "Outlet Necessaire Pequenos Defeitos", "preco": 9.9,
         "link": "https://s.shopee.com.br/c", "imagem": "https://cf.shopee/c.jpg"},
        {"id": "1", "quando": agora.isoformat(), "titulo": "Sem foto", "preco": 19.9,
         "link": "https://s.shopee.com.br/a"},
        {"id": "2", "quando": agora.isoformat(), "titulo": "Strobo", "preco": 99.99, "preco_original": 699.9,
         "link": "https://s.shopee.com.br/b", "imagem": "https://cf.shopee/b.jpg"},
    ]
    vitrine.gerar_site(hist, str(tmp_path), agora)
    idx = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "Sem foto" not in idx and "Strobo" in idx and "R$ 699,90" not in idx and "Outlet" not in idx
