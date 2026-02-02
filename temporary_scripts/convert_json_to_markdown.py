#!/usr/bin/env python3
"""
Convert glycan structure dictionary JSON to human-readable Markdown.

This script reads the dictionary JSON file and generates a comprehensive
Markdown document with embedded SNFG images from the GlyCosmos API,
combining information from multiple sources.
"""

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
from datetime import datetime


def categorize_glycan(label: str, classification: Optional[str] = None) -> str:
    """Categorize glycans based on their names and classification for better organization."""
    label_lower = label.lower()
    
    # Use classification if available
    if classification:
        class_lower = classification.lower()
        if 'monosaccharide' in class_lower:
            return "Monosaccharides"
        if 'polysaccharide' in class_lower:
            return "Polysaccharides"
        if 'oligosaccharide' in class_lower:
            return "Oligosaccharides"
    
    # Blood group antigens
    if 'blood group' in label_lower:
        return "Blood Group Antigens"
    
    # Gangliosides (GM, GD, GT, GQ, GP series)
    if re.match(r'^(GM|GD|GT|GQ|GP|GA|AGM|Gg)\d', label, re.IGNORECASE):
        return "Gangliosides"
    
    # Globo series
    if re.match(r'^(Gb|iGb|nLc)\d', label, re.IGNORECASE) or 'globo' in label_lower:
        return "Globosides"
    
    # Lewis antigens
    if 'lewis' in label_lower:
        return "Lewis Antigens"
    
    # Core structures
    if label.lower().startswith('core '):
        return "Core Structures (O-Glycans)"
    
    # Sialylated structures
    if label.startswith('Neu5') or 'sialyl' in label_lower:
        return "Sialylated Glycans"
    
    # Sulfated structures
    if 'sulfo' in label_lower or 'sulfate' in label_lower:
        return "Sulfated Glycans"
    
    # Polysaccharides
    if any(term in label_lower for term in ['mannan', 'glucan', 'xylan', 'galactan', 
                                              'chitin', 'heparan', 'chondroitin', 
                                              'keratan', 'poly-', 'amylose']):
        return "Polysaccharides"
    
    # Ceramides and glycosphingolipids
    if 'ceramide' in label_lower or label in ['Lac', 'LacNAc']:
        return "Glycosphingolipids"
    
    # Stage-specific embryonic antigens
    if label.startswith('SSEA-'):
        return "Stage-Specific Embryonic Antigens"
    
    # Tumor antigens
    if 'antigen' in label_lower and 'blood' not in label_lower:
        return "Tumor-Associated Antigens"
    
    # O-linked glycans
    if label.startswith('O-'):
        return "O-Linked Glycans"
    
    # Monosaccharides
    if any(term in label_lower for term in ['glucose', 'galactose', 'mannose', 'fucose', 
                                              'xylose', 'arabinose', 'glucuronic', 'iduronic']):
        return "Monosaccharides"
    
    # Complex glycans with explicit structures
    if '(' in label and ')' in label:
        return "Defined Glycan Structures"
    
    # Everything else
    return "Other Glycans"


def combine_sources(sources: List[Dict]) -> Dict[str, Any]:
    """
    Combine information from multiple sources into a single comprehensive view.
    Track which source provided each piece of information.
    """
    combined = {
        'gsd_ids': [],
        'gtc_ids': set(),
        'exact_synonyms': defaultdict(set),  # synonym -> set of sources
        'related_synonyms': defaultdict(set),
        'classifications': defaultdict(set),
        'definitions': [],  # list of (definition, source) tuples
        'descriptions': [],  # list of (description, source) tuples
        'evidence': [],  # list of (evidence, source) tuples
        'publications': set(),
        'db_xrefs': set(),
        'iupac_condensed': [],  # list of (iupac, source) tuples
        'functions': [],  # list of (function, source) tuples
        'disease_associations': [],  # list of (disease, source) tuples
        'source_labels': []  # all source labels
    }
    
    for source in sources:
        src = source.get('src', 'Unknown')
        src_content = source.get('src_content', {})
        src_lbl = source.get('src_lbl', '')
        
        if src_lbl:
            combined['source_labels'].append(f"{src_lbl} ({src})")
        
        # GSD IDs
        if src_content.get('gsd_id'):
            combined['gsd_ids'].append((src_content['gsd_id'], src))
        
        # GTC IDs
        if src_content.get('gtc_id'):
            for gtc_id in src_content['gtc_id']:
                if gtc_id:
                    combined['gtc_ids'].add(gtc_id)
        
        # Exact synonyms
        if src_content.get('exact_synonyms'):
            for syn in src_content['exact_synonyms']:
                if syn:
                    combined['exact_synonyms'][syn].add(src)
        
        # Related synonyms
        if src_content.get('related_synonyms'):
            for syn in src_content['related_synonyms']:
                if syn:
                    combined['related_synonyms'][syn].add(src)
        
        # Classification
        if src_content.get('classification'):
            combined['classifications'][src_content['classification']].add(src)
        
        # Definition
        if src_content.get('definition'):
            combined['definitions'].append((src_content['definition'], src))
        
        # Description
        if src_content.get('description'):
            combined['descriptions'].append((src_content['description'], src))
        
        # Evidence
        if src_content.get('evidence'):
            if isinstance(src_content['evidence'], list):
                for ev in src_content['evidence']:
                    combined['evidence'].append((ev, src))
            else:
                combined['evidence'].append((src_content['evidence'], src))
        
        # Publications
        if src_content.get('publication'):
            if isinstance(src_content['publication'], list):
                combined['publications'].update(src_content['publication'])
            else:
                combined['publications'].add(src_content['publication'])
        
        # Database cross-references
        if src_content.get('db_xref'):
            if isinstance(src_content['db_xref'], list):
                combined['db_xrefs'].update(src_content['db_xref'])
            else:
                combined['db_xrefs'].add(src_content['db_xref'])
        
        # IUPAC condensed
        if src_content.get('iupac_condensed'):
            combined['iupac_condensed'].append((src_content['iupac_condensed'], src))
        
        # Functions
        if src_content.get('function'):
            if isinstance(src_content['function'], list):
                for func in src_content['function']:
                    func_src = func.get('src', src)
                    func_content = func.get('content', str(func))
                    combined['functions'].append((func_content, func_src))
            else:
                combined['functions'].append((src_content['function'], src))
        
        # Disease associations
        if src_content.get('disease_association'):
            if isinstance(src_content['disease_association'], list):
                for disease in src_content['disease_association']:
                    disease_src = disease.get('src', src)
                    disease_content = disease.get('content', str(disease))
                    combined['disease_associations'].append((disease_content, disease_src))
            else:
                combined['disease_associations'].append((src_content['disease_association'], src))
    
    return combined


def parse_json(file_path: Path) -> Dict[str, List[tuple]]:
    """
    Parse the JSON file and organize glycans by category.
    
    Returns:
        Dictionary mapping category names to lists of (label, term_uuid, combined_data) tuples.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    categories = defaultdict(list)
    
    for node in data.get('nodes', []):
        label = node.get('lbl', 'Unknown')
        term_uuid = node.get('term_uuid', '')
        sources = node.get('sources', [])
        
        # Combine all source information
        combined = combine_sources(sources)
        
        # Get classification for categorization
        classifications = list(combined['classifications'].keys())
        classification = classifications[0] if classifications else None
        
        category = categorize_glycan(label, classification)
        categories[category].append((label, term_uuid, combined))
    
    return categories


def generate_markdown(categories: Dict[str, List[tuple]], output_path: Path) -> None:
    """Generate a comprehensive Markdown document from the categorized glycans."""
    
    # Sort categories alphabetically
    sorted_categories = sorted(categories.items())
    
    with open(output_path, 'w', encoding='utf-8') as f:
        # Write header
        f.write("# Glycan Structure Dictionary (Beta)\n\n")
        f.write("* See [https://github.com/glygener/glycan-structure-dictionary REPO] AND [https://github.com/glygener/glycan-structure-dictionary/blob/main/data/processed/dictionary_20251017_160826.json JSON FILE]*\n\n")
        f.write("---\n\n")
        
        # Write statistics
        total_glycans = sum(len(glycans) for glycans in categories.values())
        total_gtc_ids = len(set(
            gtc_id
            for glycans in categories.values()
            for _, _, combined in glycans
            for gtc_id in combined['gtc_ids']
        ))
        total_gsd_ids = len(set(
            gsd_id
            for glycans in categories.values()
            for _, _, combined in glycans
            for gsd_id, _ in combined['gsd_ids']
        ))
        
        f.write("## 📊 Dictionary Statistics\n\n")
        f.write(f"- **Total Entries:** {total_glycans}\n")
        f.write(f"- **Unique GlyTouCan IDs:** {total_gtc_ids}\n")
        f.write(f"- **Unique GSD IDs:** {total_gsd_ids}\n")
        f.write(f"- **Categories:** {len(categories)}\n\n")
        f.write("---\n\n")
        
        # Write table of contents
        f.write("## 📑 Table of Contents\n\n")
        for i, (category, glycans) in enumerate(sorted_categories, 1):
            anchor = category.lower().replace(' ', '-').replace('(', '').replace(')', '')
            f.write(f"{i}. [{category}](#{anchor}) ({len(glycans)} entries)\n")
        f.write("\n---\n\n")
        
        # Write each category
        for category, glycans in sorted_categories:
            f.write(f"## {category}\n\n")
            
            # Sort glycans within category
            sorted_glycans = sorted(glycans, key=lambda x: x[0].lower())
            
            for label, term_uuid, combined in sorted_glycans:
                f.write(f"### {label}\n\n")
                
                # GSD IDs
                if combined['gsd_ids']:
                    f.write("**GSD IDs:**\n")
                    for gsd_id, src in combined['gsd_ids']:
                        src_short = src.split(':')[-1]
                        f.write(f"- `{gsd_id}` (Source: {src_short})\n")
                    f.write("\n")
                
                # GlyTouCan IDs with images
                if combined['gtc_ids']:
                    gtc_list = sorted(combined['gtc_ids'])
                    f.write("**GlyTouCan IDs:** " + ", ".join([f"`{gtc}`" for gtc in gtc_list]) + "\n\n")
                    
                    # Display image for first GTC ID
                    primary_gtc = gtc_list[0]
                    image_url = f"https://api.glycosmos.org/wurcs2image/latest/png/binary/{primary_gtc}"
                    f.write(f"![{label}]({image_url})\n\n")
                    
                    # Links
                    f.write(f"- **Image URL:** [{primary_gtc}]({image_url})\n")
                    f.write(f"- **GlyTouCan:** [View Structure](https://glytoucan.org/Structures/Glycans/{primary_gtc})\n\n")
                
                # Term UUID
                if term_uuid:
                    f.write(f"**Term UUID:** `{term_uuid}`\n\n")
                
                # Exact synonyms
                if combined['exact_synonyms']:
                    f.write("**Exact Synonyms:**\n")
                    for syn in sorted(combined['exact_synonyms'].keys()):
                        sources = combined['exact_synonyms'][syn]
                        src_list = ', '.join([s.split(':')[-1] for s in sorted(sources)])
                        f.write(f"- {syn} (Source: {src_list})\n")
                    f.write("\n")
                
                # Related synonyms
                if combined['related_synonyms']:
                    f.write("**Related Synonyms:**\n")
                    for syn in sorted(combined['related_synonyms'].keys()):
                        sources = combined['related_synonyms'][syn]
                        src_list = ', '.join([s.split(':')[-1] for s in sorted(sources)])
                        f.write(f"- {syn} (Source: {src_list})\n")
                    f.write("\n")
                
                # Classifications
                if combined['classifications']:
                    f.write("**Classification:**\n")
                    for classification, sources in sorted(combined['classifications'].items()):
                        src_list = ', '.join([s.split(':')[-1] for s in sorted(sources)])
                        f.write(f"- {classification} (Source: {src_list})\n")
                    f.write("\n")
                
                # Definitions
                if combined['definitions']:
                    f.write("**Definition:**\n")
                    for defn, src in combined['definitions']:
                        src_short = src.split(':')[-1]
                        f.write(f"- {defn} (Source: {src_short})\n")
                    f.write("\n")
                
                # Descriptions
                if combined['descriptions']:
                    f.write("**Description:**\n")
                    for desc, src in combined['descriptions']:
                        src_short = src.split(':')[-1]
                        f.write(f"- {desc} (Source: {src_short})\n")
                    f.write("\n")
                
                # IUPAC Condensed
                if combined['iupac_condensed']:
                    f.write("**IUPAC Condensed:**\n")
                    for iupac, src in combined['iupac_condensed']:
                        src_short = src.split(':')[-1]
                        f.write(f"- `{iupac}` (Source: {src_short})\n")
                    f.write("\n")
                
                # Functions
                if combined['functions']:
                    f.write("**Biological Functions:**\n")
                    for func, src in combined['functions']:
                        src_short = src.split(':')[-1] if ':' in src else src
                        f.write(f"- {func} (Source: {src_short})\n")
                    f.write("\n")
                
                # Disease associations
                if combined['disease_associations']:
                    f.write("**Disease Associations:**\n")
                    for disease, src in combined['disease_associations']:
                        src_short = src.split(':')[-1] if ':' in src else src
                        f.write(f"- {disease} (Source: {src_short})\n")
                    f.write("\n")
                
                # Evidence
                if combined['evidence']:
                    f.write("**Evidence:**\n")
                    for ev, src in combined['evidence'][:5]:  # Limit to first 5 to avoid clutter
                        src_short = src.split(':')[-1]
                        f.write(f"- {ev} (Source: {src_short})\n")
                    if len(combined['evidence']) > 5:
                        f.write(f"- *...and {len(combined['evidence']) - 5} more evidence entries*\n")
                    f.write("\n")
                
                # Publications
                if combined['publications']:
                    pub_list = sorted(combined['publications'])
                    f.write(f"**Publications:** {len(pub_list)} references\n")
                    # Show first 10
                    for pub in pub_list[:10]:
                        if pub.startswith('PMID:'):
                            pmid = pub.replace('PMID:', '')
                            f.write(f"- [{pub}](https://pubmed.ncbi.nlm.nih.gov/{pmid}/)\n")
                        else:
                            f.write(f"- {pub}\n")
                    if len(pub_list) > 10:
                        f.write(f"- *...and {len(pub_list) - 10} more publications*\n")
                    f.write("\n")
                
                # Database cross-references
                if combined['db_xrefs']:
                    f.write("**Database Cross-References:**\n")
                    for xref in sorted(combined['db_xrefs']):
                        # Create links where possible
                        if xref.startswith('CHEBI:'):
                            chebi_id = xref.replace('CHEBI:', '')
                            f.write(f"- [{xref}](https://www.ebi.ac.uk/chebi/searchId.do?chebiId=CHEBI:{chebi_id})\n")
                        elif xref.startswith('GlycoMotif:'):
                            f.write(f"- [{xref}](https://glycomotif.org/)\n")
                        elif xref.startswith('GlycoEpitope:'):
                            f.write(f"- [{xref}](https://glycoepitope.jp/)\n")
                        elif xref.startswith('CID:'):
                            cid = xref.replace('CID:', '')
                            f.write(f"- [{xref}](https://pubchem.ncbi.nlm.nih.gov/compound/{cid})\n")
                        else:
                            f.write(f"- {xref}\n")
                    f.write("\n")
                
                f.write("---\n\n")
        
        # Write footer
        f.write("## 📚 About This Dictionary\n\n")
        f.write("This glycan structure dictionary was automatically generated from the ")
        f.write("GSD (Glycan Structure Dictionary) JSON database. All structure images are ")
        f.write("rendered in SNFG (Symbol Nomenclature for Glycans) format using the ")
        f.write("[GlyCosmos API](https://glycosmos.org/).\n\n")
        
        f.write("### Data Sources\n\n")
        f.write("This dictionary combines information from multiple authoritative sources:\n\n")
        f.write("- **GSD_GLYGEN_V0**: GlyGen Glycan Structure Database\n")
        f.write("- **EOG_VARKI_4E**: Essentials of Glycobiology (4th Edition)\n")
        f.write("- **PUBDICTIONARIES-GLYCAN-IMAGE**: PubDictionaries Glycan Image Database\n")
        f.write("- **Additional sources**: Various specialized glycan databases\n\n")
        
        f.write("Each entry consolidates information from multiple sources, with source attribution ")
        f.write("provided for each piece of information.\n\n")
        
        f.write("### Image Format\n\n")
        f.write("All images use the **SNFG** (Symbol Nomenclature for Glycans) notation:\n")
        f.write("- 🔵 **Blue circle:** Glucose (Glc)\n")
        f.write("- 🟡 **Yellow circle:** Galactose (Gal)\n")
        f.write("- 🟢 **Green circle:** Mannose (Man)\n")
        f.write("- 🟣 **Purple diamond:** N-Acetylneuraminic acid (Neu5Ac)\n")
        f.write("- 🟨 **Yellow square:** N-Acetylgalactosamine (GalNAc)\n")
        f.write("- 🔷 **Blue square:** N-Acetylglucosamine (GlcNAc)\n")
        f.write("- 🔺 **Red triangle:** Fucose (Fuc)\n\n")
        
        f.write("### External Resources\n\n")
        f.write("- **GlyTouCan:** [https://glytoucan.org/](https://glytoucan.org/) - ")
        f.write("The International Glycan Structure Repository\n")
        f.write("- **GlyCosmos:** [https://glycosmos.org/](https://glycosmos.org/) - ")
        f.write("Glycoscience Portal\n")
        f.write("- **GlyGen:** [https://glygen.org/](https://glygen.org/) - ")
        f.write("Computational and Informatics Resources for Glycoscience\n\n")
        
        f.write(f"*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")


def main():
    """Main execution function."""
    # Define paths
    script_dir = Path(__file__).parent
    input_file = script_dir / "data" / "processed" / "dictionary_20251017_160826.json"
    output_file = script_dir / "GLYCAN_STRUCTURE_DICTIONARY.md"
    
    # Check if input file exists
    if not input_file.exists():
        print(f"❌ Error: Input file not found at {input_file}")
        return 1
    
    print(f"📖 Reading glycan structures from {input_file.name}...")
    categories = parse_json(input_file)
    
    total_entries = sum(len(g) for g in categories.values())
    print(f"✅ Parsed {total_entries} glycan entries")
    print(f"📂 Organized into {len(categories)} categories")
    
    print(f"📝 Generating comprehensive Markdown document...")
    generate_markdown(categories, output_file)
    
    print(f"✨ Successfully created {output_file.name}")
    print(f"📍 Location: {output_file.absolute()}")
    
    return 0


if __name__ == "__main__":
    exit(main())
