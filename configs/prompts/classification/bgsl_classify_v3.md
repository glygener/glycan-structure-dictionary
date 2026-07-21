# bGSL Classification (v3.0.0)

You are classifying a single glycan term into one of **13 classes** defined below.

## Rules

1. **Follow the decision checks in the order given.** Return the FIRST class whose criterion is met. Do not re-evaluate later checks once a match is found.
2. **Glycobiology knowledge required.** Recognise canonical names from prior knowledge — do not parse the surface form compositionally if the term is a learned name.
3. **One short reason.** No more than 12 words. Do not narrate your reasoning.
4. **No reasoning loops.** Choose the FIRST applicable class and stop.

## Decision tree (evaluate in order)

### Check 1 — Class 3C (Association-defined marker)
The term references at least one of these EXPLICIT anchors:
- A specific protein name: e.g. `AFP`, `gp120`, `IgG`, `MUC1`, `mucin`, `ZP3`, `CD4`, `hCG`, `EPO`, `transferrin`
- An assay or biomarker name: e.g. `GlycA`, `M2BPGi`, `CA19-9`, `CA125`, `AFP-L3`
- A lectin or antibody: e.g. `VVA`, `ConA`, `MAL`, `SNA`, `RCA`, `HPA`, `WGA`, `PNA`
- A species, strain, or organism: e.g. `Leishmania`, `mammalian`, `plant`, `T. cruzi`, `Trypanosoma`
- A cell type or tissue: e.g. `B-cell`, `macrophage`, `glycocalyx`

**Critical exceptions** (these are NOT 3C even though they sound disease-y):
- "Lewis" in `Lewis x/a/b/y/c/d` — that's the chemist, part of canonical name → 1A
- `Tn antigen`, `sialyl-Tn`, `T antigen`, `TF antigen`, `STn` — canonical tumor-associated antigens → 1A
- `Forssman`, `Pk antigen`, `P antigen`, `Sda`, `H antigen`, `CT antigen`, `SSEA-1/3/4` — canonical → 1A
- "ganglio-", "globo-", "lacto-", "arthro-" series prefixes → 1A or 3A
- A vague "cancer-associated" or "tumor" mention WITHOUT a specific protein/assay/lectin/organism → **NOT 3C**. Move on to Check 2 onwards.

→ 3C **only if a concrete external anchor is in the surface form**

### Check 2 — Class 1A (Canonical named glycan entity)
The term IS or IS a chemically-modified variant of any of these well-known glycan names:
- **Lewis blood-group epitopes**: `Lewis a/b/x/y/c/d`, `Le^a/b/x/y`, `sialyl Lewis x/a`, `sLe^x/^a`, `3'-sulfo Lewis x/a`, `6-sulfo sialyl Lewis x`, `dimeric Lewis x`
- **ABH blood group**: `blood group A/B/H`, `Forssman`, `H type 1/2/3`, `A type 1/2`, `B type 1/2`
- **Tumor/stage antigens**: `Tn antigen`, `sialyl-Tn`, `STn`, `T antigen`, `TF antigen`, `Tk antigen`, `I antigen`, `i antigen`, `SSEA-1`, `SSEA-3`, `SSEA-4`
- **Other epitopes**: `HNK-1`, `alpha-gal antigen`, `P antigen`, `Pk antigen`, `Sda antigen`, `CT antigen`, `KH-1`
- **Glycan cores (specific number)**: `core 1`, `core 2`, `core 3`, `core 4`, `core 5`, `core 6`, `core 7`, `core M1`, `core M2`, `core M3`, `core 1 O-glycan`
- **Gangliosides (specific identifier)**: `GM1`, `GM1a`, `GM1b`, `GM2`, `GM3`, `GD1a`, `GD1b`, `GD2`, `GD3`, `GT1a`, `GT1b`, `GT3`, `GQ1b`, `asialo-GM1/GM2/GM3`, `2-fucosyl GM1`, `9-O-acetyl GD3`
- **Globo/lacto/arthro series members**: `Gb3`, `Gb4`, `Gb5`, `GA1`, `GA2`, `globotriaosylceramide`, `globotetraosylceramide`, `lactotetraosylceramide`, `gangliotetraosylceramide`
- **Named GAGs as specific entities**: `hyaluronan`, `hyaluronic acid`, `heparan sulfate`, `heparin`, `keratan sulfate`, `chondroitin sulfate A/B/C`, `dermatan sulfate`

Modifications, abbreviations, lexical variants of these names stay in 1A: `6'-sulfo sialyl Lewis X`, `Le^a`, `Le^x`, `sLeX`, `Slea`.

→ 1A

### Check 3 — Class 1B (Named recurrent structural feature)
The term IS a recognised glycobiology feature name (domain-learned, NOT a compositional phrase):
- **Substructure features**: `core fucose`, `core fucosylation`, `outer-arm fucosylation`, `bisecting GlcNAc`, `bisection`, `trimannosyl core`, `poly-Sia`, `LacdiNAc`, `LDN`, `lactosamine`, `type-1 LN`, `type-2 LN`
- **N-glycan structural classes**: `high mannose`, `complex type`, `hybrid type`, `paucimannose`, `oligomannose`
- **N-glycan topology**: `monoantennary`, `biantennary`, `triantennary`, `tetraantennary`, `multiantennary`

**Important**: if the term is `biantennary N-glycan` (one descriptor + context noun) → 2B, not 1B. 1B is for the bare feature label.

→ 1B

### Check 4 — Class 1C (Non-GAG homo/hetero-polymer) [NEW]
A polymer name that is NOT a GAG:
- Plant polysaccharides: `mannan`, `α-glucan`, `β-glucan`, `starch`, `glycogen`, `dextran`, `cellulose`, `amylose`, `amylopectin`, `pectin`, `inulin`, `levan`, `arabinoxylan`, `xylan`, `glucuronoxylan`
- Microbial polysaccharides: `agar`, `agarose`, `alginate`, `chitin`, `chitosan`
- Plant cell-wall polymers: `apiogalacturonan`, `arabinoglucuronoxylan`

Note: hyaluronan, heparan sulfate, chondroitin sulfate, keratan sulfate, dermatan sulfate are GAGs → 1A (not 1C).

→ 1C

### Check 5 — Class 3B (Monosaccharide / disaccharide noun)
- Standalone monosaccharide (noun form, not a state): `galactose`, `glucose`, `mannose`, `fucose`, `Gal`, `Glc`, `Man`, `Fuc`, `GlcNAc`, `GalNAc`, `Neu5Ac`, `Neu5Gc`, `NANA`, `sialic acid`, `GlcA`, `IdoA`, `Kdn`, `Xyl`, `Rha`, `Ara`
- Modified monosaccharides: `6-O-sulfated glucosamine`, `9-O-acetyl sialic acid` (as standalone), `UDP-Glc`, `GDP-Fuc`, `di-N-acetylbacillosamine`
- **Named free disaccharides** [NEW in 3B]: `sucrose`, `lactose`, `trehalose`, `maltose`, `cellobiose`, `isomaltose`, `melibiose`, `lactulose`, `gentiobiose`

→ 3B

### Check 6 — Class 3A (Umbrella class)
A broad family or superclass that's too general to be a specific term:
- **Broad N/O attachment classes**: `N-glycan`, `O-glycan`, `O-GalNAc glycan`, `O-mannosyl glycan`, `O-fucose glycan`, `O-Man`, `O-Fuc`, `O-Glc`, `glycosphingolipid`, `glycosaminoglycan`, `GAG`
- **Family-level groupings**: `ganglioside`, `gangliosides`, `Lewis antigens`, `ABO blood group antigens`, `arthro-series`, `ganglio-series`, `globo-series`, `lacto-series`, `neolacto-series`, `(a/b/c)-series gangliosides`, `gala-series`

→ 3A

### Check 7 — Class 2C (Composite descriptive phrase, multiple descriptors)
Two or more descriptors stacked together inside one phrase. Examples:
- `core-fucosylated biantennary N-glycan` (core fucose + biantennary + N-glycan)
- `sialylated complex-type N-glycan` (sialylated + complex-type)
- `galactosylated biantennary N-glycan` (galactosylated + biantennary)
- `asialylated agalactosylated biantennary N-glycan` (three descriptors)
- `disialylated fucosylated glycan` (two descriptors)

→ 2C

### Check 7.5 — Class 2D (Glycoform shorthand code)
Short alphanumeric IgG / Oxford / glycomics codes. Examples: `G0`, `G1F`, `G2FS1`, `G2FS2`, `FA2`, `FA2G2`, `FA2G2S2`, `M3`, `M5`, `M7`, `M9`, `Man3`, `Man9`, `A2`, `A2[3]`, `A2[3]G1`, `NGA2`, `NA2`, `M7BC`, `M8B`.

These are platform-specific shorthand. They are NOT canonical entity names; they are a stenographic encoding.

→ 2D

### Check 7.7 — Class 2E (Composition formula)
A monosaccharide-count formula without connectivity. Examples: `Hex5HexNAc4Fuc1NeuAc2`, `Hex5HexNAc4`, `H5N4F1S2`, `Glc3Man9GlcNAc2`.

→ 2E

### Check 8 — Class 2B (Single descriptor + optional context noun)
ONE descriptor (`-ylated`, `terminal X`, `branched`, `extended`) optionally followed by `N-glycan` / `O-glycan` / generic noun:
- `fucosylated`, `sialylated`, `galactosylated`, `agalactosylated`, `hypersialylated`
- `terminal fucose`, `terminal sialic acid`, `internal GlcNAc`
- `fucosylated N-glycan`, `sialylated N-glycan`, `extended N-glycan`, `branched N-glycan`, `multifucosylated N-glycan`

**Important constraints**:
- The descriptor MUST be a glycan / monosaccharide (e.g. `fucosylated`, NOT `N-acetylated` — that's X).
- `extended blood group A determinant` is NOT 2B — the noun is a Class 1A entity → stays 1A.
- `high mannose N-glycan` — `high mannose` is a 1B feature → 2C OR if the user is using `high mannose` and `N-glycan` together as a redundant pair, lean 1B.

→ 2B

### Check 9 — Class X (outside scheme)
None of the above applies AND the term is one of:
- A non-glycan descriptor: `sulfated`, `N-acetylated`, `O-acetylation`, `anomers`, `alpha-linkage`, `glycosidic linkages`
- An over-broad generic: `glycans`, `oligosaccharides`, `glycoconjugates`, `complex carbohydrates`
- An atomic/chemistry concept: `ring conformation`, `reducing end`, `esters`, `ketones`, `epimer`
- A synthetic / labelled term: `isotopic glycans`, `2'F-A type 2`, `13C-labelled glycan`, `azido-...`
- A glycoprotein/glycolipid CLASS noun without a structural anchor: `mucins` (as plain noun), `glycoproteins`, `proteoglycans`

→ X

### Default — return Class **2B**
If you've reached this point and nothing matches confidently, return `2B` with reason `"uncertain — fell through to default 2B"`. **This is a last resort.** Make sure all previous checks were properly evaluated first.

## Output format

Return strict JSON, no markdown, no prose, no code fence:

```
{"class_code": "<one of 1A,1B,1C,2A,2B,2C,2D,2E,3A,3B,3C,X>", "reason": "<short>"}
```
