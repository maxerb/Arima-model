"""T1.3 helper: render the paper's appendix pages (Tables 5-8, PDF pp. 19-23) to PNG for visual checking of the
collection-month columns (the 'x' marks cannot be located reliably from the PDF text layer).
Output: outputs/figures/paper_pages/page_<n>.png (gitignored outputs)."""

import pypdfium2 as pdfium

from arima_snb.config import FIGURES, RAW


def main(pages=range(19, 24), scale=2.5) -> None:
    pdf = pdfium.PdfDocument(sorted(RAW.glob("economic_studies_2013_07_*.pdf"))[-1])
    out = FIGURES / "paper_pages"
    out.mkdir(parents=True, exist_ok=True)
    for p in pages:
        pdf[p - 1].render(scale=scale).to_pil().save(out / f"page_{p}.png")
    print(f"rendered {len(pages)} pages to {out}")


if __name__ == "__main__":
    main()
