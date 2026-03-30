from pydantic import BaseModel
from typing import Optional, List

#############################################################################
# Layer 4
#############################################################################
class Function(BaseModel):
    src: str
    content: str

class DiseaseAssociation(BaseModel):
    src: str
    content: str

#############################################################################
# Layer 3
#############################################################################
class SourceContent(BaseModel):
    gsd_id: Optional[str] = None
    gtc_id: Optional[List[str]] = None
    
    exact_synonyms: Optional[List[str]] = None
    related_synonyms: Optional[List[str]] = None
    
    classification: Optional[str] = None
    definition: Optional[str] = None
    description: Optional[str] = None
    
    evidence: Optional[List[str]] = None
    publication: Optional[List[str]] = None
    db_xref: Optional[List[str]] = None
    function: Optional[List[Function]] = None
    disease_association: Optional[List[DiseaseAssociation]] = None
    
    iupac_condensed: Optional[str] = None

#############################################################################
# Layer 2
#############################################################################
class Source(BaseModel):
    src_lbl: str
    src: str
    src_uuid: str
    src_content: SourceContent

#############################################################################
# Layer 1
#############################################################################
class Node(BaseModel):
    lbl: str
    term_uuid: str
    sources: List[Source]
    
class Edge(BaseModel):
    subj: str
    pred: str
    obj: str
    comment: Optional[str] = None
    
#############################################################################
# Layer 0
#############################################################################
class GSD(BaseModel):
    nodes: List[Node]
    edges: List[Edge]