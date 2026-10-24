"""Build 'where to buy online' SEARCH links from product names in treatment advice.
Search links only: never invents product pages, prices or availability."""
import re
from urllib.parse import quote_plus

ORGANIC_BUYABLE = ("neem", "trichoderma", "pseudomonas", "bacillus", "bordeaux",
                   "copper", "sulphur", "sulfur", "bio-")
GENERIC = re.compile(r"consult|kvk|officer|agri shop|local|nearest|remove|avoid|maintain|monitor|"
                     r"destroy|spacing|irrigation", re.I)
DOSE = re.compile(r"\d+(?:\.\d+)?\s*(?:g|gm|kg|ml|l|ltr|litre|liter|cc)\b(?:\s*/\s*\w+)?", re.I)


def _clean_product(item: str):
    s = (item or "").strip()
    if not s or GENERIC.search(s):
        return None
    s = re.sub(r"^(spray|apply|use|drench|dust|foliar spray of)\s+", "", s, flags=re.I)
    s = re.split(r"\s*(?:@|\bat\b|\bper\b|\bin\b|\bwith\b|[:;–—]|\s-\s|,)", s, maxsplit=1)[0]
    s = DOSE.sub("", s).strip(" .()-")
    words = s.split()
    if len(s) < 4 or not re.search(r"[A-Za-z]", s) or len(words) > 7:
        return None
    return s


def products_from_remedies(remedies: dict, max_products: int = 3):
    items = list(remedies.get("chemical", []))
    items += [o for o in remedies.get("organic", []) if any(k in o.lower() for k in ORGANIC_BUYABLE)]
    seen, out = set(), []
    for it in items:
        name = _clean_product(it)
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        out.append({
            "name": name,
            "amazon": f"https://www.amazon.in/s?k={quote_plus(name + ' agriculture India')}",
            "bighaat": f"https://www.bighaat.com/search?q={quote_plus(name)}",   # VERIFY this pattern once
        })
        if len(out) >= max_products:
            break
    return out


def format_buy_message(products, header: str, note: str) -> str:
    lines = [header, ""]
    for p in products:
        lines += [f"• {p['name']}", f"  Amazon.in: {p['amazon']}", f"  BigHaat: {p['bighaat']}"]
    lines += ["", note]
    return "\n".join(lines)