from flask import Blueprint, request, jsonify
from models import Translation
from services.translate import nllb_translator
from rapidfuzz import fuzz, process
import re
from collections import Counter

corpus_bp = Blueprint("corpus", __name__)

# --- Language mappings ---
field_map = {
    "zul": "isizulu_text",
    "eng": "english_text"
}

nllb_map = {
    "zul": "zul_Latn",
    "xho": "xho_Latn",
    "eng": "eng_Latn"
}


# --- Helpers ---
def normalize_text(text: str) -> str:
    text = str(text).lower()
    text = re.sub(r"[^a-zA-Z\u00C0-\u017F\s']", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()



def get_common_pairs(sentence: str, lang: str, top_n: int = 5):
    """Return common word pairs from dataset that relate to words in sentence."""
    if lang not in field_map:  # isiXhosa not supported yet
        return []

    field = field_map[lang]
    tokens = sentence.split()

    # Fetch all sentences from DB
    all_rows = Translation.query.with_entities(getattr(Translation, field)).all()

    bigram_counter = Counter()

    for (sent,) in all_rows:
        if not sent:
            continue
        words = sent.lower().split()
        for i in range(len(words) - 1):
            bigram = f"{words[i]} {words[i+1]}"
            bigram_counter[bigram] += 1

    # Filter bigrams that contain at least one word from the query
    related_pairs = [pair for pair, _ in bigram_counter.most_common()
                     if any(w in pair for w in tokens)]

    return related_pairs[:top_n]

def analyze_word(word: str, lang: str):
    results = {"frequency": 0, "examples": []}

    if lang not in field_map:  # e.g. isiXhosa
        return results

    field = field_map[lang]
    candidates = Translation.query.filter(
        getattr(Translation, field).ilike(f"%{word}%")
    ).all()

    if candidates:
        results["frequency"] = len(candidates)
        examples = []
        seen = set()
        for c in candidates[:10]:  # fetch more rows
            sentence = getattr(c, field)
            words = sentence.split()
            short_sent = " ".join(words[:7])  # ≤7 words now
            if short_sent not in seen:        # avoid duplicates
                examples.append(short_sent)
                seen.add(short_sent)
            if len(examples) >= 3:            # stop at 3 unique
                break
        results["examples"] = examples

    return results


def get_translation(sentence: str, src_lang: str, tgt_lang: str):
    if src_lang == "xho" or tgt_lang == "xho":
        # always NLLB for isiXhosa
        return nllb_translator.translate(
            sentence, src_lang=nllb_map[src_lang], tgt_lang=nllb_map[tgt_lang]
        )

    src_field = field_map[src_lang]
    tgt_field = field_map[tgt_lang]

    # 1. Fetch all rows
    candidates = Translation.query.all()
    if not candidates:
        return nllb_translator.translate(
            sentence, src_lang=nllb_map[src_lang], tgt_lang=nllb_map[tgt_lang]
        )

    # 2. Build search space
    search_space = [getattr(c, src_field) for c in candidates if getattr(c, src_field)]

    # 3. Fuzzy match against corpus
    best = process.extractOne(sentence, search_space, scorer=fuzz.token_sort_ratio)

    if best:
        best_match, score, idx = best
        if score > 70:  # threshold
            matched_row = candidates[idx]
            # ✅ return FULL DB translation (not cut)
            return getattr(matched_row, tgt_field)

    # 4. Fallback → NLLB
    return nllb_translator.translate(
        sentence, src_lang=nllb_map[src_lang], tgt_lang=nllb_map[tgt_lang]
    )


@corpus_bp.route("/analyze", methods=["POST"])
def analyze_sentence():
    data = request.get_json()
    if not data or "sentence" not in data or "src_lang" not in data or "tgt_lang" not in data:
        return jsonify({"error": "Request must include 'sentence', 'src_lang' and 'tgt_lang'"}), 400

    sentence = normalize_text(data["sentence"])
    src_lang = data["src_lang"]
    tgt_lang = data["tgt_lang"]

    # 1. Translation
    translation = get_translation(sentence, src_lang, tgt_lang)

    if src_lang == "xho" or tgt_lang == "xho":
        # isiXhosa → only translation
        return jsonify({"query": sentence, "translation": translation})

    # 2. Word stats + examples
    tokens = sentence.split()
    word_analysis = {w: analyze_word(w, src_lang) for w in tokens}

    # 3. Common pairs from corpus
    common_pairs = get_common_pairs(sentence, src_lang)

    return jsonify({
        "query": sentence,
        "translation": translation,
        "analysis": {
            "word_stats": {w: word_analysis[w]["frequency"] for w in tokens},
            "examples": {w: word_analysis[w]["examples"] for w in tokens},
            "common_pairs": common_pairs
        }
    })
