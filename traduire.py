#!/usr/bin/env python3
# Traduit les pages villes d'OnBouge (champs texte seulement) avec des modèles LIBRES (Helsinki-NLP / OPUS-MT),
# sur une machine GitHub Actions : 0 €, aucune API, rien ne dépend d'un quota.
#   entrée  : lots/<lang>.jsonl   {"slug","lang","ville","champs":{...}}   (exporté par le serveur OnBouge)
#   sortie  : resultats/<lang>.jsonl {"slug","lang","payload":{...}}  (même forme que le cache du site)
# Un enregistrement dont la traduction PERD le nom de la commune est écarté (jamais « Berg » -> « Montagne »).
import json, os, re, sys, time
import torch
from transformers import MarianMTModel, MarianTokenizer

LANG = sys.argv[1]
MAX_SECONDES = int(os.environ.get("MAX_SECONDES", str(5 * 3600)))
CHAINE = {
    "it": [("Helsinki-NLP/opus-mt-tc-big-itc-itc", ">>ita<< ")],
    "es": [("Helsinki-NLP/opus-mt-fr-es", "")],
    "de": [("Helsinki-NLP/opus-mt-fr-de", "")],
    "en": [("Helsinki-NLP/opus-mt-tc-big-fr-en", "")],
    "nl": [("Helsinki-NLP/opus-mt-tc-big-fr-en", ""), ("Helsinki-NLP/opus-mt-en-nl", "")],  # pas de modèle direct fr->nl
}[LANG]
torch.set_num_threads(os.cpu_count() or 4)
MODELES = [(MarianTokenizer.from_pretrained(m), MarianMTModel.from_pretrained(m).eval(), pre) for m, pre in CHAINE]

PHRASES = re.compile(r"(?<=[.!?])\s+(?=[A-ZÀ-Ý0-9«\"])")
def decouper(t):
    t = (t or "").strip()
    if len(t) < 350:
        return [t]
    return [p for p in PHRASES.split(t) if p]

def traduire_lot(textes):
    out = list(textes)
    for tok, mod, pre in MODELES:
        res = []
        for i in range(0, len(out), 24):
            lot = [pre + x for x in out[i:i + 24]]
            enc = tok(lot, return_tensors="pt", padding=True, truncation=True, max_length=480)
            with torch.inference_mode():
                gen = mod.generate(**enc, num_beams=2, max_new_tokens=512)
            res += tok.batch_decode(gen, skip_special_tokens=True)
        out = res
    return out

# Faux-sens CONNUS, relevés au premier essai (15/10/2026) : « déménagement » devenait « transfer ».
GLOSSAIRE = {
    "en": [(r"\btransfers?\b", "move"), (r"\bDowntown\b", "Town centre")],
    "nl": [(r"\btransfer\b", "verhuizing"), (r"\bDowntown\b", "Centrum")],
    "it": [(r"\bprezzo minimo per un viaggio a\b", "prezzo di un trasloco a"), (r"\bun viaggio a\b", "un trasloco a"), (r"\bun trasferimento a\b", "un trasloco a")],
    "de": [(r"\s*✓\s*", " — ")],
}
def corriger(t):
    for motif, par in GLOSSAIRE.get(LANG, []):
        t = re.sub(motif, par, t)
    return t

def aplatir(champs):
    """Liste des chaînes à traduire + fonction qui reconstruit la même forme."""
    textes, poses = [], []
    def ajout(v, chemin):
        if isinstance(v, str) and v.strip():
            # « Centre-ville parfois dense — accès camion à confirmer » : sans ce découpage le modèle
            # avalait le tiret (« Downtown soms dichte truck… », un « ✓ » en allemand). 15/10/2026.
            parts = re.split(r"(\s+[—–]\s+)", v)
            plan = []
            for p in parts:
                if re.fullmatch(r"\s+[—–]\s+", p): plan.append(("sep", p)); continue
                m = decouper(p) if p.strip() else []
                plan.append(("txt", len(textes), len(m))); textes.extend(m)
            poses.append((chemin, plan))
    for k in ("descripteurCourt", "arriveeIntro", "aquarelleAlt"):
        ajout(champs.get(k), (k,))
    for k in ("presentation", "specs"):
        v = champs.get(k)
        if isinstance(v, list):
            for i, x in enumerate(v): ajout(x, (k, i))
        else:
            ajout(v, (k,))
    for i, f in enumerate(champs.get("faq") or []):
        ajout(f.get("q"), ("faq", i, "q")); ajout(f.get("a"), ("faq", i, "a"))
    for i, c in enumerate(champs.get("checklist") or []):
        ajout(c.get("horizon"), ("checklist", i, "horizon"))
        for j, it in enumerate(c.get("items") or []): ajout(it, ("checklist", i, "items", j))
    def reconstruire(traduits):
        p = json.loads(json.dumps(champs))
        for chemin, plan in poses:
            val = "".join(x[1] if x[0] == "sep" else " ".join(traduits[x[1]:x[1] + x[2]]) for x in plan).strip()
            val = corriger(val)
            cible = p
            for c in chemin[:-1]: cible = cible[c]
            cible[chemin[-1]] = val
        return p
    return textes, reconstruire

def nom_garde(ville, champs, payload):
    """Le nom de la commune présent dans le français doit survivre (sinon : écarté)."""
    if not ville or len(ville) < 3: return True
    src, dst = json.dumps(champs, ensure_ascii=False), json.dumps(payload, ensure_ascii=False)
    return src.count(ville) == 0 or dst.count(ville) >= max(1, src.count(ville) // 2)

os.makedirs("resultats", exist_ok=True)
entree = f"lots/{LANG}.jsonl"
if not os.path.exists(entree):
    print("rien à traduire pour", LANG); sys.exit(0)
t0, ok, ecartes = time.time(), 0, 0
with open(entree, encoding="utf8") as fi, open(f"resultats/{LANG}.jsonl", "w", encoding="utf8") as fo:
    for ligne in fi:
        if time.time() - t0 > MAX_SECONDES:
            print("temps écoulé, on publie ce qui est fait"); break
        r = json.loads(ligne)
        textes, refaire = aplatir(r["champs"])
        if not textes: continue
        payload = refaire(traduire_lot(textes))
        if not nom_garde(r.get("ville", ""), r["champs"], payload):
            ecartes += 1; continue
        fo.write(json.dumps({"slug": r["slug"], "lang": LANG, "payload": payload}, ensure_ascii=False) + "\n")
        ok += 1
        if ok % 100 == 0: print(f"{LANG} : {ok} pages ({time.time() - t0:.0f} s)", flush=True)
print(f"{LANG} : {ok} traduites, {ecartes} écartées (nom de commune perdu), {time.time() - t0:.0f} s")
