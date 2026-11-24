"""T1.1: download the BFS/SFSO CPI (LIK) detail results for every basket and the weights file.

Source page (checked 2026-11-24):
https://www.bfs.admin.ch/bfs/de/home/statistiken/preise/landesindex-konsumentenpreise/detailresultate.html

Each basket revision has its own "Detailresultate seit 1982" XLSX with all positions (down to the lowest published
level) on one index base. We need every base from 1993 on, because item codes and weights change between baskets and
the panel is chain-linked later (T1.4, skill snb-arima-cpi-panel). The DAM asset ids below are what the page linked to
on the check date; BFS replaces an asset id when it updates a file, so if a download 404s, look the id up again there.

Files are saved untouched in data/raw/ as `<code>_<asset>_<download date>.<ext>` (AGENTS.md rule 4).
Already-present files are not downloaded again, so the script is idempotent.
"""

from datetime import date

import requests

from arima_snb.config import RAW

DAM = "https://dam-api.bfs.admin.ch/hub/api/dam/assets/{asset}/master"

# code -> DAM asset id (BFS file code in square brackets on the page)
ASSETS = {
    "LIK93B93": 205911,      # base May 1993 = 100, basket 1993
    "LIK00B00": 228983,      # base May 2000 = 100, basket 2000
    "LIK05B05": 214275,      # base Dec 2005 = 100
    "LIK10B10": 255148,      # base Dec 2010 = 100
    "LIK15B15": 15964066,    # base Dec 2015 = 100
    "LIK20B20": 36366704,    # base Dec 2020 = 100
    "LIK25B25": 36970582,    # base Dec 2025 = 100 (current, updated monthly)
    "GEWICHTUNGEN": 36453530,  # weights of the baskets (detailed)
}


def download(code: str, asset: int) -> None:
    """Download one asset unless a file with the same code and asset id already exists."""
    existing = list(RAW.glob(f"{code}_{asset}_*"))
    if existing:
        print(f"{code}: present ({existing[0].name})")
        return
    r = requests.get(DAM.format(asset=asset), timeout=120)
    r.raise_for_status()
    # Extension from the content type / filename header; BFS serves .xlsx or old .xls
    cd = r.headers.get("content-disposition", "")
    ext = cd.rsplit(".", 1)[-1].strip('"; ') if "." in cd else "xlsx"
    path = RAW / f"{code}_{asset}_{date.today():%Y-%m-%d}.{ext}"
    path.write_bytes(r.content)
    assert path.stat().st_size > 10_000, f"{code}: suspiciously small file"
    print(f"{code}: saved {path.name} ({path.stat().st_size / 1e6:.1f} MB)")


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    for code, asset in ASSETS.items():
        download(code, asset)


if __name__ == "__main__":
    main()
