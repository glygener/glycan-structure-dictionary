# GST Classification (v1.3.4)

We classify glycan terms that encode structural content into 3 tiers. **Every term must encode a structure or set of structures** that may or may not have been experimentally resolved. Terms with protein / subcellular component / tissue / species associations are only allowed in Class 3C.

## Tier 1. Canonical named glycan entities

Terms that behave as learned glycan names rather than descriptive phrases; recurrent named entities that must typically be recognized by prior domain knowledge.

### Class 1A. Canonical named glycan entity

---

#### Definition

A conventionalized glycan name that refers to a recognized glycan motif, epitope/determinant, glycolipid-series member, glycan core type, or glycosaminoglycan family/entity, where the term functions as a learned name rather than a structurally transparent descriptive phrase.

#### Types

- **Epitopes / determinants**: Named antigenic entities where the glycan moiety must constitute the determinant. Examples: `Lewis X antigen`, `Le^x`, `SLe^x`, `blood group A antigen`, `SSEA-4 determinant`, `HNK-1 antigen`, `Tn antigen`, `sialyl-Tn antigen`, `alpha-gal antigen`, `I antigen`, `Pk antigen`.

- **Glycan cores**: Named core glycan entities. Examples: `core 1 O-glycan`, `core 2`, `core M3`.

- **Glycolipid-series members**: Named members of established glycolipid naming systems. Examples: `GM1`, `GM1a`, `asialo-GM1`, `GD1`, `GT1`, `Gb3`, `globotriaosylceramide`.

- **Named GAGs**: Established names for glycosaminoglycans. Examples: `hyaluronan`, `hyaluronic acid`, `heparan sulfate`, `keratan sulfate`.

#### Notes and special handling

- **Abbreviations, aliases, and lexical variants stay in Class 1A**.

- **Chemically-modified variants of Class 1A entities remain in Class 1A**. Example: `6′-sulfo-sialyl Lewis X`.

- **Terms that are too broad DO NOT belong in Class 1A**, even if they refer to well-known glycan groupings. Move such terms to Class 3A. Examples: `arthro-series glycolipid`, `ABO blood group antigens`, `Lewis antigens`.

---

### Class 1B. Named recurrent structural / motif-like feature

#### Definition

A conventionalized glycan feature term that refers to a recurrent, recognized structural feature or architectural subtype, where the meaning is **understood by prior glycobiology knowledge** rather than being fully transparent from ordinary language alone. These terms are not full entity-style names in the Class 1A sense, but they function as established labels for specific recurring glycan features, motif-like units, or context-bound structural classes.

#### Types

- **Named substructure features**: Specific recurring glycan features recognized as established named units within a broader glycan context. Examples: `core fucose`, `core fucosylation`, `outer-arm fucosylation`, `bisecting GlcNAc`, `bisection`, `trimannosyl core`, `poly-Sia`, `LacdiNAc`, `LDN`, `lactosamine`, `type-2 LN`

- **Named N-glycan structural classes**: Established glycan class labels whose meaning is not just generic English, but a recognized structural category presuming a glycobiology context, especially N-glycosylation context. Examples: `high mannose`, `complex type`, `hybrid type`, `paucimannose`.

- **Named N-glycan topology classes**: Established labels for recurring glycan branching architectures. Examples: `biantennary`, `triantennary`, `tetraantennary`, `multiantennary`.

#### Notes and special handling

- **Class 1B includes established glycan feature labels whose meaning is domain-learned**. For example, `complex type` here does not mean the ordinary English adjective `complex`; it refers to a recognized N-glycan structural class.

- **If a Class 1B component appears inside a larger composite phrase, the full phrase is instead assigned to a separate composite class 2C**. Examples: `core-fucosylated biantennary N-glycan`, `sialylated complex-type N-glycan`.

---

## Tier 2. Structural descriptors / semi-formal encodings

Terms that encode or describe glycan structure, but do not behave like canonical learned names.

---

### Class 2A. Linkage-specified substructure

#### Definition

A mono- or multi-residue fragment in which residue identity and connectivity are explicitly stated in the surface form.

#### Types

- **Linkage-bearing residue fragments**: Fragments with explicit residue-to-residue connectivity. Examples: `Galβ1-4GlcNAc`, `Neu5Acα2-6Galβ1-4GlcNAc`, and residue strings containing `α/β` and `1-3`, `1→4`, `1-6` style encoding as a component.

- **Linkage-marked modification features**: Structural features written with explicit linkage or positional notation rather than as plain-language descriptors. Examples: `α2-6 sialylation`, `β1-4 galactosylation`.

#### Notes and special handling

- Use Class 2A **whenever the term itself contains explicit anomeric (αβ) / positional (numerical) encoding**.

- Linkage descriptors without a noun are **DISCARDED**: e.g. `beta-linked`, `α1-4-linked` -> discard

- **Trim off aglycons**. E.g., `Siaα2-3Galβ1-4Glc-ceramide` -> `Siaα2-3Galβ1-4Glc-'`

---

### Class 2B. Glycan substructure as a structural modifier / descriptor

#### Definition

A non-name descriptive term or phrase that states a modification with a glycan substructure or residue in plain language, optionally with a context noun such as `N-glycan` or `O-glycan`, but without explicit linkage notation and without functioning as a canonical named entity or named recurrent feature.

#### Types

- **General residue descriptors**: Adjectival or participial terms indicating that a larger glycan entity carries a modification by one type of glycan. Examples: `fucosylated`, `sialylated`, `galactosylated`, `difucosylated`, `hypersialylated`, `agalactosylated`.

- **Positional residue descriptors**: Plain-language descriptions of where a residue occurs in a glycan, without explicit linkage notation. Examples: `terminal fucosylated`, `terminal fucose`, `internal GlcNAc`.

- **Context-bearing simple descriptors**: Simple descriptive phrases that pair a descriptor (2B) with a generic glycan context noun (3A). Examples: `extended + O-mannosyl glycan`, `branched N-glycan`, `fucosylated N-glycan`.

#### Notes and special handling.

- One descriptor feature + optional context noun. `terminal fucosylated N-glycan` belongs here because terminal fucosylation is one feature. `O-linked fucose` goes to 3A because the pattern `(X)-linked + MONOSACCHARIDE` belong to Class 3A terms.

- **The descriptor itself must be a glycan / monosaccharide** (**Discard**: `N-acetylated`, `N-acetylated gangliosides`,`sulfation`, `anomers`, `alpha-linkage`).

- Terms such as `core fucosylation`, `high mannose`, `biantennary`, and `bisection` **DO NOT** belong here as they are well-established named features.

- A **process/state form** belongs here: `sialylated`, `galactosylated`. Whereas a **noun form** belongs in Class 3B: `sialic acid`, `Gal`, `GlcNAc`.

---

### Class 2C. Composite descriptive glycan phrase

#### Definition

A multiword descriptive phrase whose full expression refers to a glycan or glycoconjugate class using two or more embedded descriptors, but which does not behave as a canonical named glycan entity.

#### Types

- **Multi-descriptor composite phrases**: Phrases combining more than one descriptor into a single referential unit. Examples: `core-fucosylated biantennary N-glycan`, `galactosylated biantennary N-glycan`.

- **Feature + architecture + context phrases**: Phrases mixing feature-like and class-like components inside one descriptive noun phrase. Examples: `sialylated complex-type N-glycan`.

#### Notes and special handling

- Phrases with one descriptor goes to Class 2B. Example: `sialylated N-glycan` -> 2B

- Phrases where one or more descriptors modify a Class 1A term remains in Class 1A. Examples: `extended blood group A determinant` -> 1A

---

### Class 2D. Glycoform shorthand code

#### Definition

A compact glycoform identifier whose meaning depends on a community or platform naming convention rather than being fully readable from ordinary language alone. These codes typically describes N-linked glycoforms and are common in glycomics analytical workflows and result tables.

#### Types

- **IgG shorthand glycoform codes**: Examples: `G0`, `G1`, `G1F` `G2FS1`, `G2FS2`, `Man3`, `Man9`.

- **Oxford nomenclature codes**: M, A, G, F, and S indicate mannose count, antenna number, galactose count, core fucosylation, and sialylation. Examples: `M3`, `M9`, `A2`, `FA2`, `A2[3]G1`, `FA2G2S2`, `A3G3S3`.

- **Other glycoform shorthand systems**: Examples: `NGA2`, `NGA2F`, `NA2`, `Na6-4(AF)F6`, `M3FX`, and `A4A4F`.

#### Notes and special handling

- Do not place genuine composition formulas here.`Hex5HexNAc4Fuc1NeuAc2` or `H5N4F1S2` belong in the "composition" class instead.

---

### Class 2E. Composition formula

#### Definition

A formula-like term specifying monosaccharide counts without implied or explicit connectivity.

#### Types

- **Full composition formulas**: Examples: `Hex5HexNAc4Fuc1NeuAc2`, `Glc3Man9GlcNAc2`.

- **Abbreviated composition formulas**: Examples: `H5N2`, `H5N4F1S2`.

#### Notes and special handling

- None

---

## Tier 3. Background vocabulary and structurally underdetermined terms

Terms that are too broad, too atomic, or too externally defined to function as specific glycan structure entries on their own.

---

### Class 3A. Umbrella class / glycoconjugate type

#### Definition

A broad glycan-related category, glycoconjugate superclass, or family-level grouping that is useful for organizing glycobiology concepts, but is too general to function as a specific glycan structure entry on its own.

#### Types

- **Broad glycan classes**: Biosynthetic attachment superclass. Examples: `N-glycan`, `O-glycan`, `O-GalNAc glycan`, `O-mannosyl glycan`, `glycosaminoglycan`, `O-Fuc`, `O-Man`, `O-Glc`.

- **Broad glycan family/group labels**: Well-known family or antigen-group headings that remain too inclusive to represent one specific glycan term. Examples: `ganglioside`, `ABO blood group antigens`, `Lewis antigens`, `arthro-series`

#### Notes and special handling

- Superclass terms such as `arthro-series glycolipid` belong here when they function as broad class names rather than specific named entities.

- Protein / subcellualar localization / tissue / species names are strictly forbidden in a Class 3A. Terms including the word "protein" are also forbidden.

---

### Class 3B. Monosaccharide / monosaccharide derivative

#### Definition

A standalone monosaccharide, residue name, or monosaccharide-derived building block term that is naturally-occuring.

#### Types

- **Monosaccharide residue names**: Standard residue-level sugar names used as glycan building blocks. Examples: `galactose`, `Gal`, `Glc`, `Man`, `Fuc`, `GlcNAc`, `N-acetylglucosamine`, `NANA`, `GlcA`, `IdoA`, `Kdn`, `Neu5Ac`, `sialic acids`.

- **Monosaccharide derivatives**: Chemically modified residue-level terms that still refer to a monosaccharide unit. Examples: `6-O-sulfated glucosamine`, `di-N-acetylbacillosamine`, activated monosaccharides such as `UDP-Glc`.

#### Notes and special handling

- **Noun-form residue terms only**. Residue modification states such as `sialylated` and `fucosylated` belongs in Class 2B.

---

### Class 3C. Association-defined glycan marker

#### Definition

A glycan-related label whose **structural interpretation depends primarily on an external association** such as a protein, assay, binder, organism, disease context, or other biological/experimental reference.

#### Types

- **Assay-defined markers**: Labels defined through a measurement framework or clinical assay. Examples: `GlycA`, `M2BPGi`.

- **Binder-defined labels**: Glycan structure(s) that is specifically recognized from a lectin, antibody, or other binding reagent. Examples: `VVA-binding glycan`.

- **Protein-associated markers**: Glycan tructure(s) explicitly found on a specific protein. Examples: `AFP-L3`, `gp120 glycan`, `mucin-type O-glycans`.

- **Biological context-associated labels**: Glycan structure(s) uniquely found on species, pathogen, cell type, or biological context. Examples: `Leishmania LPG`, `mammalian O-mannosyl glycan`.

#### Notes and special handling

- **This is the ONLY CLASS where any protein / species are allowed as a component**, but the term **must** encode or hint towards a constrained set of glycan structures. Therefore, `IgG N-glycans`, `glycocalyx`, `cell wall glycans`, `plant glycans`, `glycoprotein`, `mucins` should be DISCARDED.

---

## Excluded Tier (DISCARD). Out-of-scope terminologies

#### Definition

Terms that should not be collected.

#### Types

- **Non-GAG homo/hetero-polymers**: Examples: `mannan`, `alpha-glucan`, `starch`, `glycogen`.

- **Named free disaccharides**: Example: `sucrose`.

- **Descriptors that are not glycan-specific** Examples: `sulfated`, `N-acetylated`, `O-acetylation`, `acyl glycosides`, `neutral glycan`, `decassacharide`, `n-mer`, `medium-sized glycan`, `charged`, `derivitized`, `free`, `released glycan`, `protein-binding glycan`, any glycan-protein binding complexes.

- **Experimentally synthesized or artificially labeled glycans**. Example: `isotopic glycans`.

- **Umbrella classes that are overly generic**. Example: `glycans`, `oligosaccharides`, `glycoconjugates`.

- **Chemical entities or concepts that are more atomic than the monosaccharide level**. Examples: `glycosidic linkages`, `anomers`, `ring conformation`, `esters`, `ketones`, `epimer`, `open chain`, `reducing end`.
