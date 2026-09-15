import io
import re
from pathlib import Path
from difflib import SequenceMatcher

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader
from docx import Document

app = FastAPI(title="OriginalityChecker")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE = Path(__file__).resolve().parent.parent
STATIC = BASE / "static"

SOURCES = [
    {
        "title": "Example Academic Writing Source",
        "url": "https://example.org/academic-writing",
        "text": "Academic writing presents evidence, explains ideas clearly, uses appropriate citations, and develops an argument in a logical structure."
    },
    {
        "title": "Example Research Methods Source",
        "url": "https://example.org/research-methods",
        "text": "Research methods provide systematic procedures for collecting, analyzing, and interpreting information to answer a research question."
    }
]

@app.get("/")
def home():
    return FileResponse(STATIC / "dashboard.html")

@app.get("/health")
def health():
    return {"status": "ok"}

def extract_text(filename, data):
    ext = Path(filename).suffix.lower()

    if ext == ".txt":
        return data.decode("utf-8", errors="ignore")

    if ext == ".pdf":
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    if ext == ".docx":
        doc = Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs)

    raise HTTPException(
        status_code=400,
        detail="Only PDF, DOCX and TXT files are supported."
    )

@app.post("/api/check")
async def check_document(file: UploadFile = File(...)):
    data = await file.read()

    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(413, "Maximum file size is 20 MB.")

    text = extract_text(file.filename or "document.txt", data)

    if not text.strip():
        raise HTTPException(400, "No readable text was found.")

    words = re.findall(r"\b[a-zA-Z][a-zA-Z'-]*\b", text.lower())

    matches = []

    for source in SOURCES:
        score = SequenceMatcher(
            None,
            text.lower(),
            source["text"].lower()
        ).ratio() * 100

        if score >= 12:
            matches.append({
                "title": source["title"],
                "url": source["url"],
                "similarity": round(score, 1)
            })

    matches.sort(
        key=lambda x: x["similarity"],
        reverse=True
    )

    highest = matches[0]["similarity"] if matches else 0

    citations = len(
        re.findall(
            r"\([^)]*(?:19|20)\d{2}[^)]*\)",
            text
        )
    )

    sentences = re.split(r"(?<=[.!?])\s+", text)
    sentence_lengths = [
        len(s.split())
        for s in sentences
        if s.strip()
    ]

    indicators = []

    if len(words) > 120:
        unique_ratio = len(set(words)) / len(words)

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
        "additionally"
    ]

    transition_count = sum(
        text.lower().count(x)
        for x in transitions
    )

    if transition_count >= 5:
        indicators.append(
            "Frequent formulaic transitions"
        )

    ai_score = min(
        95,
        35 + len(indicators) * 15
    )

    return {
        "document": {
            "words": len(words),
            "characters": len(text)
        },
        "originality": round(
            max(0, 100 - highest),
            1
        ),
        "highest_similarity": highest,
        "sources_found": len(matches),
        "matches": matches,
        "citation_count": citations,
        "citation_health": (
            "Good" if citations >= 2
            else "Needs review"
        ),
        "ai_writing": {
            "indicator_score": ai_score,
            "indicators": indicators,
            "disclaimer": (
                "AI-writing indicators are probabilistic "
                "signals and are not proof of AI authorship."
            )
        }
  }
