import requests
import urllib.parse

def get_glycan_sequence(accession):
    try: 
        url = f"https://api.glycosmos.org/sparqlist/gtcid2seqs?gtcid={accession}"
        response = requests.get(url)
        wurcs_str = response.json()[0].get('wurcs', None)
        encoded_wurcs = urllib.parse.quote(wurcs_str, safe='')

        url = f"https://api.glycosmos.org/glycanformatconverter/2.10.4/wurcs2iupaccondensed/{encoded_wurcs}"
        response = requests.get(url)
        iupac_str = response.json()['IUPACcondensed']

        return iupac_str
    
    except Exception as e:
        return ""

if __name__ == "__main__":
    res = get_glycan_sequence("G83367MW")
    print(res)
