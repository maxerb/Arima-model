"""T1.3: download the paper PDF (Huwiler & Kaufmann 2013) so its appendix tables can be transcribed and checked.

Source: SNB Economic Studies 7/2013 (public, no login, checked 2026-11-24). Saved untouched to
data/raw/economic_studies_2013_07_<date>.pdf; skipped if already present (idempotent).
"""

from datetime import date

import requests

from arima_snb.config import RAW

URL = ("https://www.snb.ch/public/asset/de/www-snb-ch/publications/research/economic-studies/2013/03/"
       "economic_studies_2013_07/publications0/economic_studies_2013_07.n.pdf")


def main() -> None:
    existing = sorted(RAW.glob("economic_studies_2013_07_*.pdf"))
    if existing:
        print(f"present: {existing[-1].name}")
        return
    r = requests.get(URL, timeout=120)
    r.raise_for_status()
    assert r.content[:4] == b"%PDF", "response is not a PDF"
    out = RAW / f"economic_studies_2013_07_{date.today():%Y-%m-%d}.pdf"
    out.write_bytes(r.content)
    print(f"saved {out.name} ({len(r.content) / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
