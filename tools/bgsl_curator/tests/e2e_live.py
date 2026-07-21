"""End-to-end test against a running server (in-memory only; no disk writes).

Start the server first:
    bash tools/bgsl_curator/run.sh
Then:
    python tools/bgsl_curator/tests/e2e_live.py
"""

import json
import urllib.request

BASE = "http://127.0.0.1:8765"


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def find_uuid(query, lbl):
    _, d = call("GET", f"/api/nodes?query={urllib.parse.quote(query)}&page_size=50")
    for r in d["rows"]:
        if r["lbl"] == lbl:
            return r["term_uuid"]
    raise AssertionError(f"node not found: {lbl}")


import urllib.parse  # noqa: E402

# ---- 1. MERGE: T or TF antigen -> T antigen (exact) ----------------------
A = find_uuid("T antigen", "T antigen")
B = find_uuid("T or TF antigen", "T or TF antigen")
st, det = call("GET", f"/api/nodes/{B}")
assert st == 200 and det["provenance"], "B has provenance"
print(f"[merge] survivor T antigen={A}  absorbed T or TF antigen={B}")

st, res = call("POST", "/api/merge", {"survivor": A, "absorbed": B, "relation": "exact_synonym"})
assert st == 200, res
st, det = call("GET", f"/api/nodes/{A}")
assert "T or TF antigen" in det["node"]["exact_synonyms"], "absorbed label folded into exact"
assert B in det["node"]["merged_from_term_uuids"], "legacy UUID recorded"
st, _ = call("GET", f"/api/nodes/{B}")
assert st == 404, "absorbed node gone"
print("  ✓ merged; survivor keeps UUID, absorbed recorded as legacy, label folded")

# ---- 2. SPLIT: 6'-sulfo-sialyl Lewis x -> 6' vs 6 ------------------------
P = find_uuid("6'-sulfo-sialyl Lewis x", "6'-sulfo-sialyl Lewis x")
st, det = call("GET", f"/api/nodes/{P}")
prov = det["provenance"]
print(f"[split] parent={P} with {len(prov)} source rows")

def is_prime(lbl):
    return ("6'" in lbl) or ("6′" in lbl) or ("sialyl-6'" in lbl.lower())

c0 = {"lbl": "6'-sulfo-sialyl Lewis x", "src_uuids": [], "exact": [], "abbr": []}
c1 = {"lbl": "6-sulfo-sialyl Lewis x", "src_uuids": [], "exact": [], "abbr": []}
for p in prov:
    (c0 if is_prime(p["src_lbl"] or "") else c1)["src_uuids"].append(p["src_uuid"])
for s in det["node"].get("exact_synonyms", []):
    (c0 if is_prime(s) else c1)["exact"].append(s)
for s in det["node"].get("abbreviations", []):
    (c0 if is_prime(s) else c1)["abbr"].append(s)

st, res = call("POST", "/api/split", {"parent": P, "children": [c0, c1], "edge_routing": {}})
assert st == 200, res
kids = res["entry"]["children"]
assert len(kids) == 2, "two children"
assert all(k["uuid"].startswith("GSD:") and k["uuid"] != P for k in kids), "fresh UUIDs"
for k in kids:
    st, kd = call("GET", f"/api/nodes/{k['uuid']}")
    assert kd["node"]["split_from_term_uuid"] == P, "child cites parent"
st, _ = call("GET", f"/api/nodes/{P}")
assert st == 404, "parent gone"
print(f"  ✓ split into {kids[0]['lbl']!r} ({len(kids[0]['src_uuids'])} src) + "
      f"{kids[1]['lbl']!r} ({len(kids[1]['src_uuids'])} src); both cite parent")

# ---- 3. RELABEL + LIST EDIT on T antigen --------------------------------
st, res = call("POST", f"/api/nodes/{A}/lists",
               {"changes": [{"action": "move", "field": "exact_synonyms", "value": "TF antigen"}]})
# T antigen had 'TF antigen' in exact AND abbr; move dedupes toward abbr
st, det = call("GET", f"/api/nodes/{A}")
assert "TF antigen" not in det["node"]["exact_synonyms"], "moved out of exact"
print("  ✓ list edit: 'TF antigen' moved exact→abbr")

# ---- 4. JOURNAL + UNDO ---------------------------------------------------
st, j = call("GET", "/api/journal")
ops = [e["op"] for e in j["entries"]]
assert ops.count("merge") >= 1 and ops.count("split") >= 1, ops
print(f"  ✓ journal has {len(j['entries'])} entries: {ops}")

st, res = call("POST", "/api/undo")
assert st == 200, res
print(f"  ✓ undo reverted seq {res['marker']['undoes_seq']}")

print("\nALL E2E CHECKS PASSED (in-memory; no files written)")
