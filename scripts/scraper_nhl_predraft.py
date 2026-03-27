"""
Scraper de dados PRÉ-NHL de jogadores draftados (2015-2025).
Coleta stats acumuladas da carreira junior/college/europeia ANTES do draft.

Estratégia:
  1. Pegar lista de picks (sem filtro de liga) -> info básica de cada jogador
  2. Para cada liga pré-NHL relevante, pegar stats filtradas
  3. Combinar: para cada jogador, somar stats de todas as ligas pré-NHL

Fonte: Elite Prospects (eliteprospects.com)

Requisitos:
    pip install requests beautifulsoup4 pandas lxml

Uso:
    py scraper_nhl_predraft.py

Output:
    nhl_draft_predraft_stats.csv
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import re
import time
import random
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.5",
}

OUTPUT_FILE = "nhl_draft_predraft_stats.csv"
START_YEAR = 2015
END_YEAR = 2025

# Ligas pré-NHL mais comuns para jogadores draftados
PRE_NHL_LEAGUES = [
    "OHL", "WHL", "QMJHL",          # CHL (Canadian Hockey League)
    "USHL", "USDP",                   # US junior
    "NCAA",                            # College (H-East, Big Ten, NCHC, etc.)
    "SHL",                             # Swedish Hockey League
    "Liiga",                           # Finnish league
    "HockeyAllsvenskan",               # Swedish 2nd tier
    "NL",                              # Swiss National League
    "Czechia",                         # Czech Extraliga
    "Slovakia",                        # Slovak Extraliga
    "KHL",                             # Russia
    "MHL",                             # Russia junior
    "SuperElit",                       # Sweden junior
    "Jr. A SM-liiga",                  # Finland junior
    "DEL",                             # Germany
    "USHS-Prep", "USHS-MN",           # US High School
]


def fetch(url, delay=(2, 4)):
    """GET com delay e retry."""
    time.sleep(random.uniform(*delay))
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code == 200:
                return r
            if r.status_code == 429:
                time.sleep(20 * (attempt + 1))
            else:
                time.sleep(5)
        except requests.RequestException:
            time.sleep(10)
    return None


def extract_json(html):
    """Extrai __NEXT_DATA__ JSON do HTML."""
    m = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        html, re.DOTALL
    )
    if m:
        return json.loads(m.group(1))
    return None


def get_draft_picks(year):
    """Pega lista de todos os picks de um draft (sem filtro de liga)."""
    url = f"https://www.eliteprospects.com/draft/nhl-entry-draft/{year}"
    resp = fetch(url)
    if not resp:
        return []

    data = extract_json(resp.text)
    if not data:
        return []

    dts = data["props"]["pageProps"]["draftTypeSelectionStats"]["data"]
    picks = []

    for sel in dts.get("selections", []):
        player = sel.get("player", {})
        team = sel.get("team", {})
        nat = player.get("nationality", {})

        picks.append({
            "year": year,
            "overall_pick": sel.get("overall"),
            "round": sel.get("round"),
            "team": team.get("name", ""),
            "player": player.get("name", ""),
            "player_ep_id": str(player.get("id", "")),
            "position": player.get("position", ""),
            "nationality": (nat.get("slug", "") if isinstance(nat, dict) else "").upper()[:3],
        })

    return picks


def get_league_stats(year, league):
    """Pega stats de uma liga específica para um draft year."""
    url = f"https://www.eliteprospects.com/draft/nhl-entry-draft/{year}?league={league}"
    resp = fetch(url, delay=(1.5, 3))
    if not resp:
        return {}

    data = extract_json(resp.text)
    if not data:
        return {}

    dts = data["props"]["pageProps"]["draftTypeSelectionStats"]["data"]
    stats_map = {}  # player_id -> {GP, G, A, PTS, PIM, seasons}

    for stat in dts.get("stats", []):
        pid = str(stat.get("player", {}).get("id", ""))
        reg = stat.get("regularStats") or {}
        stats_map[pid] = {
            "seasons": stat.get("numberOfSeasons", 0) or 0,
            "GP": reg.get("GP", 0) or 0,
            "G": reg.get("G", 0) or 0,
            "A": reg.get("A", 0) or 0,
            "PTS": reg.get("PTS", 0) or 0,
            "PIM": reg.get("PIM", 0) or 0,
        }

    return stats_map


def scrape_year(year):
    """
    Scrape completo de um ano de draft:
    1. Pegar lista de picks
    2. Para cada liga pré-NHL, pegar stats
    3. Para cada jogador, pegar a liga com mais GP (principal)
    """
    logger.info(f"{'='*50}")
    logger.info(f"Draft {year}")
    logger.info(f"{'='*50}")

    picks = get_draft_picks(year)
    if not picks:
        logger.warning(f"Nenhum pick para {year}")
        return []

    logger.info(f"  {len(picks)} picks encontrados")

    # Coletar stats de cada liga
    all_league_stats = {}  # player_id -> {league: stats}
    for league in PRE_NHL_LEAGUES:
        stats = get_league_stats(year, league)
        if stats:
            logger.info(f"  Liga {league}: {len(stats)} jogadores com stats")
            for pid, st in stats.items():
                if pid not in all_league_stats:
                    all_league_stats[pid] = {}
                all_league_stats[pid][league] = st

    # Para cada jogador, escolher a liga com mais GP como "principal"
    # e somar stats de todas as ligas pré-NHL
    for pick in picks:
        pid = pick["player_ep_id"]
        league_stats = all_league_stats.get(pid, {})

        if not league_stats:
            pick.update({
                "amateur_league": "",
                "seasons_pre_nhl": None,
                "games_played": None,
                "goals": None,
                "assists": None,
                "points": None,
                "penalty_minutes": None,
            })
            continue

        # Somar stats de todas as ligas pré-NHL
        total_gp = sum(s["GP"] for s in league_stats.values())
        total_g = sum(s["G"] for s in league_stats.values())
        total_a = sum(s["A"] for s in league_stats.values())
        total_pts = sum(s["PTS"] for s in league_stats.values())
        total_pim = sum(s["PIM"] for s in league_stats.values())
        total_seasons = sum(s["seasons"] for s in league_stats.values())

        # Liga principal = a com mais GP
        main_league = max(league_stats, key=lambda l: league_stats[l]["GP"])

        pick.update({
            "amateur_league": main_league,
            "seasons_pre_nhl": total_seasons,
            "games_played": total_gp if total_gp > 0 else None,
            "goals": total_g if total_gp > 0 else None,
            "assists": total_a if total_gp > 0 else None,
            "points": total_pts if total_gp > 0 else None,
            "penalty_minutes": total_pim if total_gp > 0 else None,
        })

    with_stats = sum(1 for p in picks if p.get("games_played"))
    logger.info(f"  Resultado: {with_stats}/{len(picks)} jogadores com stats pré-NHL")
    return picks


def main():
    logger.info("=== Scraper NHL Draft Pre-Draft Stats ===")
    logger.info(f"Período: {START_YEAR}-{END_YEAR}")
    logger.info(f"Ligas pré-NHL: {len(PRE_NHL_LEAGUES)}")
    logger.info(f"Estimativa: ~{len(PRE_NHL_LEAGUES)} requests por ano, "
                f"~{len(PRE_NHL_LEAGUES) * (END_YEAR - START_YEAR + 1)} total")
    logger.info(f"Tempo estimado: ~{len(PRE_NHL_LEAGUES) * (END_YEAR - START_YEAR + 1) * 3 // 60} minutos\n")

    all_records = []

    for year in range(START_YEAR, END_YEAR + 1):
        records = scrape_year(year)
        all_records.extend(records)

        # Salvar progresso
        if all_records:
            df = pd.DataFrame(all_records)
            df.to_csv(OUTPUT_FILE, index=False)

    # DataFrame final
    df = pd.DataFrame(all_records)
    df = df.sort_values(["year", "overall_pick"]).reset_index(drop=True)

    # Calcular points per game
    mask = df["games_played"].notna() & (df["games_played"] > 0)
    df.loc[mask, "points_per_game"] = (
        df.loc[mask, "points"] / df.loc[mask, "games_played"]
    ).round(2)

    # Calcular goals per game
    df.loc[mask, "goals_per_game"] = (
        df.loc[mask, "goals"] / df.loc[mask, "games_played"]
    ).round(2)

    df.to_csv(OUTPUT_FILE, index=False)

    # Resumo
    total = len(df)
    with_stats = df["games_played"].notna().sum()
    logger.info(f"\n{'='*60}")
    logger.info(f"CONCLUÍDO! {total} jogadores, {with_stats} com stats pré-NHL ({with_stats/total*100:.0f}%)")
    logger.info(f"Arquivo: {OUTPUT_FILE}")
    logger.info(f"{'='*60}")

    # Preview
    print("\nPreview - Top 3 picks por ano:")
    for year in range(START_YEAR, END_YEAR + 1):
        ydf = df[df["year"] == year].head(3)
        print(f"\n  {year}:")
        for _, r in ydf.iterrows():
            gp = int(r["games_played"]) if pd.notna(r["games_played"]) else "-"
            g = int(r["goals"]) if pd.notna(r["goals"]) else "-"
            a = int(r["assists"]) if pd.notna(r["assists"]) else "-"
            pts = int(r["points"]) if pd.notna(r["points"]) else "-"
            ppg = f"{r['points_per_game']:.2f}" if pd.notna(r.get("points_per_game")) else "-"
            print(f"    #{r['overall_pick']:>3} {r['player']:<28} {r['position']:<3} "
                  f"{r['nationality']:<4} {r.get('amateur_league',''):<8} "
                  f"GP:{gp:>4} G:{g:>4} A:{a:>4} PTS:{pts:>4} PPG:{ppg}")


if __name__ == "__main__":
    main()
