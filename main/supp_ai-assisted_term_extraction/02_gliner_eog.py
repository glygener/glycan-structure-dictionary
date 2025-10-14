import json, os, re
from gliner import GLiNER
from pathlib import Path

DATA_DIR = Path(__file__).parents[2] / "data" / "supp"
INPUT_JSONL   = DATA_DIR / "eog_chunks.jsonl"
OUTPUT_JSONL  = DATA_DIR / "eog_raw_terms.jsonl"

START_LINE    = 1
END_LINE      = 1000000

MODEL         = "urchade/gliner_large-v2.1"
GLINER_LABELS = ["glycan structural class"]
THRESHOLD     = 0.25   

SENT_END = re.compile(r"(?<=\.)\s+")

###################################################################################################

# Exclude non-glycan entities (proteins, enzymes, antibodies, MS peak labels, metrics)
NON_GLYCAN_PATTERNS = [
    re.compile(r"\bMUC\d+\b", re.I),
    re.compile(r"\bgalectin-?\d*\b", re.I),
    re.compile(r"\blectins?\b", re.I),
    re.compile(r"\bintegrins?\b", re.I),
    re.compile(r"\balbumin\b", re.I),
    re.compile(r"\btransferrin\b", re.I),

    re.compile(r"\b(?:IgG|IgA|IgM)\b", re.I),
    re.compile(r"\bantibod(?:y|ies)\b", re.I),
    re.compile(r"\banti[-–\s]?glycans?\b", re.I),

    re.compile(r"\b[a-zA-Zβ-]*transferases?\b", re.I),
    re.compile(r"\b[a-zA-Zβ-]*glycosidas(?:e|es)\b", re.I),
    re.compile(r"\bhexosaminidas(?:e|es)\b", re.I),
    re.compile(r"\bmannosidas(?:e|es)\b", re.I),

    re.compile(r"\b(?:GlycA|M2BPGi)\b", re.I),
    re.compile(r"\bGP\d{1,3}\b", re.I),
    
    re.compile(r"\b(?:UDP|GDP|CMP)-[A-Za-z0-9]+(?:Kdn|Xyl|Fuc|Man|Gal|Glc|GlcA|GlcNAc|GalNAc|Neu5Ac|Neu5Gc)?\b", re.I),
    re.compile(r"\b[αβ][1-9]-[1-9]\b"),
    re.compile(r"\b[αβ][1-9]→[1-9]\b"),
    re.compile(r"\bC[1-9]{2}:[1-9]\b"),
    re.compile(r"\b(?:multivalent|vertebrate|bacterial|plant|fungal|nonreducing|cell surface|synthetic)(?:[-\w]*)\b", re.I),
    re.compile(r"\b(?:[-\w]*?)linkage\b", re.I)
]

# Exclude overly-generic words
GENERIC_BAD = {
    "glycan", "glycans", "carbohydrate", "carbohydrates", "monosaccharide", "monosaccharides",
    "disaccharide", "disaccharides", "trisaccharide", "trisaccharides", "oligosaccharide", "oligosaccharides",
    "polysaccharide", "polysaccharides", "glycosylation", "glycosylations", "glycoform", "glycoforms",
    "glycoconjugate", "glycoconjugates", "glycoprotein", "glycoproteins", "glycosidic bond", "glycosidic bonds",
    "glycolipid", "glycolipids", "glycan structure", "glycan structures",
    "glycan motif", "glycan motifs", "glycan epitope", "glycan epitopes",
    
    "n-glycan", "n-glycans", "n-linked glycan", "n-linked glycans", "n-glycan structure", "n-glycan structures",
    "o-glycan", "o-glycans", "o-linked glycan", "o-linked glycans", "o-glycan structure", "o-glycan structures",
    "gag", "gags", "glycosaminoglycan", "glycosaminoglycans",
    "proteoglycan", "proteoglycans", "peptidoglycan", "peptidoglycans",
    
    "gt", "gts", "gh", "ghs", "sialidase", "sialidases", "neuraminidase", "neuraminidases",
    "ogt", "ogts", "oga", "ogas",
    
    "dol-p-man", "mannac-6-p",
}

###################################################################################################

model = GLiNER.from_pretrained(MODEL)

# open files
os.makedirs(os.path.dirname(OUTPUT_JSONL), exist_ok=True)
out_f = open(OUTPUT_JSONL, "w", encoding="utf-8")

# iterate over the chosen slice of lines
processed = 0
hits = 0
with open(INPUT_JSONL, "r", encoding="utf-8") as f:
    for lineno, line in enumerate(f, start=1):
        # skip until START_LINE, stop after END_LINE
        if lineno < START_LINE:
            continue
        if END_LINE is not None and lineno > END_LINE:
            break
        if not line.strip():
            continue

        # parse record (expects: content, metadata{chapter, uuid|id})
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue

        text = rec.get("content", "") or ""
        meta = rec.get("metadata", {}) or {}
        chapter = meta.get("chapter")
        uid = meta.get("uuid") or meta.get("id")

        if not text:
            continue

        # precompute sentence spans for extracting period-to-period sentence
        spans = []
        start_idx = 0
        for m in SENT_END.finditer(text):
            end_idx = m.start() + 1
            spans.append((start_idx, end_idx))
            start_idx = m.end()
        if start_idx < len(text):
            spans.append((start_idx, len(text)))

        # run GLiNER
        try:
            entities = model.predict_entities(text, GLINER_LABELS, threshold=THRESHOLD)
        except Exception as e:
            print(f"[WARN] GLiNER failed on line {lineno}: {e}")
            continue

        processed += 1

        # write filtered results
        for ent in entities:
            term = (ent.get("text") or "").strip()
            if not term:
                continue

            # positions and score
            try:
                start = int(ent.get("start", -1))
                end = int(ent.get("end", -1))
            except Exception:
                continue
            if start < 0 or end <= start:
                continue
            score = float(ent.get("score", ent.get("confidence", 0.0)))

            # -------- apply exclusion filters --------
            # drop proteins/enzymes/antibodies/MS peaks/metrics
            if any(p.search(term) for p in NON_GLYCAN_PATTERNS):
                continue
            # drop generic words
            if term.lower() in GENERIC_BAD or len(term) < 3:
                continue
            # -----------------------------------------

            # extract sentence (period-to-period)
            term_sentence = None
            for s, e in spans:
                if s <= start < e or s < end <= e or (start <= s and end >= e):
                    term_sentence = text[s:e].strip()
                    break
            if term_sentence is None:
                lo = max(0, start - 120)
                hi = min(len(text), end + 120)
                term_sentence = text[lo:hi].strip()

            # write JSONL
            out = {
                "term": term,
                "start_pos": start,
                "end_pos": end,
                "similarity": score,
                "term_in_sentence": term_sentence,
                "metadata": {"chapter": chapter, "uuid": uid, "source_line": lineno}
            }
            out_f.write(json.dumps(out, ensure_ascii=False) + "\n")
            hits += 1

        if processed % 10 == 0:
            print(f"Processed {processed} chunks (lines {START_LINE}..{lineno}), hits so far: {hits}")

out_f.close()

print(f"Done. Processed lines {START_LINE}..{END_LINE or 'EOF'}; wrote {hits} records to {OUTPUT_JSONL}")

