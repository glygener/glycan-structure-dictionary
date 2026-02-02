#!/usr/bin/env python3
"""
Generate MediaWiki text for the Glycan Structure Dictionary (GSD) with full content set.

Fix: Preserve the original ordering used by the Markdown generator:
- Order terms by computed category (A→Z) then by label (A→Z), but DO NOT display categories.
Other behavior:
- No statistics panel
- No table of contents (uses __NOTOC__)
- MediaWiki formatting ('''Field''' : value <br>)
- SNFG images as LINKS (not embedded)
- Includes GSD paper citation and a final "Submit new terms" section
- Displays ALL fields (with (Source: ...)) when present
"""

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# ----------------------------
# Helpers
# ----------------------------

PMID_RE = re.compile(r"(PMID[:\s]*)(\d{5,9})", flags=re.IGNORECASE)

def short_src(src: str) -> str:
    return src.split(":")[-1] if ":" in src else src

def format_pubmed_link(pmid_num: str) -> str:
    return f"[https://pubmed.ncbi.nlm.nih.gov/{pmid_num} {pmid_num}]"

def linkify_pmids_in_text(text: str) -> str:
    def _sub(m: re.Match) -> str:
        return f"PMID:[{format_pubmed_link(m.group(2))}]"
    return PMID_RE.sub(_sub, text)

def make_glygen_link_for_gtc(gtc_id: str) -> str:
    return f"[https://www.glygen.org/glycan/{gtc_id} {gtc_id}]"

def make_glytoucan_view_link(gtc_id: str) -> str:
    return f"[https://glytoucan.org/Structures/Glycans/{gtc_id} View Structure]"

def make_snfg_link_for_gtc(gtc_id: str) -> str:
    return f"[https://image.glycosmos.org/snfg/png/{gtc_id} {gtc_id}]"

def link_for_dbxref(xref: str) -> str:
    if xref.startswith("CHEBI:"):
        chebi_id = xref.split(":", 1)[1]
        return f"[https://www.ebi.ac.uk/chebi/searchId.do?chebiId=CHEBI:{chebi_id} {xref}]"
    if xref.startswith("GlycoMotif:"):
        return f"[https://glycomotif.org/ {xref}]"
    if xref.startswith("GlycoEpitope:"):
        return f"[https://glycoepitope.jp/ {xref}]"
    if xref.startswith("CID:"):
        cid = xref.split(":", 1)[1]
        return f"[https://pubchem.ncbi.nlm.nih.gov/compound/{cid} {xref}]"
    if xref.startswith("KEGG:"):
        kid = xref.split(":", 1)[1]
        return f"[https://www.kegg.jp/entry/{kid} {xref}]"
    return xref

# ----------------------------
# Categorization (for ORDER ONLY; not displayed)
# Same logic as your original Markdown script.
# ----------------------------

def categorize_glycan(label: str, classification: Optional[str] = None) -> str:
    label_lower = label.lower()

    if classification:
        class_lower = classification.lower()
        if 'monosaccharide' in class_lower:
            return "Monosaccharides"
        if 'polysaccharide' in class_lower:
            return "Polysaccharides"
        if 'oligosaccharide' in class_lower:
            return "Oligosaccharides"

    if 'blood group' in label_lower:
        return "Blood Group Antigens"

    if re.match(r'^(GM|GD|GT|GQ|GP|GA|AGM|Gg)\d', label, re.IGNORECASE):
        return "Gangliosides"

    if re.match(r'^(Gb|iGb|nLc)\d', label, re.IGNORECASE) or 'globo' in label_lower:
        return "Globosides"

    if 'lewis' in label_lower:
        return "Lewis Antigens"

    if label_lower.startswith('core '):
        return "Core Structures (O-Glycans)"

    if label.startswith('Neu5') or 'sialyl' in label_lower:
        return "Sialylated Glycans"

    if 'sulfo' in label_lower or 'sulfate' in label_lower:
        return "Sulfated Glycans"

    if any(term in label_lower for term in ['mannan', 'glucan', 'xylan', 'galactan',
                                            'chitin', 'heparan', 'chondroitin',
                                            'keratan', 'poly-', 'amylose']):
        return "Polysaccharides"

    if 'ceramide' in label_lower or label in ['Lac', 'LacNAc']:
        return "Glycosphingolipids"

    if label.startswith('SSEA-'):
        return "Stage-Specific Embryonic Antigens"

    if 'antigen' in label_lower and 'blood' not in label_lower:
        return "Tumor-Associated Antigens"

    if label.startswith('O-'):
        return "O-Linked Glycans"

    if any(term in label_lower for term in ['glucose', 'galactose', 'mannose', 'fucose',
                                            'xylose', 'arabinose', 'glucuronic', 'iduronic']):
        return "Monosaccharides"

    if '(' in label and ')' in label:
        return "Defined Glycan Structures"

    return "Other Glycans"

# ----------------------------
# Combine sources (keep all fields + sources)
# ----------------------------

def combine_sources(sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    combined = {
        'gsd_ids': [],
        'gtc_ids': set(),
        'exact_synonyms': defaultdict(set),
        'related_synonyms': defaultdict(set),
        'classifications': defaultdict(set),
        'definitions': [],
        'descriptions': [],
        'evidence': [],
        'publications': set(),
        'db_xrefs': set(),
        'iupac_condensed': [],
        'functions': [],
        'disease_associations': [],
        'term_uuid': None,
    }

    for source in sources:
        src = source.get('src', 'Unknown')
        s = source.get('src_content', {}) or {}

        if combined['term_uuid'] is None and s.get('term_uuid'):
            combined['term_uuid'] = str(s['term_uuid'])

        if s.get('gsd_id'):
            combined['gsd_ids'].append((str(s['gsd_id']), src))

        if s.get('gtc_id'):
            for g in s['gtc_id']:
                if g:
                    combined['gtc_ids'].add(str(g))

        if s.get('exact_synonyms'):
            for syn in s['exact_synonyms']:
                if syn:
                    combined['exact_synonyms'][str(syn)].add(src)

        if s.get('related_synonyms'):
            for syn in s['related_synonyms']:
                if syn:
                    combined['related_synonyms'][str(syn)].add(src)

        if s.get('classification'):
            combined['classifications'][str(s['classification'])].add(src)

        if s.get('definition'):
            combined['definitions'].append((str(s['definition']).strip(), src))

        if s.get('description'):
            combined['descriptions'].append((str(s['description']).strip(), src))

        if s.get('evidence'):
            ev = s['evidence']
            if isinstance(ev, list):
                for e in ev:
                    if e:
                        combined['evidence'].append((str(e).strip(), src))
            else:
                combined['evidence'].append((str(ev).strip(), src))

        if s.get('publication'):
            pubs = s['publication']
            if isinstance(pubs, list):
                for p in pubs:
                    if p:
                        combined['publications'].add(str(p).strip())
            else:
                combined['publications'].add(str(pubs).strip())

        if s.get('db_xref'):
            x = s['db_xref']
            if isinstance(x, list):
                for xx in x:
                    if xx:
                        combined['db_xrefs'].add(str(xx).strip())
            else:
                combined['db_xrefs'].add(str(x).strip())

        if s.get('iupac_condensed'):
            combined['iupac_condensed'].append((str(s['iupac_condensed']).strip(), src))

        if s.get('function'):
            fn = s['function']
            if isinstance(fn, list):
                for f in fn:
                    if isinstance(f, dict):
                        combined['functions'].append((str(f.get('content', f)).strip(), str(f.get('src', src))))
                    elif f:
                        combined['functions'].append((str(f).strip(), src))
            else:
                combined['functions'].append((str(fn).strip(), src))

        if s.get('disease_association'):
            da = s['disease_association']
            if isinstance(da, list):
                for d in da:
                    if isinstance(d, dict):
                        combined['disease_associations'].append((str(d.get('content', d)).strip(), str(d.get('src', src))))
                    elif d:
                        combined['disease_associations'].append((str(d).strip(), src))
            else:
                combined['disease_associations'].append((str(da).strip(), src))

    return combined

# ----------------------------
# Parser with ORDER preserved (category → label)
# ----------------------------

def parse_json_to_entries_with_order(file_path: Path) -> List[Dict[str, Any]]:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    buckets: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for node in data.get('nodes', []):
        label = str(node.get('lbl', 'Unknown')).strip()
        combined = combine_sources(node.get('sources', []))

        # Determine classification (for ordering only)
        classifications = list(combined['classifications'].keys())
        classification = classifications[0] if classifications else None
        category = categorize_glycan(label, classification)

        buckets[category].append({'label': label, 'combined': combined})

    # Sort categories A→Z, then each bucket by label A→Z, then flatten
    ordered_entries: List[Dict[str, Any]] = []
    for cat, items in sorted(buckets.items(), key=lambda kv: kv[0].lower()):
        items.sort(key=lambda d: d['label'].lower())
        ordered_entries.extend(items)

    return ordered_entries

# ----------------------------
# MediaWiki page scaffolding
# ----------------------------

PAGE_HEADER = """__NOTOC__
{{DISPLAYTITLE:Glycan Structure Dictionary}}

FOR THE LATEST BETA VERSION OF GLYCAN STRUCTURE DICTIONARY SEE [https://github.com/glygener/glycan-structure-dictionary REPO] AND [https://github.com/glygener/glycan-structure-dictionary/blob/main/data/processed/dictionary_20251017_160826.json JSON FILE]  

Glycan Structure Dictionary (GSD) contains terms commonly used to describe glycan structural features in publications. The glycan structure terms are primarily sourced via automatic and manual literature mining as well as from other bioinformatics databases. The Glycan Structure Dictionary is a work in progress and the terms are updated regularly to include the new term(s) and annotations. On this Wiki page the Glycan Structure Dictionary terms are listed by term name (alphabetically) and also by glycan dictionary accessions. To submit new terms go to section [[Glycan structure dictionary#Submit new terms|Glycan Structure Dictionary#Submit new terms]]. Contact https://www.glygen.org/contact-us/ to report any issues. 

Please cite use of Glycan Structure Dictionary with: Vora J, Navelkar R, Vijay-Shanker K, Edwards N, Martinez K, Ding X, Wang T, Su P, Ross K, Lisacek F, Hayes C, Kahsay R, Ranzinger R, Tiemeyer M, Mazumder R. The glycan structure dictionary-a dictionary describing commonly used glycan structure terms. Glycobiology. 2023 Feb 17:cwad014. doi: 10.1093/glycob/cwad014. PMID: 36799723.  

==Terms (by Term Name)==

"""

SUBMIT_SECTION = """
==Submit new terms==
If you feel that a term is missing, you can submit a single term using the online form found at https://data.glygen.org/gsd/ . To submit multiple terms you can use GlyGen file upload https://data.glygen.org/uploads. Template for submitting terms can be found [https://docs.google.com/spreadsheets/d/19ZCAJk_LyLjXT4W-hNWCCwcyndQlGooFLoJ5qCDdxDI/edit#gid=0 here]. Contact https://www.glygen.org/contact-us/ for any questions.
"""

def write_field_line(fh, field: str, value: str):
    if value.strip():
        fh.write(f" '''{field}''' : {value} <br>\n")

# ----------------------------
# MediaWiki generation
# ----------------------------

def generate_mediawiki(entries: List[Dict[str, Any]], output_path: Path) -> None:
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(PAGE_HEADER)

        for e in entries:
            label = e['label']
            c = e['combined']
            f.write(f"=== {label} ===\n")

            write_field_line(f, "term (main_entry)", label)

            if c['gsd_ids']:
                gsd_pieces = [f"{gid} (Source: {short_src(src)})" for gid, src in c['gsd_ids']]
                write_field_line(f, "GSD IDs", " | ".join(gsd_pieces))

            if c['gtc_ids']:
                gtc_sorted = sorted(c['gtc_ids'])
                write_field_line(f, "GlyTouCan IDs", " | ".join(gtc_sorted))
                write_field_line(f, "Image URL", make_snfg_link_for_gtc(gtc_sorted[0]))
                write_field_line(f, "GlyTouCan", make_glytoucan_view_link(gtc_sorted[0]))

            if c.get('term_uuid'):
                write_field_line(f, "Term UUID", c['term_uuid'])

            if c['exact_synonyms']:
                syns = [f"{syn} (Source: " + ", ".join(sorted(short_src(s) for s in srcs)) + ")"
                        for syn, srcs in sorted(c['exact_synonyms'].items(), key=lambda kv: kv[0].lower())]
                write_field_line(f, "Exact Synonyms", " | ".join(syns))

            if c['related_synonyms']:
                rsyns = [f"{syn} (Source: " + ", ".join(sorted(short_src(s) for s in srcs)) + ")"
                         for syn, srcs in sorted(c['related_synonyms'].items(), key=lambda kv: kv[0].lower())]
                write_field_line(f, "Related Synonyms", " | ".join(rsyns))

            # If you prefer to suppress showing classification on the page,
            # comment out the next block.
            if c['classifications']:
                classes = [f"{cls} (Source: " + ", ".join(sorted(short_src(s) for s in srcs)) + ")"
                           for cls, srcs in sorted(c['classifications'].items(), key=lambda kv: kv[0].lower())]
                write_field_line(f, "Classification (beta)", " | ".join(classes))

            if c['definitions']:
                f.write(" '''Definition''' :\n")
                for defn, src in c['definitions']:
                    f.write(f" - {defn} (Source: {short_src(src)}) <br>\n")

            if c['descriptions']:
                f.write(" '''Description''' :\n")
                for desc, src in c['descriptions']:
                    f.write(f" - {desc} (Source: {short_src(src)}) <br>\n")

            if c['iupac_condensed']:
                f.write(" '''IUPAC Condensed''' :\n")
                for iupac, src in c['iupac_condensed']:
                    f.write(f" - <code>{iupac}</code> (Source: {short_src(src)}) <br>\n")

            if c['functions']:
                f.write(" '''Biological Functions''' :\n")
                for func, src in c['functions']:
                    f.write(f" - {func} (Source: {short_src(src)}) <br>\n")

            if c['disease_associations']:
                f.write(" '''Disease Associations''' :\n")
                for dis, src in c['disease_associations']:
                    f.write(f" - {dis} (Source: {short_src(src)}) <br>\n")

            if c['evidence']:
                f.write(" '''Evidence''' :\n")
                shown = 0
                for ev, src in c['evidence']:
                    if shown >= 5:
                        break
                    ev_line = linkify_pmids_in_text(ev.replace("\n", " ").strip())
                    f.write(f" - {ev_line} (Source: {short_src(src)}) <br>\n")
                    shown += 1
                more = len(c['evidence']) - shown
                if more > 0:
                    f.write(f" - ...and {more} more evidence entries <br>\n")

            if c['publications']:
                pmids = []
                for p in sorted(c['publications']):
                    pmid_num = p.replace("PMID:", "").replace("PMID", "").strip()
                    if pmid_num.isdigit():
                        pmids.append(pmid_num)
                if pmids:
                    write_field_line(f, "Publications", f"{len(pmids)} references")
                    for pm in pmids[:10]:
                        f.write(f" - {format_pubmed_link(pm)} <br>\n")
                    rem = len(pmids) - min(10, len(pmids))
                    if rem > 0:
                        f.write(f" - ...and {rem} more publications <br>\n")

            if c['db_xrefs']:
                f.write(" '''Database Cross-References''' :\n")
                for x in sorted(c['db_xrefs']):
                    f.write(f" - {link_for_dbxref(x)} <br>\n")

            f.write("\n")

        f.write(SUBMIT_SECTION.strip() + "\n")

def main():
    script_dir = Path(__file__).parent.parent
    input_file = script_dir / "data" / "processed" / "dictionary_20251030_160937_edited.json"
    output_file = script_dir / "GSD_WIKI.txt"

    if not input_file.exists():
        print(f"Error: Input file not found at {input_file}")
        return 1

    print(f"Reading: {input_file}")
    entries = parse_json_to_entries_with_order(input_file)
    print(f"Entries parsed: {len(entries)}")

    print(f"Writing MediaWiki text to: {output_file}")
    generate_mediawiki(entries, output_file)

    print("Done.")
    print(f"Location: {output_file.absolute()}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
