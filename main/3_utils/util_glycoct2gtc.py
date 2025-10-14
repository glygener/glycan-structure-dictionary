import requests
import urllib.parse

iupac_seq = "RES\r\n1b:b-dglc-HEX-1:5\r\n2s:n-acetyl\r\n3b:b-dglc-HEX-1:5\r\n4s:n-acetyl\r\n5b:b-dman-HEX-1:5\r\n6b:a-dman-HEX-1:5\r\n7b:a-dman-HEX-1:5\r\n8b:b-dglc-HEX-1:5\r\n9s:n-acetyl\r\n10b:x-dgal-HEX-1:5\r\nLIN\r\n1:1d(2+1)2n\r\n2:1o(4+1)3d\r\n3:3d(2+1)4n\r\n4:3o(4+1)5d\r\n5:5o(3+1)6d\r\n6:5o(6+1)7d\r\n7:6o(2+1)8d\r\n8:8d(2+1)9n\r\n9:8o(?+1)10d"

def get_glytoucan_id(iupac_seq: str) -> str:
    """
    Function to fetch GlyTouCan ID from an IUPAC condensed sequence.
    Example input: "Neu5Ac(a2-3)Gal(b1-3)[Fuc(a1-4)]GlcNAc"
    """
    # Ensure the sequence is URL-encoded
    encoded_seq = urllib.parse.quote(iupac_seq)
    url = f"https://api.glycosmos.org/glycanformatconverter/2.10.4/glycoct2wurcs/{encoded_seq}"

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
