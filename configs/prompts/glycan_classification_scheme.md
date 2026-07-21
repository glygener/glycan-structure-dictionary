# bGSL Glycan Term Classification Scheme (v2026_07_14)

## Scope and the one non-negotiable rule

We classify a **single glycan term** (a `surface_form`) into exactly one class. A term is _in scope_ only if it denotes a glycan structure, or a bounded set of glycan structures (something you could in principle draw). A term is _out of scope_ (-> `DISCARD`) if it names no particular structure (e.g. `oligosaccharides`), describes something other than sugar content (e.g. `sulfated` alone), or refers to something smaller than a monosaccharide (e.g. `anomer`).

**The protein/species rule:** a protein, cell type, tissue, organism, assay, or binding-reagent name may appear in a term **only in Class 3C**. If any such name appears and the term is not admissible under 3C, the term is `DISCARD`. No other class may contain one.

**How the classes are organized.** The three tiers sorts a term by _what kind of term it is_, not by its biology:

- Tier 1 (names): the term names a glycan. Split by how the name works: an opaque name you cannot read from its parts (1A), a decodable name you can read from standard glyco-vocabulary (1B), or a polymer name (1C).
- Tier 2 (descriptions and encodings): the term describes or encodes a structure instead of naming it: explicit notation (2A), plain-language descriptors (2B, 2C), shorthand codes (2D), or composition formulas (2E).
- Tier 3 (background and underdetermined): the term is too broad (3A), too atomic (3B), or defined by an external reference (3C).

**Two rules that cut across the tiers:**

1. Abbreviations and aliases inherit the class of the full entity they stand for. Classify the parent, then the abbreviation follows. `2'FL` resolves to `2'-fucosyllactose`; since that parent is decodable (1B), `2'FL` is 1B, not 1A.
2. 1A vs 1B turns on decodability. If you can read the structure from the words using ordinary glyco-vocabulary, it is 1B. If the name is an eponym, an arbitrary label, or a code you could only know by having learned it, it is 1A.

> When two classes could plausibly apply, the **Decision order** resolves it: take the first rule that fires.

---

## Decision order (apply top-down; first match wins)

1. **Out of scope?** Too generic (`glycans`, `oligosaccharides`), a non-sugar or non-specific descriptor standing alone (`sulfated`, `neutral glycan`, `released glycan`), a sub-monosaccharide concept (`anomer`, `reducing end`), a bare linkage with no residue (`β-linked`), or an artificial/labeled compound (`isotopic glycans`) -> **DISCARD**.
2. **Structure pinned only by an external anchor** (protein / species / tissue / assay / reagent), but still bounded? -> **3C**. (Anchor present but structure unbounded, e.g. `glycoprotein`, `mucins`, `IgG N-glycans` as a whole -> DISCARD.)
3. **Is the term an abbreviation or alias?** Resolve it to the full entity it names and classify that; the abbreviation takes the same class.
4. **An opaque named entity** whose structure you cannot read from its parts (an eponym, arbitrary label, antigen/blood-group name, or entity code): `Lewis x`, `GM1`, `blood group A`, `Tn antigen`, `Forssman`? -> **1A**.
5. **A non-GAG polysaccharide/polymer name** (`starch`, `mannan`, `chitin`, `LPS`)? -> **1C**.
6. **A broad family / superclass / plural grouping** (`gangliosides`, `N-glycans`, `Lewis antigens`)? -> **3A**.
7. **A plain standalone sugar**, a monosaccharide, a monosaccharide derivative, or a plain free saccharide (a base di-/tri-saccharide or a simple single-residue-type oligomer) carrying no readable modification and treated as a free sugar rather than a glycan motif: `Gal`, `cellobiose`, `chitotriose`, `maltose`? -> **3B**.
8. **A decodable named glycan term**, where you can read its structure from standard glyco-vocabulary: a recurring motif/architecture (`LacNAc`, `biantennary`, `complex-type`) OR a specific named oligosaccharide carrying a readable modification or recognized motif (`2'-fucosyllactose`, `difucosyllactose`)? -> **1B**.
9. **Explicit connectivity**: the string spells out residue-to-residue linkages (`Galβ1-4GlcNAc`) or lists residues in sequence (`GlcNAc-Man-(GlcNAc-Man)-Man`)? -> **2A**.
10. **A glycoform shorthand code**: letter/residue-plus-count tokens in a community convention (`FA2G2S2`, `G0F`, `Man3`, `Man9`)? -> **2D**.
11. **A composition formula**: a full residue-count enumeration with no connectivity (`Glc3Man9GlcNAc2`, `Hex5HexNAc4Fuc1NeuAc2`, `H5N4F1S2`)? -> **2E**.
12. **A plain-language description carrying exactly one feature**: one modification, one attachment site, or one terminal/positional residue (+ optional context noun) (`fucosylated N-glycan`, `O-linked mannose`, `terminal galactose`)? -> **2B**.
13. **A plain-language description stacking two or more features** (`core-fucosylated biantennary N-glycan`, `disialylated fucosylated glycan`)? -> **2C**.

---

# Tier 1 - Names

Terms that name a glycan rather than describe or encode it. Tier 1 splits by how the name works: an opaque name (1A), a decodable name (1B), or a polymer name (1C). An abbreviation or alias takes the class of the full entity it stands for.

## Class 1A - Opaque named entity (epitope, glycolipid, GAG, or core)

**Plain definition:** A name for one specific glyco-entity whose structure you **cannot read from its parts**: an antigen/epitope, a named glycosphingolipid, a named glycosaminoglycan, or a named glycan core. The name is an eponym, an arbitrary label, or a code, so you only know which structure it points to because you have learned it.

**Recognize it by:** you could not reconstruct the structure by reading the words (contrast 1B, where you can). _(Mnemonic: the neighbour's poodle named "Elvis". You cannot know the dog is Elvis without being told.)_ Chemically-modified variants of a 1A entity stay in 1A (`9-O-acetyl GD3`, `chondroitin-4-sulfate`). An abbreviation inherits its parent's class, so an abbreviation of a _decodable_ name is 1B, not 1A.

**Sub-types**

- 1A-i · Histo-blood-group antigens and their extensions: `blood group A`, `blood group H type 2`, `blood group B type 4`, `A Lewis b`, `Blood group A antigen pentaose type 1`, `Forssman antigen`.
- 1A-ii · Lewis / sialyl-Lewis / sulfo-Lewis epitopes: `Lewis x`, `sialyl Lewis a`, `3'-sulfo Lewis a`, `6-sulfo sialyl Lewis x`, `dimeric Lewis x`, `3'SLex`.
- 1A-iii · Tumor, stem-cell, and other carbohydrate determinants: `Tn antigen`, `sialyl-Tn`, `disialyl T antigen`, `alpha-gal antigen`, `disialyl I antigen`, `CA19-9 antigen`, `CAD`, `CD77`.
- 1A-iv · Named gangliosides / glycosphingolipids (Svennerholm and trivial names, including derivatives): `GM1`, `GD1a` (`Disialogangliotetraosylceramide`), `Gb3` / `globotriaosylceramide`, `asialo-GM3`, `9-O-acetyl GD3`, `cisGM1`, `Cytolipin R`.
- 1A-v · Named glycosaminoglycans and their defined variants: `chondroitin sulfate`, `chondroitin sulfate A-D`, `dermatan sulfate`, `keratan sulfate`, `heparan sulfate`, `hyaluronan`, `acharan sulfate`, `chondroitin-6-sulfate`.
- 1A-vi · Named glycan cores: `core 1`-`core 8`, `core M1`, `core M2`, `core M3`.

**Not 1A if:** the name is a _group heading_ (`Lewis antigens`, `ABO blood group antigens`, `ganglioside`) -> **3A**; or you can read the structure from its parts (`2'-fucosyllactose`, `LacNAc`, `biantennary`) -> **1B**.

## Class 1B - Decodable named feature, architecture, or oligosaccharide

**Plain definition:** A name whose structure you **can read from standard glyco-vocabulary**: a recurring building block, backbone/repeat unit, core-region feature, processing class, branching architecture, or a specific named oligosaccharide (including human-milk oligosaccharides) built from recognizable sugar and modification morphemes.

**Recognize it by:** a reader who knows the vocabulary can tell what the structure is from the words (contrast 1A). _(Mnemonic: "poodle", a breed you can look up and recognize from the animal itself.)_ An abbreviation inherits it's parent's class, so `2'FL` (-> `2'-fucosyllactose`) is 1B.

**Sub-types**

- 1B-i · Backbone / repeat units and their poly-forms: `N-acetyllactosamine` / `LacNAc` (`type 1 LN`, `type 2 LN`), `LacdiNAc` / `LDN`, `poly-N-acetyllactosamine`, `polysialic acid` / `poly-Sia`, `poly-KDN`, `polymannose`, `Di-LN`, `LN3`.
- 1B-ii · N-glycan core and core-region features: `N-glycan core`, `trimannosyl core`, `core fucose`, `bisecting GlcNAc`, `outer arm fucose`, `N-glycan core, bisected`.
- 1B-iii · N-glycan processing classes: `high-mannose N-glycan` / `oligomannose`, `hybrid N-glycan`, `complex-type N-glycan`, `paucimannose N-glycan`.
- 1B-iv · Branching / antennarity architecture: `biantennary N-glycan`, `triantennary N-glycan`, `tetraantennary N-glycan`, `2-6-branch of complex N-glycans`.
- 1B-v · Defined structural sub-oligosaccharide / series units: `LS-tetrasaccharide a`, `LSTc pentasaccharide`, `sialopentaosylceramide`, `LPS core`, `lipid A core oligosaccharide`.
- 1B-vi · Decodable named oligosaccharides (incl. HMOs): `2'-fucosyllactose` (abbr. `2'FL`), `3-fucosyllactose`, `difucosyllactose`, `sialyllactose`, `lacto-N-neotetraose`.

**Not 1B if:** it is a plain free sugar with no readable modification, treated as a standalone sugar rather than a glycan motif (`cellobiose`, `chitotriose`, `lactose`) -> **3B**; the term is a _productive_ descriptor phrase rather than a lexicalized entity name (`disialylated fucosylated glycan`) -> **2C**; the modifier is a plain descriptor on a generic context noun (`fucosylated N-glycan`) -> **2B**; the name is opaque (`GM1`, `Lewis x`) -> **1A**; or connectivity is written out in notation (`Galβ1-4GlcNAc`) -> **2A**.

> **1B vs 3B for disaccharides:** `N-acetyllactosamine` (`LacNAc`, Galβ1-4GlcNAc) is a recognized glycan backbone motif -> 1B. `lactose` (Galβ1-4Glc) is the free milk sugar -> 3B. Both are Gal-based disaccharides; the split is _recognized glycan motif_ (1B) vs _standalone free sugar_ (3B).

## Class 1C - Non-GAG polysaccharide / polymer

**Plain definition:** The conventional name of a **polysaccharide or glyco-polymer that is not a glycosaminoglycan**: plant, algal, fungal, microbial, or storage polymers, and closely related glyco-polymer conjugates.

**Recognize it by:** it names a polymer / polysaccharide as a whole (a `-an` polymer name, or a named microbial glycopolymer).

**Sub-types**

- 1C-i · Storage and structural homoglucans: `starch`, `amylose`, `amylopectin`, `glycogen`, `dextran`, `cellulose`, `callose`, `β-glucan`, `α-mannan`, `mannan`.
- 1C-ii · Plant / algal cell-wall and storage heteroglycans: `xylan`, `xyloglucan`, `arabinan`, `arabinogalactan type I`, `galactomannan`, `glucomannan`, `pectin`, `homogalacturonan`, `rhamnogalacturonan-II`, `fructan`, `inulin`, `fucoidan`.
- 1C-iii · Microbial / prokaryotic polymers and glyco-polymer conjugates: `chitin`, `lipopolysaccharide`, `lipoteichoic acid`, `teichoic acid`, `pseudomurein`, `methanochondroitin`, `mannosylated lipoarabinomannan`, `phosphomannan`, `matriglycan`, `lipo-chitooligosaccharide`.

**Not 1C if:** it is a glycosaminoglycan: `hyaluronan`, `heparan sulfate`, `chondroitin sulfate`, `keratan sulfate`, `dermatan sulfate` are named GAGs -> **1A**. A plain free oligosaccharide that is not a polymer (`raffinose`) -> **3B**.

---

# Tier 2 - Descriptions and encodings

Terms that describe or encode a structure without naming it. Tier 2 splits by _how_ the structure is written: explicit connectivity (2A), plain-language one feature (2B), plain-language multiple features (2C), a shorthand code (2D), or a composition formula (2E).

## Class 2A - Notation- or sequence-specified substructure

**Plain definition:** A fragment written as **explicit connectivity**: residues joined by stated linkages, or residues listed in sequence. This is the IUPAC / condensed-notation form, not a trivial name.

**Recognize it by:** the string spells out residue-to-residue connectivity (anomeric α/β with linkage positions, or arrow notation) or concatenates residue names as a sequence. **Trim aglycons** (`-ceramide`, `-Cer`, `-OMe`) before deciding.

**Sub-types**

- 2A-i · Linkage-notated residue strings: `Galβ1-4GlcNAc`, `Neu5Ac(a2-3)Gal(b1-4)Glc`, `GlcNAcβ1-2Manα1-6`, `Gal(b1-4)[Fuc(a1-3)]Glc(b1)` (branched, bracket notation).
- 2A-ii · Linkage-notated single features: `β6-linked galactose`, `α2-3 sialyllactosamine`, `α(1-6)-linked glucose branch`, `β4-linked N-acetylgalactosamine`, `1-4-linked α-L-guluronic acid`.
- 2A-iii · Bare residue sequences (residue names concatenated without a trivial name): `GlcNAc-Man-(GlcNAc-Man)-Man`, `Gal b1-4 GalNAc b1-4 Gal b1-4 Glc`.

**Not 2A if:** it is a trivial named oligosaccharide you can decode (`difucosyllactose`) -> **1B**; a plain free sugar name (`chitotriose`, `cellobiose`) -> **3B**; residue counts only -> **2E**; a shorthand code -> **2D**; or a bare linkage with no residue noun (`β-linked`, `α1-4-linked`) -> **DISCARD**.

## Class 2B - Single-feature glycan descriptor

**Plain definition:** A plain-language phrase stating **one** feature (a modification, an attachment site, or the position/identity of one terminal residue) involving a sugar, optionally attached to a generic glycan context noun (`N-glycan`, `O-glycan`, `glycan`, `glycolipid`), with no proper name.

**Recognize it by:** exactly one descriptor feature; the descriptor itself is a sugar/monosaccharide or a sugar process.

**Sub-types**

- 2B-i · Modification-state descriptors: `fucosylated N-glycan`, `sialylated O-glycan`, `sulfated glycan`, `xylosylated glycans`, `truncated N-glycan`, `branched N-glycan`, `nonfucosylated N-glycan`.
- 2B-ii · Attachment-site descriptors, `(O/S/C)-linked` + a single monosaccharide: `O-linked mannose`, `O-linked glucose`, `O-linked N-acetylglucosamine`, `S-linked glucose`, `C-mannose`, `O-Glucosylation`.
- 2B-iii · Terminal / positional-residue descriptors, a position word + one residue: `terminal galactose`, `terminal sialic acid`, `terminal N-acetylglucosamine`, `terminal mannose`, `terminal α-linked mannose`, `terminal β-linked galactose`, `internal GlcNAc`.
- 2B-iv · Single-modification community shorthand on one backbone unit: `6'SLN`, `3'SLN`, `6'SLDN`, `3'GN type1`.

**Not 2B if:** two or more features are stacked (`core-fucosylated biantennary N-glycan`) -> **2C**; the descriptor is a recognized named feature (`core fucose`, `biantennary`, `complex-type`) -> **1B**; the descriptor is not a sugar (`N-acetylated`, `sulfated` alone) -> **DISCARD**; or it is a bare noun-form residue with no position/modification (`sialic acid`, `Gal`) -> **3B**.

> **Note:** The spelled-out pattern `(O/S/C)-linked + monosaccharide` (`O-linked mannose`) belongs here, not 3A. Only the _abbreviated attachment superclass_ forms (`O-Man`, `O-Fuc`, `O-Glc`) go to 3A.

## Class 2C - Composite (multi-feature) glycan descriptor

**Plain definition:** A plain-language phrase whose meaning combines **two or more** productive descriptors/features into one referential unit.

**Recognize it by:** more than one stacked descriptor, or feature + architecture + context, written as a productive phrase rather than a lexicalized entity name.

**Sub-types**

- 2C-i · Stacked feature + architecture + class phrases: `core-fucosylated biantennary complex-type N-glycan`, `sialylated complex-type N-glycan`, `bisected complex-type N-glycan`, `tetrasialylated biantennary N-glycan`.
- 2C-ii · Two-or-more modification descriptors: `disialylated fucosylated glycan`, `sialofucosylated glycolipid`, `difucosylated tetraantennary N-glycan`.

**Not 2C if:** only one descriptor is present (`sialylated N-glycan`) -> **2B**; the descriptors modify a 1A named entity (`extended blood group A determinant`) -> stays **1A**; or the phrase is a lexicalized named oligosaccharide you can decode (`Sialyllacto-N-neotetraose`) -> **1B**.

## Class 2D - Glycoform shorthand code

**Plain definition:** A compact glycoform identifier whose meaning depends on a **community/platform naming convention** rather than being readable from ordinary language; typically N-linked glycoforms in glycomics tables.

**Recognize it by:** Oxford / IgG-style letter-number codes where letters encode features (A = antenna, G = galactose, S = sialic acid, F = core fucose, B = bisecting, M/Man = mannose), including oligomannose codes written with a residue name plus a count.

**Sub-types**

- 2D-i · IgG / oligomannose glycoform codes: `G0`, `G0F`, `G2FS2`, `Man3`, `Man9`, `(Man)2-GlcNAc`.
- 2D-ii · Oxford nomenclature codes: `A2`, `FA2G2S2`, `A3G3S3`, `FA2[6]G1`, `A2B`.
- 2D-iii · Other shorthand systems: `NGA2F`, `NA2`, `G0-N`, `M3FX`.

**Not 2D if:** it is a full composition formula enumerating the whole residue set with counts (`H5N4F1S2`, `Hex5HexNAc4Fuc1NeuAc2`, `Glc3Man9GlcNAc2`) -> **2E**. (Oligomannose shorthand such as `Man3`/`Man9` stays 2D.)

## Class 2E - Composition formula

**Plain definition:** A formula giving a **full monosaccharide-count enumeration with no connectivity**.

**Recognize it by:** stoichiometric counts across the whole residue set, full (`Glc3Man9GlcNAc2`, `Hex5HexNAc4Fuc1NeuAc2`) or abbreviated (`H5N2`, `H5N4F1S2`).

**Not 2E if:** it is an oligomannose or feature-encoding shorthand code (`Man3`, `FA2G2S2`) -> **2D**.

---

# Tier 3 - Background and underdetermined terms

Terms too broad (3A), too atomic (3B), or too dependent on an external reference (3C) to stand as a specific structure on their own.

## Class 3A - Umbrella class / glycoconjugate family

**Plain definition:** A **broad category, superclass, or family-level grouping**: useful for organizing glycobiology, but too general to be one structure.

**Recognize it by:** plural / collective / family-heading phrasing; a superclass you could not draw as a single structure.

**Sub-types**

- 3A-i · Biosynthetic attachment superclasses: `N-glycans`, `O-glycans`, `O-GalNAc glycans`, `glycosaminoglycans`, `O-GalNAc core structures`, `O-xylose-linked glycosaminoglycan`, and abbreviated attachment forms `O-Man` / `O-Fuc` / `O-Glc`.
- 3A-ii · Glycoconjugate super-families: `glycosphingolipids`, `glycolipids`, `ganglioside`, `glycoglycerolipid`, `lipoglycan`, `seminolipid`.
- 3A-iii · Glycosphingolipid root-series headings: `Glycosphingolipid Globo series`, `Glycosphingolipid Lacto series`, `a-series gangliosides`, `Ganglio`, `Globo`.
- 3A-iv · Antigen-group headings (plural / collective): `ABO blood group antigens`, `Lewis antigens`, `P blood group antigens`, `blood group antigens`, `SSEA`.

**Not 3A if:** it is a single member (`GM1`, `Lewis x`) -> **1A**; a named feature (`trimannosyl core`) -> **1B**; or it contains a protein/species name -> **3C** or **DISCARD**. Protein/species/tissue names are strictly forbidden in 3A.

## Class 3B - Monosaccharide, derivative, or plain free sugar

**Plain definition:** A standalone sugar in noun form: a monosaccharide, a monosaccharide derivative, or a **plain free saccharide** (a base di-/tri-saccharide or a simple single-residue-type oligomer) that carries no readable modification and is treated as a free sugar rather than a glycan motif.

**Recognize it by:** a sugar noun with no readable modification feature and no explicit linkage notation. Residue count is not capped here: a plain homo-oligomer stays 3B regardless of length (`chitotriose`, `chitohexose`).

**Sub-types**

- 3B-i · Monosaccharides (common and rare): `galactose`, `Gal`, `GlcNAc`, `Fuc`, `Neu5Ac` / `NeuAc` / `NANA`, `GlcA`, `IdoA`, `Kdn`; rare deoxy/dideoxy sugars `Abequose`, `Tyvelose`, `Colitose`, `Quinovose`, `Paratose`.
- 3B-ii · Monosaccharide derivatives and modified residues: `galactose 3-O-sulfate`, `3-O-sulfated GlcNS6S`, `di-N-acetylbacillosamine`, `Muramic acid`, amino sugars (`Glucosamine`, `Galactosamine`, `Fucosamine`), sugar alcohols/aldoses (`Glyceraldehyde`, `Sedoheptulose`, `D-Fucitol`), activated sugars (`UDP-Glc`).
- 3B-iii · Plain free saccharides (di-, tri-, and simple homo-oligomers): `sucrose`, `maltose`, `lactose`, `α,α-Trehalose`, `cellobiose`, `gentiobiose`, `isomaltose`, `kojibiose`, `chitotriose`, `chitohexose`, `raffinose`, `cellotriose`.

**Not 3B if:** it carries a readable modification or is a recognized glycan motif / backbone unit (`LacNAc`, `2'-fucosyllactose`) -> **1B**; it is a process/state form (`sialylated`, `galactosylated`) -> **2B**; or connectivity is spelled out in notation (`Galβ1-4GlcNAc`) -> **2A**.

## Class 3C - Association-defined glycan marker

**Plain definition:** A glycan label whose **structure is pinned primarily by an external association**: a protein, organism/species, tissue, assay, or binding reagent, but which still encodes a **bounded** set of structures.

**Recognize it by:** remove the external anchor and the structural meaning collapses; the anchor is doing the defining work. This is the only class where a protein/species/tissue/reagent name may appear. Specific-but-oddly-defined terms (assay readouts and NMR signals) also live here.

**Sub-types**

- 3C-i · Source-organism / tissue-anchored structures: `N-glycan mixture from horseradish peroxidase`, `di-sialylated N-glycan from porcine fibrinogen`, `O-mannosyl glycan / yeast`, `O-mannosyl glycan / mammalian`, `Aspergillus fumigatus GPI oligosaccharide`, `Leishmania lipophosphoglycan repeat unit`, `Human milk oligosaccharide core`.
- 3C-ii · Protein-anchored glycan markers: `As-Fibrinogen`, `Leukosialin`, `Leukocyte common antigen`, `AFP-L3`, `gp120 glycan`.
- 3C-iii · Assay / NMR-signal / reagent / binder-defined markers: `GlycA` (an NMR composite signal), `M2BPGi`, `MECA-79`, `VVA-binding glycan`, `keratan sulfate-related glycan antigens`.

**Not 3C if:** the anchor imposes no structural bound (`glycoprotein`, `mucins`, `cell wall glycans`, `plant glycans`, `IgG N-glycans` as a whole) -> **DISCARD**.

---

# Excluded tier - DISCARD

Terms that should not be collected.

- Overly generic umbrella terms: `glycans`, `oligosaccharides`, `glycoconjugates`.
- Non-sugar or non-specific descriptors standing alone: `sulfated`, `N-acetylated`, `O-acetylation`, `neutral glycan`, `charged`, `free`, `released glycan`, `derivatized`, `medium-sized glycan`, `n-mer`, `acyl glycosides`, `protein-binding glycan`.
- Bare linkage descriptors with no residue noun: `β-linked`, `α1-4-linked`, `alpha-linkage`.
- Sub-monosaccharide chemical concepts: `glycosidic linkages`, `anomers`, `ring conformation`, `reducing end`, `epimer`, `esters`, `ketones`, `open chain`.
- Artificially synthesized or labeled compounds: `isotopic glycans`, fluorinated compounds.
- Protein/species-anchored terms with no bounded structure: `glycoprotein`, `mucins`, `cell wall glycans`, `IgG N-glycans` (whole), any glycan-protein binding complex.

---

# Confusable pairs - quick tie-breakers

| If you're torn between… | Choose the first when… | Choose the second when… |
| --- | --- | --- |
| **1A vs 1B** | you cannot read the structure from the words (`GM1`, `Lewis x`, `Forssman`) | you can read it from standard glyco-vocabulary (`LacNAc`, `2'-fucosyllactose`, `biantennary`) |
| **1B vs 3B** | a recognized glycan motif, or a named oligosaccharide with a readable modification (`LacNAc`, `2'-fucosyllactose`) | a plain standalone free sugar (`lactose`, `cellobiose`, `chitotriose`) |
| **1A vs 3A** | one specific member (`GM1`) | a plural/family heading (`gangliosides`, `Lewis antigens`) |
| **1B vs 2B** | the modifier is a recognized named feature (`core fucose`, `complex-type`) | the modifier is a plain descriptor (`fucosylated`, `branched`) |
| **2B vs 2C** | exactly one feature, including `terminal + residue` (`sialylated N-glycan`, `terminal galactose`) | two or more stacked features (`core-fucosylated biantennary N-glycan`) |
| **2A vs 2D vs 2E** | connectivity spelled out (`Galβ1-4GlcNAc`) -> 2A | letter/residue-count shorthand (`FA2G2S2`, `Man3`) -> 2D; full residue-count formula (`Hex5HexNAc4`) -> 2E |
| **3B vs 2A** | a plain free sugar / single residue (`lactose`, `Gal`, `chitotriose`) | connectivity written out in notation (`Galβ1-4GlcNAc`) |
| **anything with a protein/species/reagent** | admissible under 3C and structurally bounded -> **3C** | otherwise -> **DISCARD** |

---

# Decisions in this version (v2.1.0)

1. 1A vs 1B is now decodability: 1A = a name you cannot read from its parts (opaque). 1B = a name you can read from standard glyco-vocabulary. _(Elvis vs poodle.)_
2. Abbreviations and aliases inherit the parent entity's class: `2'FL` -> `2'-fucosyllactose` -> 1B. The abbreviation and the full name are one node in the taxonomy.
3. Decodable named oligosaccharides (incl. HMOs) -> 1B (new sub-type 1B-vi): `2'-fucosyllactose`, `3-fucosyllactose`, `difucosyllactose`, `sialyllactose`.
4. 3B extended to plain free saccharides of any size (base di-/tri-saccharides and simple homo-oligomers): `cellobiose`, `chitotriose`, `chitohexose`, `raffinose`. The 1B/3B line for disaccharides is _recognized glycan motif_ (`LacNAc` -> 1B) vs _standalone free sugar_ (`lactose` -> 3B).
5. 2A narrowed to explicit notation and bare residue sequences. Trivial named oligosaccharides moved out: decodable ones (`difucosyllactose`) -> 1B; plain free-sugar names (`chitotriose`) -> 3B.
6. `Man3` / `Man9` -> 2D (oligomannose shorthand), while full residue-count formulas (`Glc3Man9GlcNAc2`) stay 2E.
7. `GlycA` -> 3C as an NMR-signal-defined marker; 3C is the home for specific-but-oddly-defined terms.
8. 1C is a kept tier; the old DISCARD entry for non-GAG polymers is gone. _Action:_ add `1C` to the classifier prompt's allowed-label list if it is still missing.

### Terms whose tags move under these rules (scope for re-tagging)

- `2'FL`, `3-Fucosyllactose`: 1A -> 1B.
- `2'-fucosyllactose`: (was 3B in source) -> 1B.
- `Difucosyllactose`: 2A -> 1B.
- `Chitotriose`, `Chitohexose`: 2A -> 3B.
- `raffinose`: 1C -> 3B.
- `Sialyllacto-N-neotetraose` and similar lexicalized HMO names: 2C -> 1B (confirm case by case).

### Residual judgment calls (not blocking)

- GSL trivial names under sialyl-/etc. (`sialylparagloboside`): `paragloboside` is a semi-opaque glycosphingolipid name, so the whole term leans 1A. Confirm.
- 3C bounded vs unbounded for bare marker names (`Leukosialin`, `MECA-79`): kept in 3C by convention; a short accept-list may be needed since surface form alone is weak here.
