import csv
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup, Tag


BASE_URL = "https://sugarbind.expasy.org/ligands/{}"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def _fix_encodings(text: str) -> str:
    if not isinstance(text, str):
        return text
    try:
        return text.encode("latin1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def _normalize_primes(text: str) -> str:
    if not isinstance(text, str):
        return text
    replacements = {
        "'": "′",
        "’": "′",
        "´": "′",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def normalize_text(text: str) -> str:
    text = " ".join(text.split()).strip()
    return _normalize_primes(_fix_encodings(text))


def get_section_values(soup: BeautifulSoup, heading_text: str) -> list[str]:
    heading = None
    for h in soup.find_all(["h1", "h2", "h3", "h4"]):
        if h.get_text(" ", strip=True).lower() == heading_text.lower():
            heading = h
            break

    if heading is None:
        return []

    values: list[str] = []

    for sib in heading.next_siblings:
        if isinstance(sib, Tag):
            if sib.name in ["h1", "h2", "h3", "h4"]:
                break

            text = sib.get_text(" ", strip=True)
            if not text or text == "-":
                continue

            if sib.name in ["ul", "ol"]:
                for li in sib.find_all("li", recursive=False):
                    li_text = li.get_text(" ", strip=True)
                    if li_text and li_text != "-":
                        values.append(li_text)
            else:
                anchors = sib.find_all("a")
                if anchors:
                    anchor_texts = [
                        a.get_text(" ", strip=True)
                        for a in anchors
                        if a.get_text(" ", strip=True)
                    ]
                    if anchor_texts:
                        values.extend(anchor_texts)
                    else:
                        values.append(text)
                else:
                    values.append(text)

    seen = set()
    deduped: list[str] = []
    for v in values:
        v = normalize_text(v)
        if v and v not in seen:
            seen.add(v)
            deduped.append(v)

    return deduped


def scrape_ligand(ligand_id: int) -> dict:
    url = BASE_URL.format(ligand_id)
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    h1 = soup.find("h1")
    label = normalize_text(h1.get_text(" ", strip=True)) if h1 else ""
    
    glycan_references = get_section_values(soup, "Glycan references")
    # first glycan reference is usually GlyTouCan, second is GlyConnect
    
        
        

    return {
        "ligand_id": "SB" + str(ligand_id).zfill(4),
        "url": url,
        "label": label,
        "glycoconjugate_type": " | ".join(get_section_values(soup, "Glycoconjugate type")),
        "aglycon": " | ".join(get_section_values(soup, "Aglycon")),
        "ligand_types": " | ".join(get_section_values(soup, "Ligand Types")),
        "ligand_synonyms": " | ".join(get_section_values(soup, "Ligand synonyms")),
        "glycan_references:glytoucan": " | ".join(glycan_references[:1]),
        "glycan_references:glyconnect": " | ".join(glycan_references[1:]),
    }


def scrape_all_ligands() -> list[dict]:
    rows: list[dict] = []
    for ligand_id in range(1, 205): # Total 204 ligands
        try:
            row = scrape_ligand(ligand_id)
            rows.append(row)
            print(f"[OK] {ligand_id}: {row['label']}")
        except Exception as e:
            print(f"[FAIL] {ligand_id}: {e}")
        time.sleep(1)
    return rows


def save_tsv(rows: list[dict]) -> Path:
    out_path = Path(__file__).parent / "sugarbind_ligands.tsv"
    fieldnames = [
        "ligand_id",
        "url",
        "label",
        "glycoconjugate_type",
        "aglycon",
        "ligand_types",
        "ligand_synonyms",
        "glycan_references:glytoucan",
        "glycan_references:glyconnect",
    ]

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    return out_path


def main() -> None:
    rows = scrape_all_ligands()
    out_path = save_tsv(rows)
    print(f"Saved {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    main()