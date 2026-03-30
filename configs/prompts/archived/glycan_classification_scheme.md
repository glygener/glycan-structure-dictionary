# Glycan Term Classification (v1.2.0)

A 3-tier glycan term classification scheme for expanding the usability of the Glycan Structure Dictionary (GSD).

## Design principle

This scheme classifies terms by how they behave on the page and in literature usage, rather than by whether two terms can ultimately be mapped to the same underlying structure.

Thus, two terms may refer to the same underlying structure but still belong to different classes if one behaves like a conventionalized literature name and the other behaves like a structural, positional, or descriptive phrase.

## Operational rule

Classify the term by its most specific interpretable surface form.

If a term is composite, assign:

- one primary class based on the whole phrase as used in text
- optional embedded component tags for internal curation, if needed

For example, a composite phrase like "core-fucosylated biantennary N-glycan" may receive one primary class as a full descriptive phrase, while also containing embedded elements from motif, topology, and umbrella classes.

---

## Tier descriptions

### Tier 1. Canonical named glycan entities and named recurrent features

Terms that behave like stable literature labels. They can stand alone as recognizable glycan names, motif names, epitope names, glyco-series members, or highly conventionalized recurrent feature names.

### Tier 2. Structural descriptors and semi-formal encodings

Terms that encode or describe glycan structure, but do not behave like stable proper-name-like entity labels.

### Tier 3. Background vocabulary and structurally underdetermined terms

Terms that are too broad, too atomic, or too externally defined to function as specific glycan structure entries on their own.

---

## Tier 1 — Canonical / conventional named entities

### Tier 1A. Canonical named glycan entity

#### Definition

A conventional glycan name, motif name, epitope name, glycolipid-series member, or other literature-stable entity label that stands alone as a recognized glycan identifier.

#### Typical behavior

- Proper-name-like or lexicalized usage
- Routinely used without extra explanation
- Often has abbreviations, aliases, capitalization conventions, or established modified variants

#### Examples

Lewis X / Le^x, HNK-1, Tn antigen / sTn, Forssman antigen, Blood group A type I, LacdiNAc, GM1 / GD1 / GT1, hyaluronan / hyaluronic acid, CA19-9, and SSEA-2; these fit because they behave as conventionalized literature names rather than merely descriptive phrases. Modified named forms such as sialyl Lewis X and 6′-sulfo-sialyl Lewis X also fit here when the whole term is used as a recognized lexicalized entity name.

---

### Tier 1B. Named recurrent structural feature / named motif-like feature

#### Definition

A highly conventionalized structural feature term that refers to a recurrent glycan substructure or topological motif and is widely used almost like a named entity, even if it is not a full standalone glycan name in the same sense as Tier 1A.

#### Typical behavior

- Stable and reusable phrase across papers
- Refers to a recognizable recurrent motif or feature
- More conventionalized than a generic descriptor
- Often names a recurring substructure rather than a whole glycan entity

#### Examples

core fucose, core fucosylation, bisecting GlcNAc, outer-arm fucosylation, core 1, core 2 O-glycan, and core M3; these fit because they denote well-recognized recurrent structural motifs/features that glycobiologists treat almost like named units, rather than ad hoc descriptive states.

#### Placement of core fucosylation

Although "core fucosylation" superficially sounds like a modification/state descriptor, it should be placed in Tier 1B, not Tier 2F, because it does not merely say that some glycan is fucosylated. It names a specific, recurrent, literature-stable structural motif defined by a characteristic positional context on the core.

---

## Tier 2 — Structural descriptors / semi-formal encodings

### Tier 2A. Linkage-specified substructure

#### Definition

A mono- or multi-residue fragment where residue identity and connectivity are explicitly stated.

#### Typical behavior

- Contains linkage symbols, numbers, or formalized sequence-like encoding
- Can often be interpreted structurally without outside context
- Usually closer to notation than to lexicalized naming

#### Examples

α/β…, 1-3…, 1→4…, α2-6 sialylation when written as explicit linkage-bearing notation, and fragments like Galβ1-4GlcNAc or Neu5Acα2-6Galβ1-4GlcNAc; these fit because connectivity is directly encoded in the surface form.

---

### Tier 2B. Positional structural feature

#### Definition

A chemically meaningful structural feature described in natural language, usually with residue identity and positional or locational information, but not expressed as a full linkage-defined fragment.

#### Typical behavior

- Natural-language structural phrase
- Indicates location, orientation, or structural role
- Structurally informative, but not a full named motif and not a full structural string

#### Examples

terminal sialic acid, internal GalNAc; these fit because they describe meaningful structural placement or positional character, but do not function as stable named motif labels on their own.

#### Boundary with 1B

If the phrase is a broadly descriptive feature, keep it in 2B.

If it behaves as a highly conventionalized named recurrent motif, move it to 1B.

---

### Tier 2C. Glycoform shorthand code

#### Definition

A compact symbolic code whose interpretation depends on a domain-specific naming convention.

#### Typical behavior

- Community- or workflow-dependent shorthand
- Meaning is not fully recoverable without convention knowledge
- Often used in glycomics output tables and platform-specific nomenclature

#### Examples

G0, G0F, G1, G2FS2, Man3, Man9, A2, FA2, A2[3]G1, FA2G2S2, M3, M9, A1, A1F, NA3, and NGA2F; these fit because they are compressed notation systems whose interpretation depends on a naming convention rather than plain-language structure reading.

---

### Tier 2D. Composition formula

#### Definition

A term specifying monosaccharide counts but not explicit connectivity.

#### Typical behavior

- Formula-like count representation
- Structurally informative at the composition level only
- Lacks branching, linkage, and position detail

#### Examples

Hex5HexNAc4Fuc1NeuAc2, Glc3Man9GlcNAc2, H5N2, and H5N4F1S2; these fit because they specify composition only. Counter-example: Man9 should be retained where relevant when the term is clearly being used as shorthand code rather than literal composition language.

---

### Tier 2E. Structural class / topology descriptor

#### Definition

A natural-language descriptor of glycan class, branching topology, or architectural type that is structurally informative but not a named motif and not a fully defined structure.

#### Typical behavior

- Describes overall architecture or class
- Often spans a family of related structures rather than one recurrent named motif
- Useful for broad structural categorization, not for naming a specific conventionalized unit

#### Examples

high mannose, hybrid, complex-type, biantennary, and paucimannose; these fit because they describe broad architectural or topological classes rather than a single named recurrent feature.

#### Counter-examples and rationale

High mannose, complex-type, and biantennary should stay here, not in Tier 1B. They are structurally meaningful, but they are not the same kind of term as core fucosylation or bisecting GlcNAc. The latter refer to more specific recurrent motif-like features that are treated as recognizable named structural units, whereas high mannose, complex-type, and biantennary describe broader architectural categories that cover multiple possible concrete structures.

---

### Tier 2F. Modification / state descriptor

#### Definition

An adjective-like descriptor indicating the presence, extent, or state of glycan modification, usually without specifying exact residue location or full structure.

#### Typical behavior

- Functions like a property or state
- Says that some larger glycan entity has undergone a modification
- Usually lacks exact positional specificity unless promoted into a named motif-like feature

#### Examples

fucosylated, sialylated, galactosylated, sulfated, hypersialylated, and phrases like fucosylated N-glycan at the modifier level; these fit because they describe a modification state rather than naming a specific canonical motif.

#### Why this differs from monosaccharides

- fucose = a building block noun → Tier 3B
- fucosylated = a state/property assigned to a larger glycan entity → Tier 2F

#### Important distinction from core fucosylation

Generic terms like fucosylated and galactosylated belong here because they only indicate that a modification is present. By contrast, core fucosylation belongs in Tier 1B because it denotes a specific recurrent motif-like feature with conventionalized meaning, not just a generic modification state.

---

### Tier 2G. Composite descriptive glycan phrase

#### Definition

A multiword term whose full phrase describes a glycan class or glycoconjugate class using one or more embedded structural/state/topology descriptors, but which does not behave as a conventional named glycan entity.

#### Typical behavior

- Whole phrase is the meaningful unit in text
- Built from components that may each belong to different classes
- Best handled as a full descriptive phrase rather than by forcing the entire term into the class of one token

#### Examples

fucosylated N-glycan, biantennary N-glycan, core-fucosylated biantennary N-glycan, and galactosylated biantennary N-glycan; they fit here because the phrase as a whole is being used referentially, while containing embedded modifiers from Tier 1B, Tier 2E, Tier 2F, and Tier 3A.

#### How to resolve mixed-class composite terms

Assign the whole phrase to Tier 2G as the primary class. For example:

- core-fucosylated biantennary N-glycan → 2G

---

## Tier 3 — Background / underdetermined vocabulary

### Tier 3A. Umbrella class / glycoconjugate type

#### Definition

A broad glycobiology category, research-domain term, or glycoconjugate superclass rather than a specific structure or recurrent feature.

#### Typical behavior

- Very broad and inclusive
- Useful for describing domain scope or major glycoconjugate classes
- Too general to serve as a specific dictionary structure entry on its own

#### Examples

N-glycan, O-glycan, glycosaminoglycan, glycolipid, glycosphingolipid, ganglioside, proteoglycan, and ABO blood group antigens; these fit because they denote broad classes rather than specific motifs or structure terms.

---

### Tier 3B. Monosaccharide / monosaccharide derivative

#### Definition

A standalone monosaccharide or monosaccharide derivative used as a building block term.

#### Typical behavior

- Atom-level building block vocabulary
- Usually names a residue rather than a complete glycan feature
- May include chemically modified monosaccharide forms

#### Examples

GalNAc, Kdn, GlcA, 6-O-sulfated glucosamine, and di-N-acetylbacillosamine; these fit because they are residue-level building blocks rather than named glycan motifs or descriptive glycan classes. Fucose belongs here for the same reason.

---

### Tier 3C. Association-defined glycan marker

#### Definition

A glycan-related label whose interpretation depends primarily on an external association such as a protein, assay, binder, organism, condition, or experimental context, such that structure cannot be inferred from the term alone.

#### Typical behavior

- Meaning depends on outside biological or assay context
- Structurally underdetermined from surface form alone
- Often useful biologically, but not suitable as a structure-only dictionary term without additional linkage

#### Examples

GlycA, VVA-binding glycan, Leishmania lipophosphoglycan repeat, gp120, AFP-L3, and M2BPGi; these fit because the term points to an assay-defined, binder-defined, protein-centric, or condition-associated glycan concept rather than a directly interpretable structure label.

---

## Excluded class. Polymer classes outside scope

#### Definition

Non-GAG polymer or polysaccharide classes that are outside the intended scope of the GSD unless you explicitly decide to include them.

#### Examples

starch, mannan, and alpha-glucan; these are excluded because they are polymer classes outside the present glycan term scope you described.
