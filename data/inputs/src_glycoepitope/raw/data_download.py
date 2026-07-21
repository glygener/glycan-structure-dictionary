import requests
from pathlib import Path

url = "https://glycosmos.org/glycoepitope.tsv?action=index&controller=glycoepitopes&page=1"
out_dir = Path(__file__).parent
out_path = out_dir / "glycoepitope.tsv"

def fetch_data(url: str):
    r = requests.get(url, timeout=120) # Takes time
    r.raise_for_status()
    return r

def import_glycoepitope(url: str, out_dir: Path) -> None:
    with open(out_path, "wb") as f:
        read = fetch_data(url)
        f.write(read.content)

if __name__ == "__main__":
    import_glycoepitope(url, out_dir=out_dir)
    print(f"Saved to {out_path}")