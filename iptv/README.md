# minha-iptv

Lista M3U de canais brasileiros gratuitos, montada a partir das listas públicas do
[iptv-org](https://github.com/iptv-org/iptv) (Brasil, Pluto TV e Samsung TV Plus).

- **Link para o player (VLC, TiviMate etc.):**
  `https://raw.githubusercontent.com/peresgabriel1207-byte/buildcores-open-db/claude/iptv-brasil-2026-y3adro/iptv/minha-lista.m3u`
- Atualiza todo dia pelo GitHub Actions (`.github/workflows/iptv-atualizar.yml`): baixa as fontes,
  testa cada link e remove os que não respondem.
- Redes comerciais e TV paga (Globo, SBT, Record, ESPN etc.) e servidores de revenda com IP puro
  são **excluídos** em `iptv/scripts/montar_lista.py`. Para ver esses canais, use os apps oficiais.
- Teste local: `python iptv/scripts/montar_lista.py --check --out iptv/minha-lista.m3u`
- Só canais de TV: canais de filme, série e anime em loop (Pluto TV e similares) ficam de fora.

## Adicionar canais por conta própria

Edite `iptv/meus-canais.m3u` (não edite `minha-lista.m3u`, que é reescrito todo dia). Cada canal são duas linhas:

```
#EXTINF:-1 group-title="Meus canais",Nome do canal
https://site.com/caminho/do/stream.m3u8
```

- Esses canais entram sempre na lista, sem filtro e sem teste de link.
- Se o canal exige referer ou user-agent, coloque antes da URL: `#EXTVLCOPT:http-referrer=https://site.com`.
- Use só transmissões que o próprio canal disponibiliza de graça.
