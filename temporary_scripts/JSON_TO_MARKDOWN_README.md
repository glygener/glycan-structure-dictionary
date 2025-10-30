# Glycan Structure Dictionary - JSON to Markdown Converter

This tool converts the comprehensive glycan structure dictionary JSON database into a beautifully formatted, human-readable Markdown document with embedded SNFG structure images and detailed annotations from multiple sources.

## 📊 Output Statistics

The generated markdown document includes:

- **Total Entries:** 619 glycan structures
- **Unique GlyTouCan IDs:** 256 structures
- **Unique GSD IDs:** 169 entries
- **Categories:** 15 organized groups
- **File Size:** ~271 KB, 15,690 lines
- **Sources:** Multiple authoritative databases combined

## 🎯 Key Features

### 1. **Multi-Source Data Integration**
Each glycan entry combines information from multiple authoritative sources:
- **GSD_GLYGEN_V0** - GlyGen Glycan Structure Database
- **EOG_VARKI_4E** - Essentials of Glycobiology (4th Edition)
- **PUBDICTIONARIES-GLYCAN-IMAGE** - PubDictionaries Glycan Image Database
- **Additional specialized databases**

### 2. **Comprehensive Information Display**
For each glycan structure, the document includes:
- ✅ **GSD IDs** with source attribution
- ✅ **GlyTouCan IDs** with embedded SNFG images
- ✅ **Exact synonyms** from all sources
- ✅ **Related synonyms** with sources
- ✅ **Classifications** (e.g., Monosaccharide, Polysaccharide, Named Functional Motif)
- ✅ **Definitions** with chemical details
- ✅ **Descriptions** explaining biological significance
- ✅ **IUPAC Condensed notation**
- ✅ **Biological functions** (e.g., lymphocyte homing, cell adhesion)
- ✅ **Disease associations** (e.g., Influenza, cancer)
- ✅ **Evidence** from literature with URLs
- ✅ **Publications** with PMID links (up to hundreds per entry)
- ✅ **Database cross-references** (CHEBI, GlycoMotif, GlycoEpitope, PubChem, etc.)

### 3. **Source Attribution**
Every piece of information includes its source, allowing users to:
- Trace data provenance
- Understand which databases contributed specific information
- Cross-reference with original sources
- Identify the most authoritative sources for specific types of data

### 4. **Smart Organization**
Glycans are automatically categorized into 15 groups:
1. Blood Group Antigens (21 entries)
2. Gangliosides (28 entries)
3. Globosides (17 entries)
4. Lewis Antigens (26 entries)
5. Sialylated Glycans (57 entries)
6. Sulfated Glycans (16 entries)
7. Core Structures / O-Glycans (13 entries)
8. Polysaccharides (93 entries)
9. Monosaccharides (29 entries)
10. Glycosphingolipids (15 entries)
11. O-Linked Glycans (19 entries)
12. Defined Glycan Structures (13 entries)
13. Stage-Specific Embryonic Antigens (3 entries)
14. Tumor-Associated Antigens (9 entries)
15. Other Glycans (260 entries)

## 🚀 Usage

Simply run the script:

```bash
python convert_json_to_markdown.py
```

The script will:
1. Read `data/processed/dictionary_20251017_160826.json`
2. Parse all 619 glycan entries
3. Combine information from multiple sources per entry
4. Organize into categories
5. Generate `GLYCAN_STRUCTURE_DICTIONARY.md`

## 📝 Example Entry Format

Here's what a typical entry looks like with combined sources:

```markdown
### 6′-sulfo-sialyl Lewis x

**GSD IDs:**
- `GSD000011` (Source: GSD_GLYGEN_V0)

**GlyTouCan IDs:** `G00672PE`

![6′-sulfo-sialyl Lewis x](https://api.glycosmos.org/wurcs2image/latest/png/binary/G00672PE)

- **Image URL:** [G00672PE](https://api.glycosmos.org/wurcs2image/latest/png/binary/G00672PE)
- **GlyTouCan:** [View Structure](https://glytoucan.org/Structures/Glycans/G00672PE)

**Term UUID:** `GSD:6e033c8a-f202-509b-8b71-6eef358777b2`

**Exact Synonyms:**
- 6'-Sulfo-sialyl Lewis x (Source: GSD_GLYGEN_V0)
- 6'-sulfated sialyl Lewis x- (Source: GSD_GLYGEN_V0)
- 6'-sulfo-sLe(x) (Source: GSD_GLYGEN_V0)
- 6′-sulfo-SLex (Source: EOG_VARKI_4E)
- Sialyl-6′-sulfo-Lewis x (Source: EOG_VARKI_4E)
- Su-SaiLex (Source: GSD_GLYGEN_V0)
- Su-Slex (Source: GSD_GLYGEN_V0)
- sialyl-6′-sulfo-Lex (Source: EOG_VARKI_4E)

**Classification:**
- Named Functional Motif (Source: EOG_VARKI_4E)

**Definition:**
- A branched amino tetrasaccharide comprised of a trisaccharide chain of N-acetyl-α-neuraminic acid, 6-O-sulfo-β-D-glactose and N-acetyl-β-D-glucosamine residues linked sequentially (2→3) and (1→4), to the GlcNAC residue of which is also linked (1→3) an α-L-fucose residue.[CHEBI:71558] (Source: GSD_GLYGEN_V0)

**Description:**
- 6′-sulfo-sialyl Lewis X (6′-sulfo-SLex) is a sialyl Lewis X (SLex) glycan motif that is further modified by sulfation at the 6′ position of the galactose residue. It serves as a recognition ligand for selectins and Siglecs, guiding cell to cell interactions in the immune system and shaping inflammatory responses at mucosal surfaces. (Source: EOG_VARKI_4E)

**IUPAC Condensed:**
- `Neu5Ac(a2-3)Gal6S(b1-4)[Fuc(a1-3)]GlcNAc(b1-` (Source: PUBDICTIONARIES-GLYCAN-IMAGE)

**Biological Functions:**
- lymphocyte homing (Source: EP0014)

**Disease Associations:**
- Influenza (Source: 128)

**Evidence:**
- https://www.ncbi.nlm.nih.gov/books/n/glyco4/ch35/#:~:text=It%20has%20also%20been%20shown%20that,such%20as%20interleukin-5%20%28IL-5%29 (Source: EOG_VARKI_4E)
- https://www.ncbi.nlm.nih.gov/books/n/glyco4/ch35/#:~:text=Apoptosis%20depends%20on%20generation%20of,using%20different%20signaling%20pathways (Source: EOG_VARKI_4E)
- Studies using sulfotransferase-deficient mice showed that 6-sulfo sialyl Lewis X (6-sulfo sLe(x)), a major ligand for L-selectin that is expressed on the high endothelial venules (HEVs), plays critical roles in lymphocyte homing to the peripheral lymph nodes.[PMID:2288521] (Source: GSD_GLYGEN_V0)

**Publications:** 38 references
- [PMID:10435581](https://pubmed.ncbi.nlm.nih.gov/10435581/)
- [PMID:10460836](https://pubmed.ncbi.nlm.nih.gov/10460836/)
- ...and 28 more publications

**Database Cross-References:**
- [CHEBI:71558](https://www.ebi.ac.uk/chebi/searchId.do?chebiId=CHEBI:71558)
- [CID:70698387](https://pubchem.ncbi.nlm.nih.gov/compound/70698387)
- [GlycoEpitope:EP0014](https://glycoepitope.jp/)
- [GlycoMotif:GGM.000025](https://glycomotif.org/)
- SugarBind_Ligand:128
```

## 🔧 Requirements

- Python 3.6+
- Standard library only (no external dependencies!)
  - `json` - Parse JSON file
  - `re` - Regular expressions for categorization
  - `collections.defaultdict` - Data organization
  - `pathlib.Path` - File path handling
  - `datetime` - Timestamp generation

## 💡 Design Philosophy

### Multi-Source Integration
The script intelligently combines data from multiple sources:
- **Synonyms** are aggregated with source tracking
- **Definitions** from all sources are included separately
- **Evidence** and **Publications** are merged
- **Database cross-references** are combined from all sources

### Source Attribution Pattern
Every field shows which source contributed the information:
```
- Field value (Source: SOURCE_NAME)
```

This allows users to:
- Verify information against original sources
- Identify the most comprehensive sources
- Understand data provenance
- Cross-reference conflicting information

### Smart Categorization
The categorization algorithm considers:
1. Explicit classification from source data
2. Naming patterns (GM1, GD1a, Gb3, etc.)
3. Structural features (sialylated, sulfated, etc.)
4. Functional roles (blood group, tumor antigen, etc.)
5. Chemical class (monosaccharide, polysaccharide, etc.)

## 📚 Data Sources Explained

### GSD_GLYGEN_V0
- Comprehensive glycan structure database
- Includes definitions, synonyms, publications
- Links to CHEBI, PubChem, GlycoMotif
- Focus on structure-function relationships

### EOG_VARKI_4E
- Essentials of Glycobiology (4th Edition)
- Authoritative textbook content
- Detailed biological context
- Evidence from primary literature

### PUBDICTIONARIES-GLYCAN-IMAGE
- IUPAC condensed notation
- GlyTouCan ID mappings
- Structural representations

## 🎨 SNFG Symbol Notation

All images use the Symbol Nomenclature for Glycans (SNFG):
- 🔵 Blue circle: Glucose (Glc)
- 🟡 Yellow circle: Galactose (Gal)
- 🟢 Green circle: Mannose (Man)
- 🟣 Purple diamond: N-Acetylneuraminic acid (Neu5Ac)
- 🟨 Yellow square: N-Acetylgalactosamine (GalNAc)
- 🔷 Blue square: N-Acetylglucosamine (GlcNAc)
- 🔺 Red triangle: Fucose (Fuc)

## 🔗 External Resources

The generated markdown includes links to:
- **GlyTouCan** - International Glycan Repository
- **PubMed** - Publication references
- **ChEBI** - Chemical Entities of Biological Interest
- **PubChem** - Chemical compound database
- **GlycoMotif** - Glycan motif database
- **GlycoEpitope** - Glycan epitope database
- **GlyCosmos** - Integrated glycoscience portal

## 📊 Statistics Breakdown

- **Entries with GSD IDs:** 169
- **Entries with GlyTouCan IDs:** 256
- **Entries with Publications:** Varies (some have 100+ references)
- **Entries with Disease Associations:** Multiple
- **Entries with Biological Functions:** Multiple
- **Total Categories:** 15 major groups

## 🎯 Use Cases

This markdown dictionary is ideal for:
- **Education** - Learning glycobiology with visual structures
- **Research** - Quick reference for glycan structures
- **Documentation** - Citing glycan structures in papers
- **Database Development** - Understanding glycan data models
- **Literature Review** - Finding publications about specific glycans
- **Drug Discovery** - Identifying disease-associated glycans

## 📄 License

This tool is provided as-is for converting glycan structure data. The underlying glycan structure data comes from multiple authoritative sources (GlyGen, GlyCosmos, GlyTouCan, etc.).

## 🙏 Acknowledgments

Data sources:
- GlyGen (https://glygen.org/)
- GlyCosmos (https://glycosmos.org/)
- GlyTouCan (https://glytoucan.org/)
- Essentials of Glycobiology (https://www.ncbi.nlm.nih.gov/books/NBK579915/)
