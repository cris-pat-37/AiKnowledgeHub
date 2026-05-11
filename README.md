# AI Research & Knowledge Hub for Enterprises

A multi-company knowledge assistant for enterprise documents. Upload PDFs for any company, ask questions about those documents, get grounded AI answers, and listen to the generated response using Sarvam AI Text-to-Speech.

## What This Project Does

- Creates separate knowledge hubs for multiple companies.
- Uploads and reads PDF documents.
- Splits document text into searchable chunks.
- Retrieves the most relevant chunks for a user question.
- Uses Sarvam Chat Completions to generate an answer from only the retrieved context.
- Uses Sarvam Text-to-Speech so users can listen to the answer.

## Tech Stack

- Frontend: React + Vite
- Backend: Python + FastAPI
- File upload: FastAPI UploadFile
- PDF parsing: pypdf
- AI: Sarvam Chat Completions
- TTS: Sarvam Text-to-Speech
- Demo storage: JSON file storage

For a production version, the JSON storage layer can be replaced with MongoDB without changing the main app flow.

## Setup

Install dependencies:

```bash
npm install
npm run install:all
```

Create `server_py/.env`:

```env
PORT=5000
SARVAM_API_KEY=your_sarvam_key_here
SARVAM_CHAT_MODEL=sarvam-30b
```

Run both frontend and backend:

```bash
npm run dev
```

Open:

```text
http://localhost:5173
```

## Vercel Deployment

This repo deploys as a Vercel app with:

- React/Vite frontend from `client/dist`
- Python FastAPI backend from `api/index.py`
- RAG code from `server_py/rag_pipeline.py`

Add these Environment Variables in Vercel before deploying:

```env
SARVAM_API_KEY=your_sarvam_key_here
SARVAM_CHAT_MODEL=sarvam-30b
```

You do not need `VITE_API_BASE_URL` on Vercel. The frontend calls the same deployed app through `/api`.

For the interview demo, Vercel stores uploaded PDFs/chunks in temporary serverless storage. For a real production app, replace the JSON store with MongoDB, Postgres, Supabase, or another persistent database.

## Interview Explanation

This project uses RAG, which means Retrieval-Augmented Generation. The app does not send a question directly to the AI model. First, the Python backend searches the uploaded company documents and finds the most relevant text chunks. Then it sends only those chunks plus the question to Sarvam AI. This makes answers more grounded and reduces hallucination.

After the answer is generated, the Listen button sends the answer text to Sarvam TTS and plays the returned audio in the browser.

## Example Questions

- What does the uploaded project ask us to build?
- Summarize this company's leave policy.
- What are the main responsibilities in this resume?
- Which team should handle VPN issues?
- What are the key requirements from this document?
