#!/usr/bin/env python3
"""Monta minha-lista.m3u a partir das listas públicas do iptv-org (Brasil).

Uso:
  python scripts/montar_lista.py                      # baixa as fontes da internet
  python scripts/montar_lista.py --src-dir PASTA      # usa arquivos locais (br.m3u, ...)
  python scripts/montar_lista.py --check              # testa cada link e remove os mortos
"""
import argparse, re, sys, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE = "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/"
# (arquivo, grupo padrão)
FONTES = [
    ("br.m3u", "Brasil"),
    ("br_pluto.m3u", "Pluto TV"),
    ("br_samsung.m3u", "Samsung TV Plus"),
]
# palavras-chave -> grupo (só para fontes "Brasil"); a primeira que casar vence
CATEGORIAS = [
    ("Notícias", ["news", "noticia", "notícia", "jornal", "cnn", "band news", "tv câmara", "tv camara", "tv senado", "agro", "canal rural"]),
    ("Infantil", ["kids", "infantil", "cartoon", "desenho", "baby", "turma", "gloob", "anime"]),
    ("Esportes", ["sport", "esporte", "futebol", "fut ", "arena", "copa", "motor", "nba", "ufc", "fight"]),
    ("Música", ["music", "música", "musica", "mtv", "trace", "hits", "radio", "rádio", "fm "]),
    ("Religioso", ["igreja", "gospel", "catól", "catol", "canção nova", "cancao nova", "rede vida", "evang", "deus", "fé", "fe tv", "aparecida"]),
    ("Filmes e Séries", ["movie", "filme", "cinema", "cine ", "série", "serie", "drama", "novela", "terror", "horror"]),
]
UA = "Mozilla/5.0 (compatible; minha-iptv-checker)"

# Redes comerciais e TV paga que só têm transmissão oficial em app/site próprio.
# Links soltos desses canais em servidores de terceiros são retransmissão sem
# autorização, então ficam de fora. Edite com cuidado.
EXCLUIR = re.compile(
    r"globo|sbt|record|\bband\b|bandnews|band sports|bandeirantes|rede ?tv|cnn|espn|combate|"
    r"premiere|sportv|telecine|hbo|max\b|megapix|\bgnt\b|multishow|viva\b|gloob|"
    r"discovery|disney|warner|\btnt\b|\bfox\b|\bfx\b|amc\b|axn|sony|space\b|"
    r"paramount|nickelodeon|cartoon network|history|\ba&e\b|national geographic|"
    r"tcm|nick|ge fast|tv bahia|tv a critica|canal off|bis\b|studio universal|universal|comedy central|mtv|playboy|sexy|adult|xxx",
    re.I,
)
# Host que é só um número IP (ex.: http://45.162.64.114/...) = servidor de revenda, descartado.
HOST_IP = re.compile(r"^https?://\d{1,3}(\.\d{1,3}){3}[:/]")


def ler(src_dir, nome):
    if src_dir:
        return (Path(src_dir) / nome).read_text(encoding="utf-8", errors="replace")
    req = urllib.request.Request(BASE + nome, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", errors="replace")


def parse(texto):
    """Devolve lista de (extinf, [linhas_opt], url)."""
    itens, extinf, opts = [], None, []
    for linha in texto.replace("\r", "").split("\n"):
        linha = linha.strip()
        if not linha or linha.startswith("#EXTM3U"):
            continue
        if linha.startswith("#EXTINF"):
            extinf, opts = linha, []
        elif linha.startswith("#"):
            opts.append(linha)
        elif extinf and re.match(r"https?://", linha):
            itens.append((extinf, opts, linha))
            extinf, opts = None, []
    return itens


def nome_do(extinf):
    return extinf.rsplit(",", 1)[-1].strip()


def grupo_de(nome, padrao):
    if padrao != "Brasil":
        return padrao
    n = nome.lower()
    for g, palavras in CATEGORIAS:
        if any(p in n for p in palavras):
            return g
    return "Geral"


def viva(item):
    _, opts, url = item
    headers = {"User-Agent": UA}
    for o in opts:  # respeita referer / user-agent exigidos pelo canal
        if o.startswith("#EXTVLCOPT:http-referrer="):
            headers["Referer"] = o.split("=", 1)[1]
        elif o.startswith("#EXTVLCOPT:http-user-agent="):
            headers["User-Agent"] = o.split("=", 1)[1]
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as r:
            if r.status != 200:
                return False
            corpo = r.read(2048)
        return b"#EXTM3U" in corpo or b"#EXT-X" in corpo or len(corpo) > 0 and url.endswith((".ts", ".mp4"))
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src-dir")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--out", default="minha-lista.m3u")
    a = ap.parse_args()

    vistos, canais = set(), []
    for arquivo, grupo in FONTES:
        try:
            itens = parse(ler(a.src_dir, arquivo))
        except Exception as e:
            print(f"aviso: não consegui ler {arquivo}: {e}", file=sys.stderr)
            continue
        for extinf, opts, url in itens:
            if url in vistos:
                continue
            vistos.add(url)
            nome = nome_do(extinf)
            if EXCLUIR.search(nome) or HOST_IP.match(url):
                continue
            g = grupo_de(nome, grupo)
            extinf = re.sub(r'\s+group-title="[^"]*"', "", extinf)
            extinf = extinf.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{g}"', 1)
            canais.append((g, nome.lower(), (extinf, opts, url)))

    total = len(canais)
    if not total:
        sys.exit("nenhum canal lido; mantendo a lista anterior")

    if a.check:
        with ThreadPoolExecutor(max_workers=40) as ex:
            ok = list(ex.map(lambda c: viva(c[2]), canais))
        vivos = [c for c, o in zip(canais, ok) if o]
        print(f"{len(vivos)} de {total} links responderam")
        # trava de segurança: se menos de 20% responder, é falha de rede, não de canais
        if len(vivos) < total * 0.2:
            sys.exit("menos de 20% dos links responderam; mantendo a lista anterior")
        canais = vivos

    canais.sort(key=lambda c: (c[0], c[1]))
    linhas = ["#EXTM3U"]
    for _, _, (extinf, opts, url) in canais:
        linhas += [extinf, *opts, url]
    Path(a.out).write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print(f"{len(canais)} canais gravados em {a.out}")


if __name__ == "__main__":
    main()
