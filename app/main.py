import io
import re
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from pypdf import PdfReader
from docx import Document

from app.plagiarism_engine import (
    Source,
    compare_local_documents,
    calculate_report,
    search_academic_sources,
)


app = FastAPI(title="OriginalityChecker")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


BASE = Path(__file__).resolve().parent.parent
STATIC = BASE / "static"


# --------------------------------------------------
# DEMO SOURCES
# --------------------------------------------------
# These are temporary local sources used to verify
# the new engine. Real academic/web retrieval comes
# in the next layer.
# --------------------------------------------------

SOURCES = [
    Source(
        title="Example Academic Writing Source",
        url="https://example.org/academic-writing",
        source_type="academic",
        text=(
            "Academic writing presents evidence, explains ideas clearly, "
            "uses appropriate citations, and develops an argument in a "
            "logical structure."
        ),
    ),

    Source(
        title="Example Research Methods Source",
        url="https://example.org/research-methods",
        source_type="academic",
        text=(
            "Research methods provide systematic procedures for collecting, "
            "analyzing, and interpreting information to answer a research question."
        ),
    ),
]


# --------------------------------------------------
# PAGES
# --------------------------------------------------

@app.get("/")
def home():
    return FileResponse(STATIC / "dashboard.html")


@app.get("/dashboard")
def dashboard():
    return FileResponse(STATIC / "dashboard.html")


@app.get("/checker")
def checker():
    return FileResponse(STATIC / "checker.html")


@app.get("/documents")
def documents():
    return FileResponse(STATIC / "documents.html")


@app.get("/reports")
def reports():
    return FileResponse(STATIC / "reports.html")


@app.get("/citations")
def citations():
    return FileResponse(STATIC / "citations.html")


@app.get("/ai-analysis")
def ai_analysis():
    return FileResponse(STATIC / "ai-analysis.html")


@app.get("/settings")
def settings():
    return FileResponse(STATIC / "settings.html")


# --------------------------------------------------
# HEALTH
# --------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "engine": "stage-2a",
    }


# --------------------------------------------------
# DOCUMENT EXTRACTION
# --------------------------------------------------

def extract_text(filename: str, data: bytes) -> str:

    ext = Path(filename).suffix.lower()

    if ext == ".txt":
        return data.decode(
            "utf-8",
            errors="ignore"
        )

    if ext == ".pdf":

        reader = PdfReader(
            io.BytesIO(data)
        )

        pages = []

        for page in reader.pages:
            pages.append(
                page.extract_text() or ""
            )

        return "\n".join(pages)

    if ext == ".docx":

        doc = Document(
            io.BytesIO(data)
        )

        return "\n".join(
            paragraph.text
            for paragraph in doc.paragraphs
        )

    raise HTTPException(
        status_code=400,
        detail=(
            "Only PDF, DOCX and TXT files "
            "are supported."
        )
    )


# --------------------------------------------------
# CITATION ANALYSIS
# --------------------------------------------------

def count_citations(text: str) -> int:

    parenthetical = re.findall(
        r"\([^)]*(?:19|20)\d{2}[^)]*\)",
        text
    )

    author_year = re.findall(
        r"\b[A-Z][A-Za-z'-]+(?:\s+et al\.)?,?\s*\((?:19|20)\d{2}\)",
        text
    )

    return len(
        set(parenthetical + author_year)
    )


# --------------------------------------------------
# MAIN CHECK ENDPOINT
# --------------------------------------------------

@app.post("/api/check")
async def check_document(
    file: UploadFile = File(...)
):

    filename = (
        file.filename
        or "document.txt"
    )

    data = await file.read()

    # 20 MB upload limit
    if len(data) > 20 * 1024 * 1024:

        raise HTTPException(
            status_code=413,
            detail="Maximum file size is 20 MB."
        )

    # Extract
    text = extract_text(
        filename,
        data
    )

    if not text.strip():

        raise HTTPException(
            status_code=400,
            detail="No readable text was found."
        )

    # --------------------------------------------------
    # STAGE 2A ENGINE
    # --------------------------------------------------

    # --------------------------------------------------
# ACADEMIC SOURCE RETRIEVAL
# --------------------------------------------------

academic_sources = search_academic_sources(
    document_text=text,
    max_queries=5,
    results_per_query=5,
)

# Combine temporary local sources with
# retrieved academic sources.
all_sources = SOURCES + academic_sources

matches = compare_local_documents(
    document_text=text,
    sources=all_sources,
    threshold=15,
)
    report = calculate_report(
        document_text=text,
        matches=matches,
    )

    # --------------------------------------------------
    # CITATIONS
    # --------------------------------------------------

    citation_count = count_citations(
        text
    )

    if citation_count >= 2:
        citation_health = "Good"
    elif citation_count == 1:
        citation_health = "Needs review"
    else:
        citation_health = "Needs citations"

    # --------------------------------------------------
    # BASIC AI-WRITING SIGNALS
    # --------------------------------------------------

    words = re.findall(
        r"\b[a-zA-Z][a-zA-Z'-]*\b",
        text.lower()
    )

    indicators = []

    if len(words) > 120:

        unique_ratio = (
            len(set(words))
            / len(words)
        )

        if unique_ratio < 0.38:
            indicators.append(
                "Relatively repetitive vocabulary"
            )

    transitions = [
        "moreover",
        "furthermore",
        "in conclusion",
        "therefore",
        "however",
        "additionally",
    ]

    transition_count = sum(
        text.lower().count(item)
        for item in transitions
    )

    if transition_count >= 5:

        indicators.append(
            "Frequent formulaic transitions"
        )

    ai_score = min(
        95,
        35 + len(indicators) * 15
    )

    # --------------------------------------------------
    # FINAL RESPONSE
    # --------------------------------------------------

    return {
        "engine": {
            "version": "2A",
            "name": "OriginalityChecker Hybrid Engine",
            "status": "active",
        },

        "document": {
            "filename": filename,
            "words": report["words"],
            "characters": len(text),
            "passages": report["passages"],
        },

        "originality": report["originality"],

        "similarity": report["similarity"],

        "highest_similarity": (
            max(
                [
                    match["score"]
                    for match in report["matches"]
                ],
                default=0
            )
        ),

        "sources_found": len(
            report["matches"]
        ),

        "matches": report["matches"],

        "citation_count": citation_count,

        "citation_health": citation_health,

        "ai_writing": {
            "indicator_score": ai_score,
            "indicators": indicators,
            "disclaimer": (
                "AI-writing indicators are "
                "probabilistic signals and are "
                "not proof of AI authorship."
            ),
        },

        "search_status": {
    "local_engine": "complete",
    "private_documents": "next",
    "academic_search": "complete",
    "web_search": "next",
    "semantic_embeddings": "next",
},

"academic_search": {
    "provider": "OpenAlex",
    "sources_retrieved": len(academic_sources),
    "queries_generated": 5,
},
}
