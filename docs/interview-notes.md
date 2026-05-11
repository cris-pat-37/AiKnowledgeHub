# Interview Notes

## One-Minute Project Pitch

I built a multi-company AI knowledge hub for enterprise documents. A company can upload PDFs like project briefs, policies, resumes, onboarding docs, or internal reports. The app extracts text, splits it into chunks, retrieves the most relevant chunks for a question, and then asks Sarvam AI to generate a grounded answer. The answer also has a Listen button powered by Sarvam Text-to-Speech.

## Why This Is Useful

Employees waste time searching across PDFs, wikis, and internal documents. This tool gives them one place to ask questions and get answers from trusted company documents.

## Main Flow

1. Create or select a company.
2. Upload one or more PDFs for that company.
3. Ask a question.
4. Backend searches only that company's document chunks.
5. Sarvam AI generates an answer from the retrieved context.
6. Sources are shown so the user knows which document was used.
7. Listen converts the generated answer into audio.
8. Users can delete one PDF, clear all PDFs for a company, or delete a company.

## Product Features To Mention

- Multi-company separation: each company's documents are searched independently.
- PDF document management: upload, delete one document, clear all documents.
- Multi-document overview: broad questions summarize every uploaded PDF, not just one match.
- Grounded answers: the answer is generated from retrieved document chunks.
- Source visibility: users can see which document chunks were used.
- Listen mode: Sarvam TTS turns the answer into audio.
- Audio controls: users can pause, resume, and start the generated audio over.
- Mobile-friendly UI: company selection scrolls horizontally and buttons are touch-friendly.
- Quick question chips: useful for demo prompts like summary, person name, and skills.

## Code File To Explain

The main GenAI/RAG logic is in `server_py/rag_pipeline.py`.

That file contains:

- PDF text chunking with 300-word chunks and 50-word overlap.
- Keyword-based retrieval for the MVP.
- Multi-document overview handling.
- Guardrails for questions that do not match the uploaded document type.
- Deterministic handling for simple questions like person name.
- Fallback routing to HR, IT, Finance, Sales/Ops, or Knowledge Base Admin.
- Sarvam chat completion call.
- Sarvam TTS call and speech text cleanup.

The React UI was built quickly for the demo, but the RAG system is explainable in Python.

## Important Terms To Explain

RAG means Retrieval-Augmented Generation. It reduces hallucination because the AI is given relevant document context before answering.

Chunking means splitting a large document into smaller text sections so the app can search the most relevant parts instead of sending the whole PDF every time.

This project uses 300-word chunks with a 50-word overlap. Overlap means the last 50 words of one chunk are repeated at the start of the next chunk, so important context is not lost at chunk boundaries.

TTS means Text-to-Speech. In this project, the generated answer is sent to Sarvam TTS and returned as playable audio.

## Current Demo Storage

This project uses JSON file storage for quick local demo setup. In production, I would replace it with MongoDB:

- companies collection
- documents collection
- chunks collection with embeddings

## Production Improvements

- Replace keyword search with embeddings and vector search.
- Store companies, documents, and chunks in MongoDB.
- Add user login and role-based access.
- Encrypt private documents.
- Add support for DOCX, TXT, and webpages.
- Add Hindi/Telugu/Tamil answer and voice options.

## Questions They May Ask

Why not send the whole PDF to the LLM?

Because large documents can exceed context limits and cost more. Retrieval sends only the most relevant chunks.

How do you avoid hallucination?

The system prompt tells the model to answer only from uploaded context. If relevant chunks are not found, the backend returns a fallback message.

Where is the Sarvam API key stored?

Only in `server_py/.env`. The frontend never sees the key.

Can it support multiple companies?

Yes. Each company has its own documents and chunks, and the ask API searches only within the selected company's knowledge base.

Why did you add delete options?

In a real enterprise tool, admins need to manage stale or incorrect documents. Deleting a PDF also deletes its chunks so old knowledge does not affect future answers.

How is the mobile experience handled?

The layout changes on small screens: the company selector becomes horizontally scrollable, main actions become full-width, and document controls are touch-friendly.

Does it cover the assigned requirements?

Mostly yes for an MVP. It supports PDF knowledge ingestion, retrieval-based answering, source visibility, fallback routing, and text-to-audio listening. The current demo stores data in JSON and uses keyword retrieval, while a production build would use MongoDB plus embeddings/vector search. It currently handles PDFs, and DOCX/webpage support can be added later with extra parsers.
