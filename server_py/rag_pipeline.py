import json
import os
import re
import uuid
from pathlib import Path
from typing import Any

import httpx
from pypdf import PdfReader


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = Path("/tmp/ai-knowledge-hub-data") if os.getenv("VERCEL") else ROOT_DIR / "server" / "data"
DATA_DIR = Path(os.getenv("KNOWLEDGE_STORE_DIR", DEFAULT_DATA_DIR))
DATA_FILE = DATA_DIR / "knowledge-base.json"
SARVAM_BASE_URL = "https://api.sarvam.ai"

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "with",
}


def load_env() -> None:
    """Load local env files without requiring python-dotenv."""
    for env_path in [ROOT_DIR / "server_py" / ".env", ROOT_DIR / "server" / ".env"]:
        if not env_path.exists():
            continue

        for line in env_path.read_text(encoding="utf-8").splitlines():
            clean_line = line.strip()

            if not clean_line or clean_line.startswith("#") or "=" not in clean_line:
                continue

            key, value = clean_line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def extract_pdf_text(file_bytes: bytes) -> str:
    temp_path = DATA_DIR / f"upload-{uuid.uuid4()}.pdf"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temp_path.write_bytes(file_bytes)

    try:
        reader = PdfReader(str(temp_path))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages).strip()
    finally:
        temp_path.unlink(missing_ok=True)


def chunk_text(text: str, size: int = 300, overlap: int = 50) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()

    if not normalized:
        return []

    words = normalized.split(" ")
    chunks = []
    start = 0

    while start < len(words):
        end = min(start + size, len(words))
        chunks.append(" ".join(words[start:end]))

        if end == len(words):
            break

        start = max(0, end - overlap)

    return chunks


def read_store() -> dict[str, list[dict[str, Any]]]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not DATA_FILE.exists():
        DATA_FILE.write_text(
            json.dumps({"companies": [], "documents": [], "chunks": []}, indent=2),
            encoding="utf-8",
        )

    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def write_store(store: dict[str, list[dict[str, Any]]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(store, indent=2), encoding="utf-8")


def list_companies() -> list[dict[str, Any]]:
    store = read_store()
    companies = []

    for company in store["companies"]:
        companies.append(
            {
                **company,
                "documentCount": len(
                    [doc for doc in store["documents"] if doc["companyId"] == company["id"]]
                ),
                "chunkCount": len(
                    [chunk for chunk in store["chunks"] if chunk["companyId"] == company["id"]]
                ),
            }
        )

    return companies


def create_company(name: str) -> dict[str, Any]:
    clean_name = name.strip()

    if not clean_name:
        raise ValueError("Company name is required.")

    store = read_store()
    existing = next(
        (
            company
            for company in store["companies"]
            if company["name"].lower() == clean_name.lower()
        ),
        None,
    )

    if existing:
        return existing

    company = {
        "id": str(uuid.uuid4()),
        "name": clean_name,
        "createdAt": now_iso(),
    }
    store["companies"].append(company)
    write_store(store)
    return company


def get_company_knowledge(company_id: str) -> dict[str, Any]:
    store = read_store()
    company = next((item for item in store["companies"] if item["id"] == company_id), None)

    if not company:
        raise ValueError("Company not found.")

    return {
        "company": company,
        "documents": [doc for doc in store["documents"] if doc["companyId"] == company_id],
        "chunks": [chunk for chunk in store["chunks"] if chunk["companyId"] == company_id],
    }


def save_document(company_id: str, file_name: str, text: str, chunks: list[str]) -> dict[str, Any]:
    store = read_store()
    company = next((item for item in store["companies"] if item["id"] == company_id), None)

    if not company:
        raise ValueError("Company not found.")

    document = {
        "id": str(uuid.uuid4()),
        "companyId": company_id,
        "fileName": file_name,
        "characterCount": len(text),
        "chunkCount": len(chunks),
        "uploadedAt": now_iso(),
    }
    stored_chunks = [
        {
            "id": str(uuid.uuid4()),
            "companyId": company_id,
            "documentId": document["id"],
            "documentName": file_name,
            "index": index,
            "content": content,
        }
        for index, content in enumerate(chunks)
    ]

    store["documents"].append(document)
    store["chunks"].extend(stored_chunks)
    write_store(store)
    return {"document": document, "chunks": stored_chunks}


def delete_document(company_id: str, document_id: str) -> dict[str, Any]:
    store = read_store()
    document = next(
        (
            doc
            for doc in store["documents"]
            if doc["id"] == document_id and doc["companyId"] == company_id
        ),
        None,
    )

    if not document:
        raise ValueError("Document not found.")

    store["documents"] = [doc for doc in store["documents"] if doc["id"] != document_id]
    store["chunks"] = [chunk for chunk in store["chunks"] if chunk["documentId"] != document_id]
    write_store(store)
    return document


def clear_company_documents(company_id: str) -> dict[str, Any]:
    store = read_store()
    company = next((item for item in store["companies"] if item["id"] == company_id), None)

    if not company:
        raise ValueError("Company not found.")

    removed_count = len([doc for doc in store["documents"] if doc["companyId"] == company_id])
    store["documents"] = [doc for doc in store["documents"] if doc["companyId"] != company_id]
    store["chunks"] = [chunk for chunk in store["chunks"] if chunk["companyId"] != company_id]
    write_store(store)
    return {"company": company, "removedCount": removed_count}


def delete_company(company_id: str) -> dict[str, Any]:
    store = read_store()
    company = next((item for item in store["companies"] if item["id"] == company_id), None)

    if not company:
        raise ValueError("Company not found.")

    store["companies"] = [item for item in store["companies"] if item["id"] != company_id]
    store["documents"] = [doc for doc in store["documents"] if doc["companyId"] != company_id]
    store["chunks"] = [chunk for chunk in store["chunks"] if chunk["companyId"] != company_id]
    write_store(store)
    return company


async def answer_question(
    company: dict[str, Any],
    documents: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    question: str,
) -> dict[str, Any]:
    if is_person_name_question(question):
        return build_person_name_answer(documents, chunks)

    if is_all_documents_question(question):
        relevant_chunks = representative_chunks_by_document(chunks, per_document=1)
        return {
            "answer": build_all_documents_overview(documents, chunks),
            "sources": to_sources(relevant_chunks),
        }

    matches = retrieve_relevant_chunks(question, chunks)

    if not matches:
        team = route_question_to_team(question)
        return {
            "answer": (
                "I could not find a confident answer in the uploaded company knowledge base.\n\n"
                f"Suggested route: {team}.\n\n"
                "Please upload a relevant document or ask the responsible team to confirm this information."
            ),
            "sources": [],
        }

    answer = await generate_sarvam_answer(company["name"], question, matches)
    return {"answer": answer, "sources": to_sources(matches)}


def retrieve_relevant_chunks(
    question: str, chunks: list[dict[str, Any]], limit: int = 5
) -> list[dict[str, Any]]:
    question_terms = tokenize(expand_question(question))

    if not question_terms:
        return [{**chunk, "score": 0} for chunk in chunks[:limit]]

    scored_chunks = []
    for chunk in chunks:
        content = chunk["content"].lower()
        score = sum(content.count(term) for term in question_terms)
        scored_chunks.append({**chunk, "score": score})

    return sorted(
        [chunk for chunk in scored_chunks if chunk["score"] > 0],
        key=lambda chunk: chunk["score"],
        reverse=True,
    )[:limit]


async def generate_sarvam_answer(
    company_name: str, question: str, context_chunks: list[dict[str, Any]]
) -> str:
    guarded_answer = answer_known_document_mismatch(question, context_chunks)

    if guarded_answer:
        return guarded_answer

    context = "\n\n".join(
        [
            f"Source {index + 1}: {chunk['documentName']}, chunk {chunk['index'] + 1}\n{chunk['content']}"
            for index, chunk in enumerate(context_chunks)
        ]
    )
    body = {
        "model": os.getenv("SARVAM_CHAT_MODEL", "sarvam-30b"),
        "temperature": 0.2,
        "reasoning_effort": "low",
        "max_tokens": 2000,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an enterprise knowledge assistant. Answer only from the provided company document context. "
                    "If the answer is not present, say that the knowledge base does not contain enough information. "
                    "Keep answers clear, practical, and interview-demo friendly. Return plain text only. "
                    "Do not use markdown, asterisks, brackets, tables, or bold formatting."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Company: {company_name}\n\nDocument context:\n{context}\n\nQuestion: {question}\n\n"
                    "If the question asks about all uploaded documents, combine chunks by PDF file name. "
                    "Do not mention internal chunk numbers unless the user asks for retrieval details."
                ),
            },
        ],
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{SARVAM_BASE_URL}/v1/chat/completions",
            headers=auth_headers(),
            json=body,
        )

    data = response.json()

    if response.status_code >= 400:
        message = data.get("error", {}).get("message", "Sarvam chat request failed.")
        raise RuntimeError(message)

    content = extract_message_content(data.get("choices", [{}])[0].get("message", {}))

    if content:
        return clean_answer_for_display(content)

    return clean_answer_for_display(build_extractive_fallback(question, context_chunks))


async def text_to_speech(text: str) -> dict[str, str]:
    body = {
        "text": clean_text_for_speech(text)[:1800],
        "target_language_code": "en-IN",
        "model": "bulbul:v3",
        "speaker": "shubh",
        "output_audio_codec": "wav",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{SARVAM_BASE_URL}/text-to-speech",
            headers=auth_headers(),
            json=body,
        )

    data = response.json()

    if response.status_code >= 400:
        message = data.get("error", {}).get("message", "Sarvam TTS request failed.")
        raise RuntimeError(message)

    audio = data.get("audios", [None])[0]

    if not audio:
        raise RuntimeError("Sarvam TTS did not return audio.")

    return {"audioBase64": audio, "mimeType": "audio/wav"}


def representative_chunks_by_document(
    chunks: list[dict[str, Any]], per_document: int = 2
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}

    for chunk in chunks:
        grouped.setdefault(chunk["documentId"], []).append(chunk)

    selected = []
    for group in grouped.values():
        selected.extend([{**chunk, "score": 0} for chunk in group[:per_document]])

    return selected


def build_person_name_answer(
    documents: list[dict[str, Any]], chunks: list[dict[str, Any]]
) -> dict[str, Any]:
    found = []

    for document in documents:
        document_chunks = sorted(
            [chunk for chunk in chunks if chunk["documentId"] == document["id"]],
            key=lambda chunk: chunk["index"],
        )
        text = " ".join(chunk["content"] for chunk in document_chunks)

        if not looks_like_resume(text.lower()):
            continue

        name = extract_likely_name(text, document["fileName"])

        if name:
            found.append({"document": document, "chunk": document_chunks[0], "name": name})

    if not found:
        return {
            "answer": (
                "I could not find a clear person's name in the uploaded documents. "
                "Please ask about a specific PDF or upload a document with a visible name section."
            ),
            "sources": [],
        }

    if len(found) == 1:
        answer = f"The person's name appears to be {found[0]['name']}."
    else:
        lines = [f"{item['document']['fileName']}: {item['name']}" for item in found]
        answer = "I found these person names across the uploaded documents:\n\n" + "\n".join(lines)

    return {
        "answer": answer,
        "sources": [
            {
                "documentName": item["document"]["fileName"],
                "chunk": item["chunk"]["index"] + 1,
                "score": 0,
            }
            for item in found
        ],
    }


def build_all_documents_overview(
    documents: list[dict[str, Any]], chunks: list[dict[str, Any]]
) -> str:
    sections = []

    for document in documents:
        document_chunks = sorted(
            [chunk for chunk in chunks if chunk["documentId"] == document["id"]],
            key=lambda chunk: chunk["index"],
        )
        text = " ".join(chunk["content"] for chunk in document_chunks)
        sections.append(f"{document['fileName']}: {summarize_document(document['fileName'], text)}")

    return (
        "\n\n".join(sections)
        + f"\n\nOverall: These uploads contain {len(documents)} document(s). "
        "The knowledge hub can answer questions across them, show the source PDF used, "
        "and convert the final response into speech."
    )


def summarize_document(file_name: str, text: str) -> str:
    lower = text.lower()
    name = extract_likely_name(text, file_name)

    if looks_like_resume(lower):
        owner = f" for {name}" if name else ""
        projects = extract_project_names(text)
        project_text = f" It mentions projects such as {', '.join(projects)}." if projects else ""
        return (
            f"This appears to be a resume{owner}. It covers education, technical skills, "
            f"experience, and project work.{project_text}"
        )

    if "whatsapp" in lower and ("wati" in lower or "sales assistant" in lower):
        return (
            "This is a project brief for a WhatsApp AI sales assistant. It describes a "
            "website-to-WhatsApp flow, WATI integration, AI-based product and pricing replies, "
            "lead outreach, and human handoff for complex customer cases."
        )

    if "project objective" in lower or "main features" in lower:
        return (
            "This appears to be a project requirement document. It explains the objective, "
            "expected user flow, main features, and implementation responsibilities."
        )

    return f"{clean_preview(text)}."


def route_question_to_team(question: str) -> str:
    lower = question.lower()

    if any(word in lower for word in ["leave", "salary", "employee"]):
        return "HR team"

    if any(word in lower for word in ["vpn", "laptop", "password"]):
        return "IT support team"

    if any(word in lower for word in ["invoice", "payment", "reimbursement"]):
        return "Finance team"

    if any(word in lower for word in ["customer", "lead", "sales"]):
        return "Sales or customer operations team"

    return "Knowledge base admin"


def answer_known_document_mismatch(question: str, context_chunks: list[dict[str, Any]]) -> str:
    normalized_question = question.lower()
    combined = " ".join(chunk["content"] for chunk in context_chunks)
    normalized_context = combined.lower()
    asks_build_intent = "ask" in normalized_question and (
        "build" in normalized_question or "project" in normalized_question
    )
    looks_like_resume_context = any(
        word in normalized_context
        for word in ["resume", "linkedin", "github", "education", "skills", "experience"]
    )

    if not asks_build_intent or not looks_like_resume_context:
        return ""

    name = extract_likely_name(combined)
    name_text = f" It appears to be the resume of {name}." if name else ""
    return clean_answer_for_display(
        "This uploaded document appears to be a resume, not a project brief or task document."
        f"{name_text}\n\n"
        "So it does not directly ask us to build anything. It describes the person's profile, "
        "skills, experience, and projects. If you want a project requirement answer, upload the "
        "actual project PDF or assignment document."
    )


def build_extractive_fallback(question: str, context_chunks: list[dict[str, Any]]) -> str:
    lower = question.lower()
    combined = " ".join(chunk["content"] for chunk in context_chunks)

    if any(word in lower for word in ["name", "person", "candidate"]):
        name = extract_likely_name(combined)

        if name:
            return f"Based on the retrieved document context, the person's name appears to be {name}."

    preview = context_chunks[0]["content"][:500] if context_chunks else ""
    return (
        "Sarvam returned an empty final response, so here is the most relevant extracted "
        f"context from the knowledge base:\n\n{preview}"
    )


def extract_likely_name(text: str, file_name: str = "") -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    leading_name = re.match(
        r"^([A-Z][A-Z.]+(?:\s+[A-Z][A-Z.]+){1,4})(?=\s+(Hyderabad|India|AI Engineer|Email|E-mail|Linkedin|GitHub|CAREER|PROFESSIONAL|P R O|B\.Tech))",
        compact,
        re.IGNORECASE,
    )

    if leading_name:
        return title_case_name(leading_name.group(1))

    lines = [line.strip() for line in re.split(r"\n| {2,}", text) if line.strip()]
    candidate = next((line for line in lines if re.match(r"^[A-Z][A-Z\s.]{4,45}$", line)), "")

    if candidate:
        return title_case_name(candidate)

    file_name_hint = re.sub(r"\.[^.]+$", "", file_name)
    file_name_hint = re.sub(r"resume|cv|[0-9]", "", file_name_hint, flags=re.IGNORECASE)
    file_name_hint = re.sub(r"[_-]+", " ", file_name_hint).strip()
    return title_case_name(file_name_hint) if file_name_hint else ""


def looks_like_resume(lower_text: str) -> bool:
    return any(
        marker in lower_text
        for marker in [
            "resume",
            "career objective",
            "professional summary",
            "education",
            "technical skills",
        ]
    )


def extract_project_names(text: str) -> list[str]:
    names = [
        "Restaurant Ordering System",
        "Business AI Chatbot",
        "AI Calling Agent",
        "Newton's Cooling Simulator",
        "WhatsApp AI sales assistant",
    ]
    lower = text.lower()
    return [name for name in names if name.lower() in lower][:3]


def extract_message_content(message: dict[str, Any]) -> str:
    content = message.get("content")

    if not content:
        return ""

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts = []

        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                parts.append(part.get("text") or part.get("content") or "")

        return " ".join(parts).strip()

    return ""


def clean_answer_for_display(text: str) -> str:
    cleaned = text
    cleaned = re.sub(r"```[\s\S]*?```", "Code block omitted.", cleaned)
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"\*([^*]+)\*", r"\1", cleaned)
    cleaned = re.sub(r"__([^_]+)__", r"\1", cleaned)
    cleaned = re.sub(r"_([^_]+)_", r"\1", cleaned)
    cleaned = re.sub(r"^#{1,6}\s+", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^\s*[-*+]\s+", "- ", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
    cleaned = re.sub(r"^Source\s+\d+:\s*", "", cleaned, flags=re.IGNORECASE | re.MULTILINE)
    cleaned = re.sub(r",\s*chunk\s+\d+", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"[()[\]{}<>|*_#~]", "", cleaned)
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def clean_text_for_speech(text: str) -> str:
    cleaned = clean_answer_for_display(text)
    cleaned = re.sub(r"```[\s\S]*?```", " code block omitted. ", cleaned)
    cleaned = re.sub(r"^\s*-\s+", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^\s*\d+\.\s+", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def auth_headers() -> dict[str, str]:
    api_key = os.getenv("SARVAM_API_KEY")

    if not api_key:
        raise RuntimeError("SARVAM_API_KEY is missing. Add it locally in server_py/.env or in Vercel Environment Variables.")

    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "api-subscription-key": api_key,
    }


def tokenize(value: str) -> list[str]:
    words = re.sub(r"[^a-z0-9\s]", " ", value.lower()).split()
    return [word for word in words if len(word) > 2 and word not in STOP_WORDS]


def expand_question(question: str) -> str:
    lower = question.lower()
    additions = []

    if "name" in lower or "person" in lower or "candidate" in lower:
        additions.append("resume profile contact candidate education experience")

    if "project" in lower or "ask" in lower or "build" in lower:
        additions.append("project requirement build solution task objective")

    if "skill" in lower or "tech" in lower:
        additions.append("skills technologies tools programming")

    if "email" in lower or "phone" in lower or "contact" in lower:
        additions.append("email phone contact mobile linkedin github")

    return f"{question} {' '.join(additions)}"


def is_all_documents_question(question: str) -> bool:
    lower = question.lower()
    return any(
        phrase in lower
        for phrase in [
            "all documents",
            "uploaded documents",
            "these documents",
            "documents about",
            "documents summary",
            "summarize documents",
            "summarise documents",
            "what is this documents",
        ]
    )


def is_person_name_question(question: str) -> bool:
    lower = question.lower()
    return (
        ("name" in lower and "person" in lower)
        or "candidate name" in lower
        or "person name" in lower
        or lower == "name"
    )


def clean_preview(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text)
    cleaned = re.sub(r"[()[\]{}<>|*_#~]", "", cleaned)
    return cleaned[:260].strip()


def title_case_name(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower().title()).strip()


def to_sources(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "documentName": chunk["documentName"],
            "chunk": chunk["index"] + 1,
            "score": chunk.get("score", 0),
        }
        for chunk in chunks
    ]


def now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
