from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .rag_pipeline import (
    answer_question,
    chunk_text,
    clear_company_documents,
    create_company,
    delete_company,
    delete_document,
    extract_pdf_text,
    get_company_knowledge,
    list_companies,
    load_env,
    save_document,
    text_to_speech,
)


load_env()

app = FastAPI(title="AI Knowledge Hub API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CompanyRequest(BaseModel):
    name: str


class AskRequest(BaseModel):
    question: str


class TtsRequest(BaseModel):
    text: str


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "AI Knowledge Hub Python API"}


@app.get("/api/companies")
def companies():
    return {"companies": list_companies()}


@app.post("/api/companies", status_code=201)
def add_company(payload: CompanyRequest):
    try:
        return {"company": create_company(payload.name)}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.get("/api/companies/{company_id}")
def company_details(company_id: str):
    try:
        knowledge = get_company_knowledge(company_id)
        return {
            "company": knowledge["company"],
            "documents": knowledge["documents"],
            "chunkCount": len(knowledge["chunks"]),
        }
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))


@app.post("/api/companies/{company_id}/documents", status_code=201)
async def upload_document(company_id: str, document: UploadFile = File(...)):
    try:
        file_bytes = await document.read()
        text = extract_pdf_text(file_bytes)
        chunks = chunk_text(text)

        if not chunks:
            raise HTTPException(status_code=400, detail="No readable text was found in this PDF.")

        result = save_document(company_id, document.filename or "document.pdf", text, chunks)
        uploaded = result["document"]

        return {
            "document": uploaded,
            "message": f"Uploaded {uploaded['fileName']} with {uploaded['chunkCount']} chunks.",
        }
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))


@app.delete("/api/companies/{company_id}/documents/{document_id}")
def remove_document(company_id: str, document_id: str):
    try:
        document = delete_document(company_id, document_id)
        return {"message": f"{document['fileName']} was deleted.", "document": document}
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))


@app.delete("/api/companies/{company_id}/documents")
def clear_documents(company_id: str):
    try:
        result = clear_company_documents(company_id)
        return {
            "message": (
                f"Cleared {result['removedCount']} document(s) from "
                f"{result['company']['name']}."
            )
        }
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))


@app.delete("/api/companies/{company_id}")
def remove_company(company_id: str):
    try:
        company = delete_company(company_id)
        return {"message": f"{company['name']} was deleted.", "company": company}
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))


@app.post("/api/companies/{company_id}/ask")
async def ask(company_id: str, payload: AskRequest):
    question = payload.question.strip()

    if not question:
        raise HTTPException(status_code=400, detail="Question is required.")

    try:
        knowledge = get_company_knowledge(company_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))

    if not knowledge["chunks"]:
        raise HTTPException(status_code=400, detail="Upload at least one document first.")

    try:
        return await answer_question(
            company=knowledge["company"],
            documents=knowledge["documents"],
            chunks=knowledge["chunks"],
            question=question,
        )
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error))


@app.post("/api/tts")
async def tts(payload: TtsRequest):
    text = payload.text.strip()

    if not text:
        raise HTTPException(status_code=400, detail="Text is required.")

    try:
        return await text_to_speech(text)
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error))
