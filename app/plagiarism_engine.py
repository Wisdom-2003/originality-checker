import json
import urllib.parse
import urllib.requestimport re
import math
from dataclasses import dataclass
from collections import Counter
from typing import List


def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s'-]", " ", text)
    return text.strip()


def tokenize(text: str) -> List[str]:
    return normalize(text).split()


def segment_passages(
    text: str,
    min_words: int = 25,
    max_words: int = 120
) -> List[str]:

    paragraphs = re.split(r"\n\s*\n+", text)
    passages = []

    for paragraph in paragraphs:
        paragraph = paragraph.strip()

        if not paragraph:
            continue

        tokens = paragraph.split()

        if len(tokens) <= max_words:
            if len(tokens) >= min_words:
                passages.append(paragraph)
            continue

        step = max_words - 25

        for start in range(0, len(tokens), step):
            chunk = tokens[start:start + max_words]

            if len(chunk) >= min_words:
                passages.append(" ".join(chunk))

    return passages


def shingles(text: str, size: int = 7) -> set:
    tokens = tokenize(text)

    if len(tokens) < size:
        return set()

    return {
        " ".join(tokens[i:i + size])
        for i in range(len(tokens) - size + 1)
    }


def fingerprint_score(a: str, b: str) -> float:
    sa = shingles(a)
    sb = shingles(b)

    if not sa or not sb:
        return 0.0

    intersection = len(sa & sb)
    union = len(sa | sb)

    if union == 0:
        return 0.0

    return intersection / union * 100


def lexical_score(a: str, b: str) -> float:
    wa = Counter(tokenize(a))
    wb = Counter(tokenize(b))

    if not wa or not wb:
        return 0.0

    common = sum(
        min(wa[word], wb[word])
        for word in wa.keys() & wb.keys()
    )

    total = max(
        sum(wa.values()),
        sum(wb.values())
    )

    if total == 0:
        return 0.0

    return common / total * 100


def cosine_similarity(a: str, b: str) -> float:
    wa = Counter(tokenize(a))
    wb = Counter(tokenize(b))

    vocabulary = set(wa) | set(wb)

    if not vocabulary:
        return 0.0

    dot = sum(
        wa[x] * wb[x]
        for x in vocabulary
    )

    magnitude_a = math.sqrt(
        sum(wa[x] ** 2 for x in vocabulary)
    )

    magnitude_b = math.sqrt(
        sum(wb[x] ** 2 for x in vocabulary)
    )

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return (
        dot /
        (magnitude_a * magnitude_b)
    ) * 100


def exact_score(a: str, b: str) -> float:
    na = normalize(a)
    nb = normalize(b)

    if not na or not nb:
        return 0.0

    if na == nb:
        return 100.0

    if len(na) < 40 or len(nb) < 40:
        return 0.0

    if na in nb or nb in na:
        return 90.0

    return 0.0


def confidence_for(
    exact: float,
    fingerprint: float,
    lexical: float,
    semantic: float
) -> str:

    if exact >= 90:
        return "Very High"

    if fingerprint >= 55:
        return "High"

    if fingerprint >= 30 and lexical >= 55:
        return "High"

    if lexical >= 50 or semantic >= 65:
        return "Medium"

    if fingerprint >= 12 or lexical >= 30:
        return "Low"

    return "Minimal"


@dataclass
class Passage:
    id: int
    text: str


@dataclass
class Source:
    title: str
    url: str
    text: str
    source_type: str = "web"


@dataclass
class Match:
    passage_id: int
    source_title: str
    source_url: str
    source_type: str
    passage: str
    source_text: str
    exact: float
    fingerprint: float
    lexical: float
    semantic: float
    score: float
    confidence: str


def compare_passage(
    passage: Passage,
    source: Source
) -> Match:

    exact = exact_score(
        passage.text,
        source.text
    )

    fingerprint = fingerprint_score(
        passage.text,
        source.text
    )

    lexical = lexical_score(
        passage.text,
        source.text
    )

    semantic = cosine_similarity(
        passage.text,
        source.text
    )

    score = (
        exact * 0.35 +
        fingerprint * 0.30 +
        lexical * 0.20 +
        semantic * 0.15
    )

    confidence = confidence_for(
        exact,
        fingerprint,
        lexical,
        semantic
    )

    return Match(
        passage_id=passage.id,
        source_title=source.title,
        source_url=source.url,
        source_type=source.source_type,
        passage=passage.text,
        source_text=source.text,
        exact=round(exact, 2),
        fingerprint=round(fingerprint, 2),
        lexical=round(lexical, 2),
        semantic=round(semantic, 2),
        score=round(score, 2),
        confidence=confidence
    )


def compare_local_documents(
    document_text: str,
    sources: List[Source],
    threshold: float = 15
):

    raw_passages = segment_passages(
        document_text
    )

    passages = [
        Passage(i + 1, text)
        for i, text in enumerate(raw_passages)
    ]

    matches = []

    for passage in passages:

        best_match = None

        for source in sources:

            result = compare_passage(
                passage,
                source
            )

            if result.score >= threshold:

                if (
                    best_match is None
                    or result.score > best_match.score
                ):
                    best_match = result

        if best_match:
            matches.append(best_match)

    return deduplicate_matches(matches)


def deduplicate_matches(
    matches: List[Match]
):

    unique = {}

    for match in matches:

        key = (
            match.passage_id,
            match.source_url
        )

        if (
            key not in unique
            or match.score > unique[key].score
        ):
            unique[key] = match

    return sorted(
        unique.values(),
        key=lambda x: x.score,
        reverse=True
    )


def calculate_report(
    document_text: str,
    matches: List[Match]
):

    document_words = re.findall(
        r"\b[a-zA-Z][a-zA-Z'-]*\b",
        document_text.lower()
    )

    passages = segment_passages(
        document_text
    )

    if not passages:

        return {
            "words": len(document_words),
            "passages": 0,
            "similarity": 0,
            "originality": 100,
            "matches": []
        }

    matched_passages = {
        match.passage_id
        for match in matches
        if match.score >= 20
    }

    similarity = (
        len(matched_passages)
        / len(passages)
    ) * 100

    similarity = min(
        100,
        round(similarity, 1)
    )

    originality = round(
        100 - similarity,
        1
    )

    return {
        "words": len(document_words),
        "passages": len(passages),
        "similarity": similarity,
        "originality": originality,
        "matches": [
            {
                "passage_id": match.passage_id,
                "source_title": match.source_title,
                "source_url": match.source_url,
                "source_type": match.source_type,
                "passage": match.passage,
                "source_text": match.source_text,
                "score": match.score,
                "confidence": match.confidence,
                "signals": {
                    "exact": match.exact,
                    "fingerprint": match.fingerprint,
                    "lexical": match.lexical,
                    "semantic": match.semantic
                }
            }
            for match in matches
        ]
}
# ==========================================================
# OPENALEX ACADEMIC SEARCH
# ==========================================================

OPENALEX_API = "https://api.openalex.org/works"


def build_academic_queries(text: str, max_queries: int = 5):
    """
    Creates focused academic search queries from a document.
    """

    passages = segment_passages(
        text,
        min_words=30,
        max_words=80
    )

    queries = []

    for passage in passages[:max_queries]:

        cleaned = normalize(passage)

        # Remove very common words
        stopwords = {
            "the", "and", "that", "this", "with",
            "from", "have", "which", "their",
            "there", "about", "into", "than",
            "were", "been", "also", "they",
            "these", "those", "using", "such"
        }

        tokens = [
            word
            for word in cleaned.split()
            if word not in stopwords
            and len(word) > 3
        ]

        query = " ".join(tokens[:14])

        if query and query not in queries:
            queries.append(query)

    return queries


def search_openalex(
    query: str,
    per_page: int = 5
):
    """
    Search OpenAlex for scholarly works.

    Returns lightweight Source objects that can
    be passed into the Stage 2A comparison engine.
    """

    if not query.strip():
        return []

    params = {
        "search": query,
        "per-page": min(per_page, 10),
    }

    url = (
        OPENALEX_API
        + "?"
        + urllib.parse.urlencode(params)
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent":
                "OriginalityChecker/2.0 "
                "(academic similarity research)"
        }
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=12
        ) as response:

            payload = json.loads(
                response.read().decode(
                    "utf-8"
                )
            )

    except Exception:
        return []

    sources = []

    for work in payload.get(
        "results",
        []
    ):

        title = (
            work.get("display_name")
            or work.get("title")
            or "Untitled academic work"
        )

        work_url = (
            work.get("doi")
            or work.get("primary_location", {})
                .get("landing_page_url")
            or work.get("id")
            or ""
        )

        abstract = ""

        inverted_index = (
            work.get("abstract_inverted_index")
        )

        if inverted_index:

            words_by_position = []

            for word, positions in inverted_index.items():

                for position in positions:
                    words_by_position.append(
                        (position, word)
                    )

            words_by_position.sort(
                key=lambda x: x[0]
            )

            abstract = " ".join(
                word
                for _, word
                in words_by_position
            )

        if not abstract:
            abstract = title

        sources.append(
            Source(
                title=title,
                url=work_url,
                text=abstract,
                source_type="academic"
            )
        )

    return sources


def search_academic_sources(
    document_text: str,
    max_queries: int = 5,
    results_per_query: int = 5
):
    """
    Runs multiple OpenAlex searches and removes
    duplicate academic works.
    """

    queries = build_academic_queries(
        document_text,
        max_queries=max_queries
    )

    all_sources = []

    seen = set()

    for query in queries:

        results = search_openalex(
            query,
            per_page=results_per_query
        )

        for source in results:

            key = (
                source.url
                or source.title.lower()
            )

            if key in seen:
                continue

            seen.add(key)
            all_sources.append(source)

    return all_sourcesa
