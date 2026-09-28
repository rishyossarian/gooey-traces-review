#!/usr/bin/env python3
"""Precompute samples.json, graph.json, patterns.json seed for the error-discovery app."""
import json
import math
import random
import re
from collections import Counter
from pathlib import Path

SRC = Path.home() / "Downloads" / "traces.json"
OUT = Path(__file__).parent / "error_discovery_data"
OUT.mkdir(exist_ok=True)

STOPWORDS = set("""
a an the and or but of to in on for with as is are was were be been being
this that these those it its their our your his her they we he she i you
not no so than then thus that's it's we're they're at by from into over
under about across after before between during without within
""".split())

TOPIC_KEYWORDS = {
    "trace_01": "low-resource languages",
    "trace_02": "sovereign stack",
    "trace_03": "low-code",
    "trace_04": "orchestration / vendor-agnostic",
    "trace_05": "measurable impact & M&E",
    "trace_06": "Beyond Bias",
    "trace_07": "open-source",
    "trace_08": "team",
    "trace_09": "agriculture",
    "trace_10": "health & education",
}

def tokenize(text):
    return [w for w in re.findall(r"[a-z']+", text.lower()) if w not in STOPWORDS and len(w) > 2]

def word_count(text):
    # crude "essay word count" excluding the trailing meta line and suggestion chips
    body = text.split("≈")[0]  # split at the ≈ claimed-count marker if present
    return len(re.findall(r"\S+", body))

def claimed_count(text):
    m = re.search(r"≈\s*(\d+)\s*words", text)
    return int(m.group(1)) if m else None

def extract_chips(text):
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    chips = [l for l in lines if re.match(r"^[\U0001F300-\U0001FAFF✂✈❤✏]", l)]
    return chips

def main():
    data = json.loads(SRC.read_text())

    # --- tokenize + bag-of-words vectors ---
    docs_tokens = {d["id"]: tokenize(d["output"]) for d in data}
    vocab = Counter()
    for toks in docs_tokens.values():
        vocab.update(set(toks))
    # keep words that appear in 2+ docs (discriminative-ish) but not in all 10 (too generic)
    shared_vocab = [w for w, c in vocab.items() if 2 <= c <= 8]
    shared_vocab = sorted(shared_vocab, key=lambda w: -vocab[w])[:60]

    def vec(doc_id):
        counts = Counter(docs_tokens[doc_id])
        return [counts.get(w, 0) for w in shared_vocab]

    vectors = {d["id"]: vec(d["id"]) for d in data}

    def cosine(a, b):
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a)) or 1e-9
        nb = math.sqrt(sum(y * y for y in b)) or 1e-9
        return dot / (na * nb)

    ids = [d["id"] for d in data]
    n = len(ids)
    dist = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            dist[i][j] = 1 - cosine(vectors[ids[i]], vectors[ids[j]])

    # --- simple 2D layout via stress-majorization (pure python, tiny n) ---
    random.seed(42)
    pos = [[random.uniform(-1, 1), random.uniform(-1, 1)] for _ in range(n)]
    for _ in range(500):
        grad = [[0.0, 0.0] for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                dx = pos[i][0] - pos[j][0]
                dy = pos[i][1] - pos[j][1]
                d = math.sqrt(dx * dx + dy * dy) or 1e-6
                target = dist[i][j] * 4 + 0.3
                diff = (d - target) / d
                grad[i][0] += diff * dx
                grad[i][1] += diff * dy
        for i in range(n):
            pos[i][0] -= 0.02 * grad[i][0]
            pos[i][1] -= 0.02 * grad[i][1]

    # --- simple clustering: greedy agglomerative into ~4 groups by nearest-neighbor chains ---
    # (n=10 is too small for meaningful k-means; use similarity threshold grouping instead)
    clusters = {}
    next_cluster = 0
    assigned = {}
    order = sorted(range(n), key=lambda i: -sum(dist[i]))
    for i in order:
        if ids[i] in assigned:
            continue
        # find closest already-assigned item
        best_j, best_d = None, 0.35
        for j in range(n):
            if ids[j] in assigned and dist[i][j] < best_d:
                best_j, best_d = j, dist[i][j]
        if best_j is not None:
            assigned[ids[i]] = assigned[ids[best_j]]
        else:
            assigned[ids[i]] = next_cluster
            next_cluster += 1

    # --- structural features + outlier flags ---
    wcounts = {d["id"]: word_count(d["output"]) for d in data}
    avg_wc = sum(wcounts.values()) / n
    sorted_wc = sorted(wcounts.values())

    graph_nodes = []
    samples = []
    for idx, d in enumerate(data):
        did = d["id"]
        wc = wcounts[did]
        cc = claimed_count(d["output"])
        chips = extract_chips(d["output"])
        flags = []
        if cc is not None and abs(cc - wc) > 15:
            flags.append(f"claimed ≈{cc}w but actual body is {wc}w")
        rank = sorted_wc.index(wc)
        if rank == n - 1:
            flags.append(f"longest output ({wc}w)")
        elif rank == 0:
            flags.append(f"shortest output ({wc}w)")
        is_continuation = d["prompt"].strip().startswith("➕")

        graph_nodes.append({
            "id": did,
            "x": pos[idx][0],
            "y": pos[idx][1],
            "cluster": assigned[did],
            "topic": TOPIC_KEYWORDS.get(did, did),
        })

        samples.append({
            "id": did,
            "prompt": d["prompt"],
            "output": d["output"],
            "topic": TOPIC_KEYWORDS.get(did, did),
            "word_count": wc,
            "claimed_count": cc,
            "is_continuation": is_continuation,
            "n_chips": len(chips),
            "flags": flags,
            "cluster": assigned[did],
        })

    (OUT / "graph.json").write_text(json.dumps({"nodes": graph_nodes}, indent=2))
    (OUT / "samples.json").write_text(json.dumps(samples, indent=2))

    if not (OUT / "annotations.json").exists():
        (OUT / "annotations.json").write_text(json.dumps({}, indent=2))
    if not (OUT / "patterns.json").exists():
        (OUT / "patterns.json").write_text(json.dumps([], indent=2))
    if not (OUT / "suggestions.json").exists():
        (OUT / "suggestions.json").write_text(json.dumps([], indent=2))

    print(f"Wrote {n} samples across {next_cluster} clusters to {OUT}")
    for did, wc, cc in [(d["id"], wcounts[d["id"]], claimed_count(d["output"])) for d in data]:
        print(f"  {did}: {wc} words (claimed {cc})")

if __name__ == "__main__":
    main()
