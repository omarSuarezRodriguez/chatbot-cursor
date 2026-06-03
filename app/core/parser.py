"""Order Intelligence Engine — natural-language order parser with cart operations."""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from rapidfuzz import fuzz as _rapidfuzz

    _HAS_RAPIDFUZZ = True
except ImportError:
    _rapidfuzz = None  # type: ignore[assignment]
    _HAS_RAPIDFUZZ = False


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NUMBER_WORDS: Dict[str, int] = {
    "un": 1,
    "una": 1,
    "uno": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
    "seis": 6,
    "siete": 7,
    "ocho": 8,
    "nueve": 9,
    "diez": 10,
    "once": 11,
    "doce": 12,
}

_QTY_WORD_ALTS = "|".join(
    re.escape(word) for word in sorted(NUMBER_WORDS.keys(), key=len, reverse=True)
)

NOISE_WORDS = frozenset(
    {
        "quiero",
        "quero",
        "dame",
        "deme",
        "porfa",
        "porfavor",
        "favor",
        "mmm",
        "mm",
        "eh",
        "este",
        "esta",
        "eso",
        "esa",
        "pedir",
        "pedido",
        "pedidos",
        "ordenar",
        "orden",
        "necesito",
        "quisiera",
        "me",
        "gustaria",
        "ponme",
        "traeme",
        "trae",
        "agrega",
        "agregar",
        "anade",
        "añade",
        "añadir",
        "suma",
        "sumar",
        "tambien",
        "también",
        "mas",
        "más",
        "solo",
        "solamente",
        "favor",
        "hola",
        "buenas",
        "buenos",
        "dias",
        "tardes",
        "noches",
        "please",
        "pls",
        "ok",
        "vale",
        "listo",
        "ya",
        "ahora",
        "por",
        "para",
        "mi",
        "le",
        "mio",
        "mía",
        "escribi",
        "escribí",
        "escribo",
        "escribe",
        "de",
        "del",
        "la",
        "el",
        "los",
        "las",
        "un",
        "una",
        "unos",
        "unas",
        "sin",
        "algo",
        "alguna",
        "algun",
        "algún",
    }
)

# Token-level semantic hints (applied before menu matching, never invent products).
SYNONYM_TOKEN_MAP: Dict[str, str] = {
    "coca": "coca cola",
    "cola": "coca cola",
    "gaseosa": "coca cola",
    "gasosa": "coca cola",
    "refresco": "coca cola",
    "soda": "coca cola",
    "agua": "agua",
    "natural": "agua",
    "mineral": "agua",
    "hambre": "hamburguesa",
    "burger": "hamburguesa",
    "hamburgesa": "hamburguesa",
    "hamburgsa": "hamburguesa",
    "hambrguesa": "hamburguesa",
    "habasurguesa": "hamburguesa",
    "gaseoza": "coca cola",
    "gaseosa": "coca cola",
    "hamburguesa": "hamburguesa",
    "hamburguesas": "hamburguesa",
    "margarita": "margarita",
    "margaritas": "margarita",
    "hawaiana": "hawaiana",
    "hawaiano": "hawaiana",
    "hawaianas": "hawaiana",
    "hawaianos": "hawaiana",
    "cesar": "cesar",
    "césar": "cesar",
    "papas": "papas fritas",
    "papitas": "papas fritas",
    "fritas": "papas fritas",
    "frits": "papas fritas",
    "pizza": "pizza",
    "ensalada": "ensalada",
}

MENU_INTENT_TOKENS = frozenset({"menu", "carta", "catalogo", "catálogo", "lista", "ver"})

ORDER_INTENT_PHRASES = (
    "quiero comer",
    "tengo hambre",
    "algo de comer",
    "hacer pedido",
    "hacer un pedido",
)

COMMA_SPLIT_RE = re.compile(r"\s*,\s*")

PLUS_SPLIT_RE = re.compile(r"\s*\+\s*")
STAR_SPLIT_RE = re.compile(r"\s*\*\s*")

CONNECTOR_SPLIT_RE = re.compile(
    r"\s*(?:,|;|&|\band\b|\s+y\s+|\s+e\s+|\s+con\s+|\s+mas\s+|\s+más\s+|\s+también\s+|\s+tambien\s+)\s*",
    re.IGNORECASE,
)

COMPOUND_Y_RE = re.compile(r"\bde\s+(\w+)\s+y\s+(\w+)\b", re.IGNORECASE)
COMPOUND_Y_TOKEN = "__ingy__"

EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002700-\U000027BF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "]+",
    flags=re.UNICODE,
)

REPEAT_CHAR_RE = re.compile(r"([a-z])\1{2,}", re.UNICODE)

QTY_PREFIX_RE = re.compile(
    r"^(?:(\d+)\s*[x×]\s*|[x×]\s*(\d+)\s*|[x×](\d+)\s*|(\d+)\s+)(.*)$",
    re.IGNORECASE,
)

QTY_SUFFIX_RE = re.compile(r"^(.+?)\s+(\d+)\s*$")

SEGMENT_BOUNDARY_RE = re.compile(
    rf"(?<!\d)(?:(\d+)\s*[x×]\s*|[x×]\s*(\d+)\s*|[x×](\d+)\s*|(\d+)\s+|(?:(?:{_QTY_WORD_ALTS})\s+))",
    re.IGNORECASE,
)

ACCEPT_AUTO_SCORE = 0.80
ACCEPT_REVIEW_SCORE = 0.50
AMBIGUITY_DELTA = 0.05
TYPO_CORRECT_MIN_SCORE = 0.68
TYPO_CORRECT_MIN_GAP = 0.05
TYPO_VOCAB_MIN_LEN = 4


def log_parser_errors(
    *,
    wa_id: str = "",
    message: str = "",
    reason: str = "",
    parser_status: str = "",
    score: Optional[float] = None,
    unknown: Optional[List[str]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """Append parser audit events; never raises."""
    try:
        from app.config import PARSER_ERROR_LOG_PATH

        record: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "wa_id": wa_id,
            "message": message,
            "reason": reason,
            "parser_status": parser_status,
            "score": score,
            "unknown": unknown or [],
        }
        if extra:
            record.update(extra)
        path = Path(PARSER_ERROR_LOG_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        logger.exception("log_parser_errors failed (non-fatal)")


def _min_confidence(items: List[Dict[str, Any]]) -> Optional[float]:
    scores = [float(item.get("confidence", 0)) for item in items if item.get("confidence")]
    return min(scores) if scores else None


# Generic menu words — matching only these must not beat a distinctive token hit.
CATEGORY_STOPWORDS = frozenset(
    {
        "pizza",
        "pizzas",
        "hamburguesa",
        "hamburguesas",
        "ensalada",
        "ensaladas",
        "agua",
        "coca",
        "cola",
        "mineral",
        "clasica",
        "cesar",
        "clasico",
        "natural",
        "bebida",
        "bebidas",
    }
)


# ---------------------------------------------------------------------------
# Text normalization
# ---------------------------------------------------------------------------


def _strip_accents(value: str) -> str:
    """Fold áéíóú, ñ and other accented characters for stable menu matching."""
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def _singularize_token(token: str) -> str:
    """Reduce simple Spanish plurals for matching (pizzas → pizza)."""
    if len(token) <= 3:
        return token
    if token.endswith("iones"):
        return token[:-2]
    if token.endswith("anes") and len(token) > 5:
        return token[:-2]
    if token.endswith("ces") and len(token) > 4:
        return token[:-2] + "r"
    if token.endswith("as") and len(token) > 4:
        return token[:-1]
    if token.endswith("es") and len(token) > 4:
        return token[:-2]
    if token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _token_keys(text: str) -> set[str]:
    return {
        _singularize_token(_strip_accents(part))
        for part in text.split()
        if part and _singularize_token(_strip_accents(part)) not in CATEGORY_STOPWORDS
    }


def normalize(value: str) -> str:
    """Public lightweight normalizer (backward compatible)."""
    return TextNormalizer.basic(value)


class TextNormalizer:
    """Advanced normalization pipeline for chaotic WhatsApp input."""

    @staticmethod
    def basic(value: str) -> str:
        cleaned = value.lower().strip()
        cleaned = EMOJI_RE.sub(" ", cleaned)
        cleaned = _strip_accents(cleaned)
        cleaned = COMMA_SPLIT_RE.sub(" ", cleaned)
        cleaned = PLUS_SPLIT_RE.sub(" ", cleaned)
        cleaned = STAR_SPLIT_RE.sub(" ", cleaned)
        cleaned = re.sub(r"[^\w\s]", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip()

    @classmethod
    def advanced(cls, value: str, catalog_normalized: Optional[List[str]] = None) -> str:
        text = value.lower().strip()
        text = EMOJI_RE.sub(" ", text)
        text = _strip_accents(text)
        text = COMMA_SPLIT_RE.sub(" ", text)
        text = PLUS_SPLIT_RE.sub(" ", text)
        text = STAR_SPLIT_RE.sub(" ", text)
        text = REPEAT_CHAR_RE.sub(r"\1", text)
        text = re.sub(r"[^\w\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        if catalog_normalized:
            glued_tokens: List[str] = []
            for token in text.split():
                if re.search(r"\d", token):
                    glued_tokens.append(token)
                else:
                    glued_tokens.append(
                        cls._split_glued_words(token, catalog_normalized)
                    )
            text = " ".join(glued_tokens)
        text = cls._remove_noise_tokens(text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @staticmethod
    def _split_glued_words(text: str, catalog_names: List[str]) -> str:
        compact = text.replace(" ", "")
        if not compact:
            return text
        compact_to_spaced: Dict[str, str] = {}
        for spaced_name in catalog_names:
            if not spaced_name:
                continue
            compact_name = spaced_name.replace(" ", "")
            if len(compact_name) < 4:
                continue
            if compact_name not in compact_to_spaced or len(spaced_name) > len(
                compact_to_spaced[compact_name]
            ):
                compact_to_spaced[compact_name] = spaced_name

        for compact_name, spaced_name in compact_to_spaced.items():
            if compact == compact_name:
                return spaced_name
            for suffix in ("s", "es"):
                if compact == f"{compact_name}{suffix}":
                    return spaced_name

        spans: List[Tuple[int, int, str]] = []
        for compact_name, spaced_name in compact_to_spaced.items():
            start = 0
            while True:
                idx = compact.find(compact_name, start)
                if idx == -1:
                    break
                spans.append((idx, idx + len(compact_name), spaced_name))
                start = idx + 1
        if not spans:
            return text
        spans.sort(key=lambda s: (-(s[1] - s[0]), s[0]))
        used: List[Tuple[int, int]] = []
        chosen: List[Tuple[int, int, str]] = []
        for start, end, spaced_name in spans:
            if any(not (end <= u0 or start >= u1) for u0, u1 in used):
                continue
            used.append((start, end))
            chosen.append((start, end, spaced_name))
        if not chosen:
            return text
        chosen.sort(key=lambda s: s[0])
        rebuilt: List[str] = []
        cursor = 0
        for start, end, spaced_name in chosen:
            if start > cursor:
                gap = compact[cursor:start]
                if gap:
                    rebuilt.append(gap)
            rebuilt.append(spaced_name)
            cursor = end
        if cursor < len(compact):
            rebuilt.append(compact[cursor:])
        return " ".join(rebuilt)

    @staticmethod
    def _remove_noise_tokens(text: str) -> str:
        tokens = text.split()
        filtered = [
            t
            for t in tokens
            if t not in NOISE_WORDS or t in NUMBER_WORDS
        ]
        return " ".join(filtered)


# ---------------------------------------------------------------------------
# Fuzzy matching
# ---------------------------------------------------------------------------


class FuzzyMatcher:
    """Real numeric similarity scoring against dynamic menu catalog."""

    def __init__(self, catalog: List[Dict[str, Any]]) -> None:
        self.catalog = catalog
        self._vocabulary = self._build_vocabulary(catalog)

    @staticmethod
    def _build_vocabulary(catalog: List[Dict[str, Any]]) -> List[str]:
        words: set[str] = set()
        for entry in catalog:
            words.add(entry["normalized"])
            for token in entry.get("tokens", []):
                if len(token) >= TYPO_VOCAB_MIN_LEN:
                    words.add(token)
        return sorted(words, key=len, reverse=True)

    def _best_vocab_match(self, token: str) -> Tuple[str, float, float]:
        token_key = _strip_accents(token.lower())
        if len(token_key) < TYPO_VOCAB_MIN_LEN:
            return token, 0.0, 0.0
        if token_key in self._vocabulary:
            return token, 1.0, 0.0

        best_word = token
        best_score = 0.0
        second_score = 0.0
        for candidate in self._vocabulary:
            if abs(len(candidate) - len(token_key)) > 3:
                continue
            score = self._ratio(token_key, candidate)
            if score > best_score or (score == best_score and len(candidate) > len(best_word)):
                second_score = best_score
                best_score = score
                best_word = candidate
            elif score > second_score:
                second_score = score
        return best_word, best_score, second_score

    def _correct_typos(self, text: str) -> str:
        if not text:
            return text
        corrected: List[str] = []
        for token in text.split():
            candidate, score, second_score = self._best_vocab_match(token)
            if (
                score >= TYPO_CORRECT_MIN_SCORE
                and (score - second_score) >= TYPO_CORRECT_MIN_GAP
                and _strip_accents(candidate.lower()) != _strip_accents(token.lower())
            ):
                corrected.append(candidate)
            else:
                corrected.append(token)
        return " ".join(corrected)

    @staticmethod
    def _ratio(a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        if a == b:
            return 1.0
        if _HAS_RAPIDFUZZ and _rapidfuzz is not None:
            token_score = _rapidfuzz.token_set_ratio(a, b) / 100.0
            partial_score = _rapidfuzz.partial_ratio(a, b) / 100.0
            base_score = _rapidfuzz.ratio(a, b) / 100.0
            return max(token_score, partial_score, base_score)
        token_a = set(a.split())
        token_b = set(b.split())
        token_overlap = len(token_a & token_b) / max(len(token_a | token_b), 1)
        seq_score = SequenceMatcher(None, a, b).ratio()
        if a in b or b in a:
            return max(0.95, token_overlap, seq_score)
        return max(token_overlap, seq_score)

    def score_pair(self, query: str, item: Dict[str, Any]) -> float:
        normalized_query = query.strip()
        if not normalized_query:
            return 0.0

        target = item["normalized"]
        if normalized_query == target:
            return 1.0
        if normalized_query in target or target in normalized_query:
            return 0.95

        base = self._ratio(normalized_query, target)
        query_tokens = set(normalized_query.split())
        item_tokens = set(item["tokens"])
        if query_tokens and item_tokens:
            overlap = len(query_tokens & item_tokens) / max(len(query_tokens | item_tokens), 1)
            base = max(base, overlap)

        for alias in item.get("aliases", []):
            alias_score = self._ratio(normalized_query, alias)
            base = max(base, alias_score)

        q_keys = _token_keys(normalized_query)
        i_keys = _token_keys(target)
        distinctive = i_keys - CATEGORY_STOPWORDS
        if distinctive:
            hits = len(distinctive & q_keys)
            if hits == len(distinctive):
                base = max(base, 0.97)
            elif hits == 0:
                base = min(base, 0.62)

        return min(base, 1.0)

    def best_match(
        self, fragment: str
    ) -> Tuple[Optional[Dict[str, Any]], float, Optional[Dict[str, Any]], float]:
        query = TextNormalizer.advanced(
            fragment,
            [entry["normalized"] for entry in self.catalog],
        )
        query = self._correct_typos(query)
        query = self._apply_synonyms(query)
        if not query:
            return None, 0.0, None, 0.0

        ranked: List[Tuple[Dict[str, Any], float]] = []
        for item in self.catalog:
            ranked.append((item, self.score_pair(query, item)))
        ranked.sort(key=lambda pair: pair[1], reverse=True)

        if not ranked or ranked[0][1] < ACCEPT_REVIEW_SCORE:
            return None, 0.0, None, 0.0

        if (
            len(ranked) > 1
            and ranked[0][1] == ranked[1][1]
            and FuzzyMatcher.has_distinctive_winner(query, ranked[1][0], ranked[0][0])
        ):
            ranked[0], ranked[1] = ranked[1], ranked[0]

        best_item, best_score = ranked[0]
        second_score = ranked[1][1] if len(ranked) > 1 else 0.0
        second_item = ranked[1][0] if len(ranked) > 1 else None
        return best_item, best_score, second_item, second_score

    @staticmethod
    def has_distinctive_winner(
        query: str,
        best: Dict[str, Any],
        second: Dict[str, Any],
    ) -> bool:
        q_keys = _token_keys(query)
        best_keys = _token_keys(best["normalized"]) - CATEGORY_STOPWORDS
        second_keys = _token_keys(second["normalized"]) - CATEGORY_STOPWORDS
        best_hits = best_keys & q_keys
        second_hits = second_keys & q_keys
        if best_hits and not second_hits:
            return True
        if len(best_hits) > len(second_hits):
            return True
        return False

    @staticmethod
    def _apply_synonyms(text: str) -> str:
        tokens = text.split()
        expanded: List[str] = []
        i = 0
        while i < len(tokens):
            token = tokens[i]
            token_key = _strip_accents(token.lower())
            mapped = SYNONYM_TOKEN_MAP.get(token_key, SYNONYM_TOKEN_MAP.get(token, token))
            mapped_parts = mapped.split()
            expanded.extend(mapped_parts)
            skip = 0
            for j, part in enumerate(mapped_parts[1:], start=1):
                if (
                    i + j < len(tokens)
                    and _strip_accents(tokens[i + j].lower())
                    == _strip_accents(part.lower())
                ):
                    skip = j
            i += 1 + skip
        deduped: List[str] = []
        for token in expanded:
            if token and (not deduped or deduped[-1] != token):
                deduped.append(token)
        return " ".join(deduped)


# ---------------------------------------------------------------------------
# Segmentation & quantity extraction
# ---------------------------------------------------------------------------


class SegmentEngine:
    """Splits chaotic order text into quantity + product fragments."""

    @staticmethod
    def _preserve_compound_y(text: str) -> str:
        return COMPOUND_Y_RE.sub(
            lambda match: f"de {match.group(1)} {COMPOUND_Y_TOKEN} {match.group(2)}",
            text,
        )

    @staticmethod
    def _restore_compound_y(text: str) -> str:
        return text.replace(COMPOUND_Y_TOKEN, "y")

    @staticmethod
    def _split_by_connectors(raw: str) -> List[str]:
        chunks = [raw.strip()]
        for splitter in (COMMA_SPLIT_RE, PLUS_SPLIT_RE, STAR_SPLIT_RE):
            next_chunks: List[str] = []
            for chunk in chunks:
                next_chunks.extend(splitter.split(chunk))
            chunks = [part.strip() for part in next_chunks if part.strip()]
        return chunks

    @staticmethod
    def split_segments(text: str) -> List[str]:
        raw = text.strip()
        if not raw:
            return []

        comma_chunks = SegmentEngine._split_by_connectors(raw)
        if not comma_chunks:
            return []

        segments: List[str] = []
        for chunk in comma_chunks:
            normalized = TextNormalizer.basic(chunk)
            if not normalized:
                continue
            normalized = SegmentEngine._preserve_compound_y(normalized)
            parts = CONNECTOR_SPLIT_RE.split(normalized)
            for part in parts:
                part = SegmentEngine._restore_compound_y(part.strip())
                if not part:
                    continue
                segments.extend(SegmentEngine._split_numeric_boundaries(part))

        merged: List[str] = []
        for segment in segments:
            segment = segment.strip()
            if not segment:
                continue
            if merged and SegmentEngine._is_quantity_only(segment):
                prev_qty, prev_name = QuantityEngine.extract(merged[-1])
                extra_qty, _ = QuantityEngine.extract(segment)
                merged[-1] = f"{prev_qty + extra_qty} {prev_name}".strip()
                continue
            merged.append(segment)
        return merged

    @staticmethod
    def _split_numeric_boundaries(part: str) -> List[str]:
        matches = list(SEGMENT_BOUNDARY_RE.finditer(part))
        if not matches:
            return [part]

        chunks: List[str] = []
        cursor = 0
        for match in matches:
            if match.start() > cursor:
                prefix = part[cursor : match.start()].strip()
                if prefix:
                    chunks.append(prefix)
            cursor = match.start()

        tail = part[cursor:].strip()
        if tail:
            chunks.append(tail)

        if not chunks:
            return [part]
        return chunks

    @staticmethod
    def _is_quantity_only(segment: str) -> bool:
        cleaned = segment.strip()
        return bool(re.fullmatch(r"\d+", cleaned))


class QuantityEngine:
    """Robust quantity resolver: 2x, x2, digits, number words."""

    @staticmethod
    def _strip_leading_noise(text: str) -> str:
        tokens = text.split()
        while tokens and tokens[0] in NOISE_WORDS and tokens[0] not in NUMBER_WORDS:
            tokens.pop(0)
        return " ".join(tokens)

    @staticmethod
    def extract(segment: str) -> Tuple[int, str]:
        cleaned = TextNormalizer.basic(segment)
        cleaned = QuantityEngine._strip_leading_noise(cleaned)
        if not cleaned:
            return 1, ""

        match = QTY_PREFIX_RE.match(cleaned)
        if match:
            qty = int(match.group(1) or match.group(2) or match.group(3) or match.group(4))
            remainder = (match.group(5) or "").strip()
            return max(qty, 1), remainder

        for word, qty in NUMBER_WORDS.items():
            pattern = rf"^{word}\s+(.+)$"
            word_match = re.match(pattern, cleaned)
            if word_match:
                return qty, word_match.group(1).strip()

        suffix = QTY_SUFFIX_RE.match(cleaned)
        if suffix:
            name = suffix.group(1).strip()
            qty = int(suffix.group(2))
            if name and not re.fullmatch(r"\d+", name):
                return max(qty, 1), name

        return 1, cleaned

    @staticmethod
    def resolve(segment: str, catalog_norms: Optional[List[str]] = None) -> Tuple[int, str]:
        """Extract quantity from the raw segment, then product text for matching."""
        basic = TextNormalizer.basic(segment)
        qty, product_text = QuantityEngine.extract(basic)
        if not product_text:
            return qty, ""

        normalized = TextNormalizer.advanced(product_text, catalog_norms)
        _, product_text = QuantityEngine.extract(normalized)
        qty_check, _ = QuantityEngine.extract(
            TextNormalizer.advanced(segment, catalog_norms)
        )
        if qty_check != qty:
            raw_numbers = [int(value) for value in re.findall(r"\d+", basic)]
            if raw_numbers and raw_numbers[0] == qty:
                return qty, product_text or normalized
        return qty, product_text or normalized


# ---------------------------------------------------------------------------
# Order Intelligence Engine (core)
# ---------------------------------------------------------------------------


class OrderIntelligenceEngine:
    """
    Production-grade order interpretation pipeline.
    Menu is injected at construction time (dynamic, never hardcoded).
    """

    def __init__(self, menu_items: List[Dict[str, Any]]) -> None:
        self.menu_items = [item for item in menu_items if item.get("disponible", True)]
        self._catalog = self._build_catalog()
        self._matcher = FuzzyMatcher(self._catalog)
        self._catalog_by_name = {entry["nombre"].lower(): entry for entry in self._catalog}

    def _build_catalog(self) -> List[Dict[str, Any]]:
        catalog: List[Dict[str, Any]] = []
        for item in self.menu_items:
            name = str(item.get("nombre", "")).strip()
            normalized = TextNormalizer.basic(name)
            aliases = {normalized, *normalized.split()}
            for token, mapped in SYNONYM_TOKEN_MAP.items():
                if mapped.replace(" ", "") in normalized.replace(" ", ""):
                    aliases.add(token)
            catalog.append(
                {
                    "id": item.get("id"),
                    "nombre": name,
                    "precio": float(item.get("precio", 0)),
                    "categoria": item.get("categoria", ""),
                    "tokens": normalized.split(),
                    "normalized": normalized,
                    "aliases": sorted(aliases),
                }
            )
        return sorted(catalog, key=lambda entry: len(entry["normalized"]), reverse=True)

    def parse(self, text: str) -> Dict[str, Any]:
        """Canonical output contract."""
        raw = (text or "").strip()
        if not raw:
            return self._result([], "needs_clarification", ["entrada vacía"])

        normalized_full = TextNormalizer.advanced(
            raw,
            [entry["normalized"] for entry in self._catalog],
        )

        if self._is_menu_intent(normalized_full):
            return self._result([], "needs_clarification", ["intención de menú"])

        if self._is_order_intent_only(normalized_full):
            return self._result([], "needs_clarification", ["intención de pedido sin productos"])

        catalog_norms = [entry["normalized"] for entry in self._catalog]
        segments = SegmentEngine.split_segments(raw)
        if not segments:
            segments = [normalized_full] if normalized_full else []

        if not self._has_menu_token_overlap(normalized_full) and (
            self._is_gibberish(normalized_full) or len(_token_keys(normalized_full)) <= 1
        ):
            if len(segments) < 2:
                return self._fail_safe(["texto no interpretable"])

        parsed_items: List[Dict[str, Any]] = []
        unknown: List[str] = []
        needs_review = False

        for segment in segments:
            qty, product_text = QuantityEngine.resolve(segment, catalog_norms)
            if not product_text:
                continue
            product_text = FuzzyMatcher._apply_synonyms(product_text)
            if not product_text:
                continue

            best, score, second, second_score = self._matcher.best_match(product_text)
            if not best:
                unknown.append(segment)
                continue

            if (
                score < ACCEPT_AUTO_SCORE
                and not self._match_aligns_with_intent(product_text, best)
            ):
                unknown.append(segment)
                continue

            if score < ACCEPT_AUTO_SCORE:
                needs_review = True
            ambiguous = (
                second
                and second_score >= ACCEPT_REVIEW_SCORE
                and best["id"] != second["id"]
                and abs(score - second_score) <= AMBIGUITY_DELTA
                and not FuzzyMatcher.has_distinctive_winner(product_text, best, second)
            )
            if ambiguous:
                needs_review = True

            parsed_items.append(
                {
                    "product": best["nombre"],
                    "quantity": qty,
                    "product_id": best["id"],
                    "unit_price": best["precio"],
                    "confidence": round(score, 4),
                }
            )

        parsed_items = self._deduplicate(parsed_items)
        parsed_items, qa_unknown, qa_review = self._quality_assurance(raw, parsed_items)
        unknown.extend(qa_unknown)
        needs_review = needs_review or qa_review

        if not parsed_items:
            return self._fail_safe(unknown or ["sin productos reconocidos"])

        status = "ok" if not needs_review and not unknown else "needs_clarification"
        result = self._result(parsed_items, status, unknown)
        result["_internal"] = {
            "min_score": _min_confidence(parsed_items),
            "needs_review": needs_review,
            "ambiguous": needs_review and not unknown,
        }
        return result

    def _quality_assurance(
        self,
        raw: str,
        items: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], List[str], bool]:
        """Double-check: menu boundary, coherence, no invented products."""
        unknown: List[str] = []
        needs_review = False
        validated: List[Dict[str, Any]] = []

        for item in items:
            name_key = item["product"].lower()
            catalog_entry = self._catalog_by_name.get(name_key)
            if not catalog_entry:
                unknown.append(item["product"])
                needs_review = True
                continue
            if item.get("confidence", 0) < ACCEPT_REVIEW_SCORE:
                needs_review = True
            validated.append(item)

        validated = self._deduplicate(validated)
        if validated and not unknown:
            simulated = ", ".join(f"{i['quantity']} {i['product']}" for i in validated)
            raw_norm = TextNormalizer.basic(raw)
            if len(raw_norm) > 8 and len(simulated) < 3:
                needs_review = True

        return validated, unknown, needs_review

    @staticmethod
    def _deduplicate(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        merged: Dict[str, Dict[str, Any]] = {}
        for item in items:
            key = str(item.get("product_id") or item["product"]).lower()
            if key not in merged:
                merged[key] = dict(item)
            else:
                merged[key]["quantity"] += item["quantity"]
                merged[key]["confidence"] = max(
                    merged[key].get("confidence", 0),
                    item.get("confidence", 0),
                )
        return list(merged.values())

    def _fail_safe(self, unknown: List[str]) -> Dict[str, Any]:
        available = [entry["nombre"] for entry in self._catalog]
        return {
            "items": [],
            "total_items": 0,
            "status": "needs_clarification",
            "unknown": unknown,
            "menu_available": available,
            "_internal": {"min_score": None, "needs_review": True, "fail_safe": True},
        }

    @staticmethod
    def _result(
        items: List[Dict[str, Any]],
        status: str,
        unknown: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        public_items = [
            {"product": item["product"], "quantity": int(item["quantity"])}
            for item in items
        ]
        return {
            "items": public_items,
            "total_items": sum(item["quantity"] for item in public_items),
            "status": status,
            "unknown": unknown or [],
        }

    @staticmethod
    def _is_menu_intent(text: str) -> bool:
        tokens = {_strip_accents(token.lower()) for token in text.split()}
        menu_tokens = {_strip_accents(token.lower()) for token in MENU_INTENT_TOKENS}
        return bool(tokens & menu_tokens) and len(tokens) <= 3

    @staticmethod
    def _is_order_intent_only(text: str) -> bool:
        if any(phrase in text for phrase in ORDER_INTENT_PHRASES):
            return len(text.split()) <= 6
        return False

    def _has_menu_token_overlap(self, text: str) -> bool:
        basic = TextNormalizer.basic(text)
        if self._has_exact_menu_token_overlap(basic):
            return True
        corrected = self._matcher._correct_typos(basic)
        return corrected != basic and self._has_exact_menu_token_overlap(corrected)

    def _has_exact_menu_token_overlap(self, text: str) -> bool:
        query_tokens = set(text.split())
        if not query_tokens:
            return False
        for entry in self._catalog:
            menu_tokens = set(entry["normalized"].split())
            if query_tokens & menu_tokens:
                return True
        return False

    @staticmethod
    def _intent_tokens(product_text: str) -> set[str]:
        intents: set[str] = set()
        for token in TextNormalizer.basic(product_text).split():
            key = _strip_accents(token.lower())
            if key in NUMBER_WORDS:
                continue
            singular = _singularize_token(key)
            mapped = SYNONYM_TOKEN_MAP.get(key) or SYNONYM_TOKEN_MAP.get(singular)
            if mapped:
                intents.add(TextNormalizer.basic(mapped))
            if key not in CATEGORY_STOPWORDS:
                intents.add(TextNormalizer.basic(singular))
        return {intent for intent in intents if intent}

    @staticmethod
    def _match_aligns_with_intent(product_text: str, best: Dict[str, Any]) -> bool:
        intents = OrderIntelligenceEngine._intent_tokens(product_text)
        if not intents:
            return True
        target = best["normalized"]
        target_parts = set(target.split())
        for intent in intents:
            if intent in target:
                return True
            if any(part in target_parts for part in intent.split() if len(part) >= 4):
                return True
            if _token_keys(intent) & _token_keys(target):
                return True
        return False

    @staticmethod
    def _is_gibberish(text: str) -> bool:
        if not text or len(text) < 3:
            return True
        tokens = text.split()
        if len(tokens) == 1 and len(tokens[0]) >= 6:
            letters = re.sub(r"[^a-z]", "", tokens[0])
            if letters and len(set(letters)) <= 3:
                return True
            if not re.search(r"[aeiou]", letters) and len(letters) >= 5:
                return True
        return False


# ---------------------------------------------------------------------------
# Public facade (Flask / Twilio integration — backward compatible)
# ---------------------------------------------------------------------------


class OrderParser:
    """Facade used by OrderService; wraps OrderIntelligenceEngine."""

    def __init__(self, menu_items: List[Dict[str, Any]]) -> None:
        self.menu_items = [item for item in menu_items if item.get("disponible", True)]
        self._engine = OrderIntelligenceEngine(self.menu_items)
        self._catalog = self._engine._catalog
        self._matcher = self._engine._matcher

    def parse_order(self, text: str, wa_id: str = "") -> Dict[str, Any]:
        """Structured output contract for order interpretation."""
        result = self._engine.parse(text)
        self._audit_parse_result(text, result, wa_id=wa_id)
        return result

    @staticmethod
    def _audit_parse_result(text: str, result: Dict[str, Any], wa_id: str = "") -> None:
        status = result.get("status", "")
        unknown = result.get("unknown") or []
        internal = result.get("_internal") or {}
        if status == "ok" and not unknown and not internal.get("needs_review"):
            return
        reason = "needs_clarification"
        if internal.get("fail_safe"):
            reason = "fail_safe"
        elif unknown:
            reason = "unknown_segments"
        elif internal.get("ambiguous"):
            reason = "ambiguity"
        log_parser_errors(
            wa_id=wa_id,
            message=text,
            reason=reason,
            parser_status=status,
            score=internal.get("min_score"),
            unknown=unknown,
            extra={"total_items": result.get("total_items", 0)},
        )

    def _match_product(self, fragment: str) -> Optional[Dict[str, Any]]:
        best, score, _, _ = self._matcher.best_match(fragment)
        return best if best and score >= ACCEPT_REVIEW_SCORE else None

    def _extract_quantity(self, text: str) -> Tuple[int, str]:
        return QuantityEngine.extract(text)

    def _split_segments(self, text: str) -> List[str]:
        return SegmentEngine.split_segments(text)

    def _cart_from_parse(
        self, result: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        items: List[Dict[str, Any]] = []
        for entry in result.get("items", []):
            matched = self._catalog_by_name(entry["product"])
            if not matched:
                continue
            qty = entry["quantity"]
            items.append(
                {
                    "product_id": matched["id"],
                    "product": matched["nombre"],
                    "qty": qty,
                    "unit_price": matched["precio"],
                    "subtotal": round(qty * matched["precio"], 2),
                }
            )
        unknown = list(result.get("unknown", []))
        return items, unknown

    def parse_additions(self, text: str) -> Tuple[List[Dict[str, Any]], List[str]]:
        result = self._engine.parse(text)
        items, unknown = self._cart_from_parse(result)
        if result.get("status") == "needs_clarification" and not items:
            segments = self._split_segments(text)
            unknown.extend(segments)
        return items, unknown

    def _catalog_by_name(self, product_name: str) -> Optional[Dict[str, Any]]:
        for entry in self._catalog:
            if entry["nombre"].lower() == product_name.lower():
                return entry
        return None

    def parse_remove(self, text: str) -> Tuple[List[str], List[str]]:
        cleaned = TextNormalizer.basic(text)
        cleaned = re.sub(
            r"^(quita|quitar|elimina|eliminar|saca|sacar|borra|borrar)\s+",
            "",
            cleaned,
        )
        removed: List[str] = []
        unknown: List[str] = []
        for segment in self._split_segments(cleaned):
            matched = self._match_product(segment)
            if matched:
                removed.append(matched["nombre"])
            else:
                unknown.append(segment)
        return removed, unknown

    def parse_replace(self, text: str) -> Tuple[Optional[str], Optional[str], List[str]]:
        cleaned = TextNormalizer.basic(text)
        patterns = [
            r"cambia\s+(.+?)\s+por\s+(.+)",
            r"reemplaza\s+(.+?)\s+por\s+(.+)",
            r"cambiar\s+(.+?)\s+por\s+(.+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, cleaned)
            if not match:
                continue
            old_fragment, new_fragment = match.group(1).strip(), match.group(2).strip()
            old_item = self._match_product(old_fragment)
            new_item = self._match_product(new_fragment)
            if old_item and new_item:
                return old_item["nombre"], new_item["nombre"], []
            unknown: List[str] = []
            if not old_item:
                unknown.append(old_fragment)
            if not new_item:
                unknown.append(new_fragment)
            return None, None, unknown
        return None, None, []

    def apply_message(
        self,
        text: str,
        current_cart: Optional[List[Dict[str, Any]]] = None,
        wa_id: str = "",
    ) -> Dict[str, Any]:
        cart = [dict(item) for item in (current_cart or [])]
        notes: List[str] = []
        unknown: List[str] = []
        cleaned = TextNormalizer.basic(text)

        if re.search(r"\b(quita|quitar|elimina|eliminar|saca|sacar|borra|borrar)\b", cleaned):
            removed, unknown_remove = self.parse_remove(text)
            unknown.extend(unknown_remove)
            if removed:
                cart = [item for item in cart if item["product"] not in removed]
                notes.append(f"Eliminé: {', '.join(removed)}.")
            return {"items": cart, "notes": notes, "unknown": unknown}

        old_name, new_name, unknown_replace = self.parse_replace(text)
        unknown.extend(unknown_replace)
        if old_name and new_name:
            replaced = False
            for item in cart:
                if item["product"] == old_name:
                    new_match = self._match_product(new_name)
                    if new_match:
                        item["product_id"] = new_match["id"]
                        item["product"] = new_match["nombre"]
                        item["unit_price"] = new_match["precio"]
                        item["subtotal"] = round(item["qty"] * new_match["precio"], 2)
                        replaced = True
            if replaced:
                notes.append(f"Cambié {old_name} por {new_name}.")
            return {"items": cart, "notes": notes, "unknown": unknown}

        parse_snapshot = self._engine.parse(text)
        additions, unknown_add = self._cart_from_parse(parse_snapshot)
        unknown.extend(unknown_add)
        self._audit_parse_result(text, parse_snapshot, wa_id=wa_id)

        for addition in additions:
            found = False
            for item in cart:
                if item["product"] == addition["product"]:
                    item["qty"] += addition["qty"]
                    item["subtotal"] = round(item["qty"] * item["unit_price"], 2)
                    found = True
                    break
            if not found:
                cart.append(addition)

        return {"items": cart, "notes": notes, "unknown": unknown}

    @staticmethod
    def cart_total(items: List[Dict[str, Any]]) -> float:
        return round(sum(item.get("subtotal", 0) for item in items), 2)

    @staticmethod
    def format_cart(items: List[Dict[str, Any]]) -> str:
        if not items:
            return "Tu carrito está vacío."
        lines = []
        for item in items:
            lines.append(
                f"• {item['qty']} x {item['product']} — ${item['subtotal']:.2f}"
            )
        total = OrderParser.cart_total(items)
        lines.append(f"\n*Total: ${total:.2f}*")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal validation suite (regression guard)
# ---------------------------------------------------------------------------

_VALIDATION_MENU: List[Dict[str, Any]] = [
    {"id": "t1", "nombre": "Papas Fritas", "precio": 4.0, "categoria": "Sides", "disponible": True},
    {
        "id": "t2",
        "nombre": "Hamburguesa Clásica",
        "precio": 9.5,
        "categoria": "Hamburguesas",
        "disponible": True,
    },
    {"id": "t3", "nombre": "Agua Mineral", "precio": 1.5, "categoria": "Bebidas", "disponible": True},
]

_DEMO_VALIDATION_MENU: List[Dict[str, Any]] = [
    {"id": "1", "nombre": "Pizza Hawaiana", "precio": 12.5, "categoria": "Pizzas", "disponible": True},
    {"id": "2", "nombre": "Pizza Margarita", "precio": 11.0, "categoria": "Pizzas", "disponible": True},
    {
        "id": "3",
        "nombre": "Hamburguesa Clásica",
        "precio": 9.5,
        "categoria": "Hamburguesas",
        "disponible": True,
    },
    {"id": "4", "nombre": "Coca Cola", "precio": 2.5, "categoria": "Bebidas", "disponible": True},
    {"id": "5", "nombre": "Agua Mineral", "precio": 1.5, "categoria": "Bebidas", "disponible": True},
    {"id": "6", "nombre": "Ensalada César", "precio": 8.0, "categoria": "Ensaladas", "disponible": True},
]


def _find_item(items: List[Dict[str, Any]], product_fragment: str) -> Optional[Dict[str, Any]]:
    fragment = _strip_accents(product_fragment.lower())
    for item in items:
        if fragment in _strip_accents(item["product"].lower()):
            return item
    return None


def _qty_for(items: List[Dict[str, Any]], product_fragment: str) -> int:
    found = _find_item(items, product_fragment)
    return int(found["quantity"]) if found else 0


def run_validation_suite(verbose: bool = True) -> bool:
    """
    Executable regression tests for the Order Intelligence Engine.
    Safe to call in development; does not mutate external state.
    """
    failures: List[str] = []
    total = 0

    def check(label: str, condition: bool, detail: str = "") -> None:
        nonlocal total
        total += 1
        if not condition:
            failures.append(f"{label}: {detail}".strip())

    basic_engine = OrderIntelligenceEngine(_VALIDATION_MENU)
    demo_engine = OrderIntelligenceEngine(_DEMO_VALIDATION_MENU)

    case1 = basic_engine.parse("2 papas fritas")
    check(
        "2 papas fritas",
        case1["status"] == "ok" and _qty_for(case1["items"], "papas") == 2,
        str(case1),
    )

    case2 = basic_engine.parse("peeeedido 3 hamburgesa")
    check(
        "peeeedido 3 hamburgesa",
        case2["status"] == "ok" and _qty_for(case2["items"], "hamburguesa") == 3,
        str(case2),
    )

    case3 = basic_engine.parse("asdfgh")
    check(
        "asdfgh fail-safe",
        case3["status"] == "needs_clarification" and case3["total_items"] == 0,
        str(case3),
    )

    case4 = basic_engine.parse("2 papas fritas y agua 3 hamburguesas")
    check(
        "2 papas fritas y agua 3 hamburguesas",
        case4["status"] == "ok"
        and _qty_for(case4["items"], "papas") == 2
        and _qty_for(case4["items"], "agua") == 1
        and _qty_for(case4["items"], "hamburguesa") == 3,
        str(case4),
    )

    user_order = (
        "quiero dos pizzas hawaianas, dos pizza margarita, una hamburgsa clasica, "
        "dos agua mineral y 5 ensaladas cesar"
    )
    case5 = demo_engine.parse(user_order)
    check(
        "pedido largo con comas (usuario)",
        case5["status"] == "ok"
        and not case5.get("unknown")
        and _qty_for(case5["items"], "hawaiana") == 2
        and _qty_for(case5["items"], "margarita") == 2
        and _qty_for(case5["items"], "hamburguesa") == 1
        and _qty_for(case5["items"], "agua") == 2
        and _qty_for(case5["items"], "cesar") == 5,
        str(case5),
    )

    apply5 = OrderParser(_DEMO_VALIDATION_MENU).apply_message(user_order)
    check(
        "apply_message pedido largo sin unknown",
        len(apply5["items"]) == 5 and not apply5.get("unknown"),
        str(apply5),
    )

    case6 = demo_engine.parse("dos pizza margarita,una hamburgsa clasica")
    check(
        "comas sin espacios",
        case6["status"] == "ok"
        and _qty_for(case6["items"], "margarita") == 2
        and _qty_for(case6["items"], "hamburguesa") == 1,
        str(case6),
    )

    case7 = demo_engine.parse("2 pizzas hawaiana 1 ensalada césar")
    check(
        "tildes en producto",
        case7["status"] == "ok"
        and _qty_for(case7["items"], "hawaiana") == 2
        and _qty_for(case7["items"], "cesar") == 1,
        str(case7),
    )

    case8 = demo_engine.parse("pizzahawaiana y pizzamargarita")
    check(
        "palabras pegadas",
        case8["status"] == "ok"
        and _find_item(case8["items"], "hawaiana")
        and _find_item(case8["items"], "margarita"),
        str(case8),
    )

    case9 = demo_engine.parse("3 coca cola, 2 gaseosa")
    check(
        "sinonimos bebidas",
        case9["status"] == "ok" and _qty_for(case9["items"], "coca") >= 3,
        str(case9),
    )

    case10 = demo_engine.parse("menu")
    check(
        "intencion menu sin productos",
        case10["total_items"] == 0 and case10["status"] == "needs_clarification",
        str(case10),
    )

    case10b = demo_engine.parse("men\u00fa")
    check(
        "intencion menu con tilde",
        case10b["total_items"] == 0 and case10b["status"] == "needs_clarification",
        str(case10b),
    )

    case11 = demo_engine.parse("2 hamburgesa & 1 agua")
    check(
        "conector ampersand",
        case11["status"] == "ok"
        and _qty_for(case11["items"], "hamburguesa") == 2
        and _qty_for(case11["items"], "agua") == 1,
        str(case11),
    )

    case11b = demo_engine.parse("dos pizzas, dos hamburguesas con dos aguas")
    check(
        "conector con como y",
        case11b["status"] in {"ok", "needs_clarification"}
        and len(case11b["items"]) == 3
        and _qty_for(case11b["items"], "hamburguesa") == 2
        and _qty_for(case11b["items"], "agua") == 2,
        str(case11b),
    )

    case11c = demo_engine.parse("2 pizzas, 2 hamburguesas con 2 aguas")
    check(
        "conector con con cantidades numericas",
        case11c["status"] in {"ok", "needs_clarification"}
        and len(case11c["items"]) == 3
        and _qty_for(case11c["items"], "hamburguesa") == 2
        and _qty_for(case11c["items"], "agua") == 2,
        str(case11c),
    )

    case12 = demo_engine.parse("hamburguesa + agua")
    check(
        "conector plus",
        case12["status"] == "ok"
        and _find_item(case12["items"], "hamburguesa")
        and _find_item(case12["items"], "agua"),
        str(case12),
    )

    case13 = basic_engine.parse("peeedido dos hamburgesas y una agua")
    check(
        "errores ortograficos extremos",
        _qty_for(case13["items"], "hamburguesa") >= 2 and _qty_for(case13["items"], "agua") >= 1,
        str(case13),
    )

    extended_menu: List[Dict[str, Any]] = [
        {"id": "p1", "nombre": "Pizza de Jamon y Queso", "precio": 95.0, "categoria": "Pizzas", "disponible": True},
        {"id": "p2", "nombre": "Pizza Mexicana", "precio": 25.0, "categoria": "Pizzas", "disponible": True},
        {"id": "p3", "nombre": "Pizza Ranchera", "precio": 15.0, "categoria": "Pizzas", "disponible": True},
        {"id": "b1", "nombre": "Coca Cola", "precio": 8.0, "categoria": "Bebidas", "disponible": True},
        {"id": "h1", "nombre": "Hamburguesa Mega", "precio": 20.0, "categoria": "Hamburguesas", "disponible": True},
        {"id": "h2", "nombre": "Hamburguesa Doble Carne", "precio": 22.0, "categoria": "Hamburguesas", "disponible": True},
        {"id": "h3", "nombre": "Hamburguesa Doble Pollo", "precio": 15.0, "categoria": "Hamburguesas", "disponible": True},
    ]
    user_long_order = (
        "quiero por favor dos pizzas de jamon y queso, tres pizzas mexicanas, "
        "4 pizzas rancheras, 5 coca colas, 7 hamburguesas mega ocho hamburguesas "
        "doble carne una habasurguesa doble pollo"
    )
    case14 = OrderIntelligenceEngine(extended_menu).parse(user_long_order)
    check(
        "pedido largo jamon y queso y hamburguesas variadas",
        case14["status"] in {"ok", "needs_clarification"}
        and len(case14["items"]) == 7
        and _qty_for(case14["items"], "jamon") == 2
        and _qty_for(case14["items"], "mexicana") == 3
        and _qty_for(case14["items"], "ranchera") == 4
        and _qty_for(case14["items"], "coca") == 5
        and _qty_for(case14["items"], "mega") == 7
        and _qty_for(case14["items"], "doble carne") == 8
        and _qty_for(case14["items"], "doble pollo") == 1,
        str(case14),
    )

    case15 = demo_engine.parse("hbogruesa")
    check(
        "typo general hbogruesa",
        case15["status"] in {"ok", "needs_clarification"}
        and _qty_for(case15["items"], "hamburguesa") >= 1,
        str(case15),
    )

    case16 = demo_engine.parse("2 piza hawaiana")
    check(
        "typo general piza",
        case16["status"] in {"ok", "needs_clarification"}
        and _qty_for(case16["items"], "hawaiana") == 2,
        str(case16),
    )

    large_qty_menu: List[Dict[str, Any]] = [
        {"id": "p1", "nombre": "Pizza de Jamon y Queso", "precio": 95.0, "categoria": "Pizzas", "disponible": True},
        {"id": "p2", "nombre": "Pizza Hawaiana", "precio": 125.0, "categoria": "Pizzas", "disponible": True},
        {"id": "h1", "nombre": "Hamburguesa Clasica", "precio": 125.0, "categoria": "Hamburguesas", "disponible": True},
        {"id": "h2", "nombre": "Hamburguesa Mega", "precio": 11.0, "categoria": "Hamburguesas", "disponible": True},
        {"id": "b1", "nombre": "Coca Cola", "precio": 8.0, "categoria": "Bebidas", "disponible": True},
    ]
    large_qty_order = (
        "quiero por favor 60 hamburgsdfesas clasiccscas, 2333 hamburgueas mega, "
        "12123 cocas con 777 pirzas harwewaianas y 8 picsas de jamon y quieso"
    )
    case17 = OrderIntelligenceEngine(large_qty_menu).parse(large_qty_order)
    check(
        "cantidades grandes y repetidas",
        case17["status"] in {"ok", "needs_clarification"}
        and _qty_for(case17["items"], "clasica") == 60
        and _qty_for(case17["items"], "mega") == 2333
        and _qty_for(case17["items"], "coca") == 12123
        and _qty_for(case17["items"], "hawaiana") == 777
        and _qty_for(case17["items"], "jamon") == 8,
        str(case17),
    )

    case18 = demo_engine.parse(
        "le escribi dos pizzas hawaianas, dos cocacolas dos hamburguesas de carne y un agua"
    )
    check(
        "prefijo conversacional no suma items fantasma",
        case18["status"] in {"ok", "needs_clarification"}
        and _qty_for(case18["items"], "hawaiana") == 2
        and _qty_for(case18["items"], "coca") == 2
        and _qty_for(case18["items"], "hamburguesa") == 2
        and _qty_for(case18["items"], "agua") == 1,
        str(case18),
    )

    user_bug_menu: List[Dict[str, Any]] = [
        {"id": "1", "nombre": "Hawaiana", "precio": 125.0, "categoria": "Pizzas", "disponible": True},
        {"id": "b1", "nombre": "Coca Cola", "precio": 25.0, "categoria": "Bebidas", "disponible": True},
        {"id": "b2", "nombre": "Agua", "precio": 11.0, "categoria": "Bebidas", "disponible": True},
    ]
    case19 = OrderIntelligenceEngine(user_bug_menu).parse(
        "* 2 pizza hawaiana, 1 coca cola\n* una hamburguesa y dos aguas"
    )
    check(
        "asteriscos whatsapp sin fusionar coca con hamburguesa",
        _qty_for(case19["items"], "hawaiana") == 2
        and _qty_for(case19["items"], "coca") == 1
        and _qty_for(case19["items"], "agua") == 2
        and any("hamburguesa" in str(u).lower() for u in case19.get("unknown", [])),
        str(case19),
    )

    if verbose:
        passed = total - len(failures)
        if failures:
            print("PARSER VALIDATION FAILURES:")
            for failure in failures:
                print(f"  - {failure}")
            print(f"PARSER VALIDATION: {passed}/{total}")
        else:
            print(f"PARSER VALIDATION: OK ({total}/{total})")

    return not failures


if __name__ == "__main__":
    import sys

    ok = run_validation_suite(verbose=True)
    sys.exit(0 if ok else 1)
