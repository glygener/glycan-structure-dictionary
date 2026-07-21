# bGSL 3C Recall Check (v3.0.0)

Another classifier just labelled the term below as something **other than 3C**. The first pass is known to miss 3C (association-defined glycan marker) when the protein / assay / binder / species reference is subtle.

## Class 3C definition (reminder)

A glycan-related label whose **structural interpretation depends primarily on an external association**: a specific protein, assay, antibody, lectin, organism, cell type, or disease context.

## Decide

Does the term contain any of these?

- **Specific protein name** (case-sensitive matters): `AFP`, `gp120`, `IgG`, `IgA`, `IgM`, `IgE`, `mucin`, `mucin-type`, `MUC1`, `MUC2`, `MUC5`, `ZP3`, `CD4`, `CD43`, `CD45`, `CD52`, `hCG`, `EPO`, `transferrin`, `lactoferrin`, `tau`, `prion`, `α1-acid glycoprotein`, `AGP`, `complement`, `FXII`, `factor IX`, `factor XII`, `prostate-specific antigen`, `PSA`, `CEA`, `human serum albumin`
- **Assay / clinical biomarker**: `GlycA`, `GlycB`, `M2BPGi`, `AFP-L3`, `CA125`, `CA15-3`, `CA72-4`, `LeY ELISA`
- **Lectin / antibody binder**: `VVA`, `ConA`, `MAL-I`, `MAL-II`, `SNA`, `RCA-I`, `HPA`, `WGA`, `PNA`, `LCA`, `SBA`, `UEA-I`, `Erythrina`, `ABA`, `DBA`
- **Species, strain, organism**: `Leishmania`, `Trypanosoma`, `mammalian`, `plant`, `human-type`, `Staphylococcus`, `Helicobacter`, `E. coli`, `Streptococcus`, `Mycobacterium`, `Schistosoma`, `nematode`
- **Tissue, cell type, organ**: `glycocalyx`, `macrophage`, `B-cell`, `T-cell`, `erythrocyte`, `placental`, `kidney`, `brain glycan`
- **Disease context**: `tumor-associated`, `cancer-associated`, `oncofetal`, `inflammation-associated`

**False positives to avoid** (these are NOT 3C even if they look protein-y):
- `Lewis x/a/b/y` — "Lewis" is a chemist's name, part of canonical 1A.
- `Forssman`, `Sda`, `CT antigen` — canonical antigen names → 1A.
- `Globoseries`, `Ganglio-series`, `Lacto-series` — glycolipid families → 3A.
- `Pk antigen`, `P antigen`, `H antigen` — canonical → 1A.
- `O-mannose`, `O-glycan` — biosynthetic class, not an association → 3A.

## Output

```
{"decision": "<MAKE_3C|KEEP_ORIGINAL>", "reason": "<short>"}
```

`MAKE_3C` if the term genuinely carries a protein/assay/binder/species/tissue/disease anchor.
`KEEP_ORIGINAL` otherwise (the first pass was correct).
