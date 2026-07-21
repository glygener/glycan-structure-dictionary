import requests
import urllib.parse

iupac_seq = "Neu5Ac(a2-3)Gal(b1-3)[Fuc(a1-4)]GlcNAc"
iupac_seq = "Gal(b1-4)Glc(b1-"
iupac_seq = "GlcNAc(b1-2)[GlcNAc(b1-6)]Man(a1-"
iupac_seq = "GlcNAc(b1-2)[GlcNAc(b1-6)]Man(a1-"

def get_glytoucan_id(iupac_seq: str) -> str:
    """
    Function to fetch GlyTouCan ID from an IUPAC condensed sequence.
    Example input: "Neu5Ac(a2-3)Gal(b1-3)[Fuc(a1-4)]GlcNAc"
    """
    # Ensure the sequence is URL-encoded
    encoded_seq = urllib.parse.quote(iupac_seq)
    url = f"https://api.glycosmos.org/glycanformatconverter/2.8.2/iupaccondensed2wurcs/{encoded_seq}"

    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        glytoucan_id = data.get("id", None)
        if glytoucan_id:
            return glytoucan_id
        else:
            return "No GlyTouCan ID found"
    else:
        return f"Error: {response.status_code}"

if __name__ == "__main__":
    res = get_glytoucan_id(iupac_seq)
    print(res)
