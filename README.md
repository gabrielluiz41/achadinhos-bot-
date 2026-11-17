# Robô de achadinhos — @acheiebarato.oficial

Gera, 3x por dia (12h07, 18h07 e 21h07 de Brasília), vídeos verticais 1080x1920 com capa,
locução e legenda de produtos baratos do feed de afiliado da Shopee.

**Publicação no TikTok/Instagram: DESLIGADA** até o cadastro das credenciais das contas comerciais.
Até lá cada rodada sai como artefato do Actions (aba Actions > rodada > Artifacts) para revisão.

## Como funciona
1. `bot/fontes.py` baixa os feeds pelos secrets `SHOPEE_FEED_URL_OFICIAL` (prioridade, lojas oficiais)
   e `SHOPEE_FEED_URL_BRASIL`. Os valores dos secrets nunca são impressos nem gravados.
   2ª fonte: Open API do afiliado (GraphQL `productOfferV2`), liga sozinha quando existirem os secrets
   `SHOPEE_APP_ID` e `SHOPEE_SECRET`; busca pelo 1º termo de cada nicho. A API traz só 1 imagem (sem galeria/vídeo).
2. `bot/filtro.py` barra saúde/remédio/suplemento/emagrecedor, armas/facas, adulto, réplica,
   vape/cigarro e cadeirinha/bebê conforto.
3. `bot/selecao.py` cruza com `data/nichos.json`, pontua (loja oficial, desconto, vendas, nota, preço)
   e nunca repete produto em 14 dias (`data/historico.json`).
4. `bot/arte.py` monta a capa (faixa amarela com gancho de até 5 palavras, produto recortado,
   preço em etiqueta laranja, rodapé "@acheiebarato.oficial · link de afiliado na bio").
5. `bot/video.py` faz o vídeo (capa com zoom lento + cartão "Achei, e é barato! Link na bio.")
   com locução pt-BR (edge-tts; sem ela, vídeo mudo).
6. `data/relatorio.json` guarda o resumo da última rodada (colunas do feed, bloqueios, gerados).

## Garimpeiro
Edite `data/nichos.json` (termos, peso, ganchos, hashtags) e `data/ganchos.json` (gerais e sazonais).

## Local
```
pip install -r requirements.txt   # precisa de ffmpeg
python -m pytest -q
TTS=0 python -m bot.main --csv tests/fixtures/feed_exemplo.csv --sem-imagem --nao-gravar
```

Fonte Montserrat (SIL OFL, `assets/fonts/OFL.txt`).

## Vitrine (link da bio) e políticas
Cada rodada regenera `docs/` a partir de `data/historico.json`: `index.html` (achadinhos dos últimos 14 dias,
com link de afiliado), `privacidade.html` e `termos.html` (pt-BR e inglês, exigidos na auditoria do TikTok e no app Meta).
Para publicar: Settings > Pages > Deploy from a branch > `main` / `/docs`. GitHub Pages em repositório privado
exige plano pago; no plano grátis, torne o repositório público (não há segredos no código) ou use um repositório público só para a vitrine.
