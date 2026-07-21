from __future__ import annotations

import csv
import time
from pathlib import Path
from urllib.parse import quote_plus, urljoin

import requests
import urllib3
from bs4 import BeautifulSoup


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://glyco3d.cermav.cnrs.fr"
SEARCH_PAGE_URL = f"{BASE_URL}/search.php?type=bioligo"
SEARCH_ENDPOINT = f"{BASE_URL}/request/request_multicriteria.php"


def get_categories() -> list[str]:
    return [
        "Blood group A antigens",
        "Blood group B antigens",
        "Blood group H antigens (Blood group O)",
        "Blood group H antigens (Blood group O) and Globo H tetraose",
        "Core structures ",
        "Core structures (Type 1 & Type 2)",
        "Core structures (Type 1)",
        "Core structures (Type 2)",
        "Core structures (Type 4)",
        "Fucosylated oligosaccharides",
        "Fucosylated oligosaccharides (3 Fucosyllactose core)",
        "Fucosylated oligosaccharides (Lacto-Series)",
        "GAGs",
        "Gala-3Gal oligosaccharides (Galili and xeno antigens)",
        "Gala-3Gal oligosaccharides (Isogloboseries)",
        "Ganglioside sugars",
        "Globoside sugars (P antigens) (Forssman antigens)",
        "Globoside sugars (P antigens) (Globo series - core structure type 4)",
        "Globoside sugars (P antigens) (P blood group antigens and analogues)",
        "Globoside sugars (P antigens) (Stage-specific Embryonic antigens : SSEA-3 & SSEA-4)",
        "Glucuronylated oligosaccharides",
        "Glycosphingolipid",
        "Lewis antigens",
        "Miscellaneous",
        "Miscellaneous (Blood group-related oligosaccharides)",
        "Miscellaneous (Chitin oligosaccharides)",
        "Miscellaneous (Fibriniogen related oligosaccharides)",
        "Miscellaneous (LDN-related oligosaccharides)",
        "Miscellaneous (Lewis X-related oligosaccharides)",
        "Miscellaneous (TF-related oligosaccharides)",
        "Miscellaneous (TN-related oligosaccharides)",
        "Miscellaneous (Trehalose-like sugars)",
        "N-linked oligos",
        "Sialylated oligosaccharide (Type 1)",
        "Sialylated oligosaccharide (Type 2)",
    ]


def make_session() -> requests.Session:
    session = requests.Session()
    session.verify = False
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:148.0) Gecko/20100101 Firefox/148.0",
        "Accept": "*/*",
        "Accept-Language": "en-GB,en;q=0.9",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": BASE_URL,
        "Referer": SEARCH_PAGE_URL,
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    })
    return session


def fix_mojibake(text: str) -> str:
    if not isinstance(text, str):
        return text
    try:
        return text.encode("latin1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def normalize_primes(text: str) -> str:
    if not isinstance(text, str):
        return text
    replacements = {
        "'": "′",
        "’": "′",
        "‛": "′",
        "´": "′",
        "`": "′",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def normalize_text(text: str) -> str:
    text = " ".join(text.split()).strip()
    return normalize_primes(fix_mojibake(text))


def prime_session(session: requests.Session) -> None:
    r = session.get(SEARCH_PAGE_URL, timeout=30)
    r.raise_for_status()


def build_raw_payload(category: str) -> str:
    # Browser payload pattern:
    # query=+AND+category+%3D%22Blood+group+B+antigens%22&type=bioligo
    query_value = f' AND category ="{category}"'
    return f"query={quote_plus(query_value)}&type=bioligo"


def fetch_category_results(session: requests.Session, category: str) -> BeautifulSoup:
    payload = build_raw_payload(category)

    r = session.post(
        SEARCH_ENDPOINT,
        data=payload,   # raw encoded body, not dict
        timeout=30,
    )
    r.raise_for_status()

    # debug hook
    print(f"    response length = {len(r.text)}")

    return BeautifulSoup(r.text, "html.parser")


def parse_result_list(soup: BeautifulSoup) -> list[dict]:
    records: list[dict] = []

    for slide in soup.select("section.slide"):
        a = slide.find("a", href=True)
        if not a:
            continue

        name_span = a.select_one("span.name")
        name = name_span.get_text(" ", strip=True) if name_span else a.get_text(" ", strip=True)
        name = name.replace("bioligo", "").strip()

        records.append({
            "name": normalize_text(name),
            "detail_url": urljoin(BASE_URL, a["href"]),
        })

    return records


def parse_property_table(soup: BeautifulSoup) -> dict[str, str]:
    data: dict[str, str] = {}

    for tr in soup.find_all("tr"):
        prop = tr.find("td", class_="propriete")
        val = tr.find("td", class_="valeur")
        if not prop or not val:
            continue

        key = prop.get_text(" ", strip=True)

        val_copy = BeautifulSoup(str(val), "html.parser")
        for a in val_copy.find_all("a"):
            a.decompose()

        data[key] = normalize_text(val_copy.get_text(" ", strip=True))

    return data


def scrape_detail(session: requests.Session, detail_url: str) -> dict:
    r = session.get(detail_url, timeout=30)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    props = parse_property_table(soup)

    return {
        "name": props.get("Name", ""),
        "sequence": props.get("Sequence", ""),
        "category": props.get("Category", ""),
        "detail_url": detail_url,
    }


def scrape_all() -> list[dict]:
    session = make_session()
    prime_session(session)

    rows: list[dict] = []
    seen_urls: set[str] = set()

    for category in get_categories():
        print(f"\n[Category] {category!r}")

        try:
            soup = fetch_category_results(session, category)
            results = parse_result_list(soup)
            print(f"  Found {len(results)} result cards")
        except Exception as e:
            print(f"  [FAIL] category request :: {e}")
            time.sleep(3)
            continue

        for rec in results:
            if rec["detail_url"] in seen_urls:
                continue
            seen_urls.add(rec["detail_url"])

            try:
                row = scrape_detail(session, rec["detail_url"])
                if not row["name"]:
                    row["name"] = rec["name"]
                if not row["category"]:
                    row["category"] = normalize_text(category)
                rows.append(row)
                print(f"    [OK] {row['name']}")
            except Exception as e:
                print(f"    [FAIL] {rec['detail_url']} :: {e}")

            time.sleep(2)

        time.sleep(2)

    return rows


def save_tsv(rows: list[dict]) -> Path:
    out_path = Path(__file__).parent / "biooligo_glycans.tsv"
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["name", "sequence", "category", "detail_url"],
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerows(rows)
    return out_path


def main() -> None:
    rows = scrape_all()
    out_path = save_tsv(rows)
    print(f"\nSaved {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    main()