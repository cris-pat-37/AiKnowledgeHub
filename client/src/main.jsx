import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Building2,
  FileText,
  FileX2,
  Headphones,
  Loader2,
  MessageSquareText,
  Pause,
  Play,
  Plus,
  RotateCcw,
  Search,
  Trash2,
  Upload
} from "lucide-react";
import {
  askQuestion,
  clearDocuments,
  createCompany,
  deleteCompany,
  deleteDocument,
  generateSpeech,
  getCompanies,
  getCompany,
  uploadDocument
} from "./api.js";
import "./styles.css";

const quickQuestions = [
  "What are all uploaded documents about?",
  "If this is a project brief, what should be built?",
  "Summarize this document",
  "Name of person",
  "Main skills and responsibilities"
];

function App() {
  const [companies, setCompanies] = useState([]);
  const [activeCompanyId, setActiveCompanyId] = useState("");
  const [companyDetails, setCompanyDetails] = useState(null);
  const [companyName, setCompanyName] = useState("");
  const [question, setQuestion] = useState("What are all uploaded documents about?");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState([]);
  const [status, setStatus] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isGeneratingAudio, setIsGeneratingAudio] = useState(false);
  const [audioPlayer, setAudioPlayer] = useState(null);
  const [audioState, setAudioState] = useState("idle");

  const activeCompany = useMemo(
    () => companies.find((company) => company.id === activeCompanyId),
    [activeCompanyId, companies]
  );

  async function loadCompanies(nextActiveId = activeCompanyId) {
    const data = await getCompanies();
    setCompanies(data.companies);

    if (nextActiveId && data.companies.some((company) => company.id === nextActiveId)) {
      setActiveCompanyId(nextActiveId);
      return;
    }

    setActiveCompanyId(data.companies[0]?.id || "");
  }

  async function loadCompanyDetails(companyId) {
    if (!companyId) {
      setCompanyDetails(null);
      return;
    }

    const data = await getCompany(companyId);
    setCompanyDetails(data);
  }

  useEffect(() => {
    loadCompanies("").catch((error) => setStatus(error.message));
  }, []);

  useEffect(() => {
    loadCompanyDetails(activeCompanyId).catch((error) => setStatus(error.message));
  }, [activeCompanyId]);

  async function handleCreateCompany(event) {
    event.preventDefault();

    if (!companyName.trim()) {
      setStatus("Enter a company name first.");
      return;
    }

    try {
      setIsLoading(true);
      const data = await createCompany(companyName);
      setCompanyName("");
      await loadCompanies(data.company.id);
      setStatus(`${data.company.name} knowledge hub is ready.`);
    } catch (error) {
      setStatus(error.message);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleUpload(event) {
    const file = event.target.files?.[0];

    if (!file || !activeCompanyId) {
      return;
    }

    try {
      setIsLoading(true);
      setStatus(`Uploading ${file.name}...`);
      const data = await uploadDocument(activeCompanyId, file);
      await loadCompanies(activeCompanyId);
      await loadCompanyDetails(activeCompanyId);
      setStatus(data.message);
    } catch (error) {
      setStatus(error.message);
    } finally {
      event.target.value = "";
      setIsLoading(false);
    }
  }

  async function handleAsk(event) {
    event.preventDefault();

    if (!activeCompanyId) {
      setStatus("Create or select a company first.");
      return;
    }

    if (!question.trim()) {
      setStatus("Type a question first.");
      return;
    }

    try {
      setIsLoading(true);
      setAnswer("");
      setSources([]);
      resetAudio();
      setStatus("Searching documents and asking Sarvam AI...");
      const data = await askQuestion(activeCompanyId, question);
      setAnswer(data.answer);
      setSources(data.sources || []);
      setStatus("Answer generated from uploaded knowledge.");
    } catch (error) {
      setStatus(error.message);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleListen() {
    if (!answer) {
      return;
    }

    if (audioPlayer && audioState === "playing") {
      audioPlayer.pause();
      setAudioState("paused");
      setStatus("Audio paused.");
      return;
    }

    if (audioPlayer && audioState === "paused") {
      await audioPlayer.play();
      setAudioState("playing");
      setStatus("Resumed audio.");
      return;
    }

    if (audioPlayer && audioState === "idle") {
      if (audioPlayer.restart) {
        await audioPlayer.restart();
        setAudioState("playing");
        setStatus("Started audio again.");
        return;
      }

      audioPlayer.currentTime = 0;
      await audioPlayer.play();
      setAudioState("playing");
      setStatus("Started audio again.");
      return;
    }

    try {
      setIsGeneratingAudio(true);
      setStatus("Generating audio with Sarvam TTS...");
      const data = await generateSpeech(answer);

      if (data.demoSpeech) {
        const speak = () => {
          const utterance = new SpeechSynthesisUtterance(data.text);
          utterance.lang = "en-IN";
          utterance.onend = () => setAudioState("idle");
          utterance.onpause = () => setAudioState("paused");
          utterance.onresume = () => setAudioState("playing");
          utterance.onstart = () => setAudioState("playing");
          window.speechSynthesis.cancel();
          window.speechSynthesis.speak(utterance);
        };
        speak();
        setAudioPlayer({
          pause: () => window.speechSynthesis.pause(),
          play: () => {
            window.speechSynthesis.resume();
            return Promise.resolve();
          },
          restart: () => {
            speak();
            return Promise.resolve();
          },
          currentTime: 0
        });
        setStatus("Playing generated answer.");
        return;
      }

      const audio = new Audio(`data:${data.mimeType};base64,${data.audioBase64}`);
      audio.onended = () => setAudioState("idle");
      audio.onpause = () => {
        if (!audio.ended) {
          setAudioState("paused");
        }
      };
      audio.onplay = () => setAudioState("playing");
      setAudioPlayer(audio);
      await audio.play();
      setStatus("Playing generated answer.");
    } catch (error) {
      setStatus(error.message);
    } finally {
      setIsGeneratingAudio(false);
    }
  }

  function resetAudio() {
    if (audioPlayer) {
      audioPlayer.pause();
      audioPlayer.currentTime = 0;
    }

    setAudioPlayer(null);
    setAudioState("idle");
  }

  async function handleRestartAudio() {
    if (!audioPlayer) {
      return;
    }

    if (audioPlayer.restart) {
      await audioPlayer.restart();
      setAudioState("playing");
      setStatus("Restarted audio from the beginning.");
      return;
    }

    audioPlayer.currentTime = 0;
    await audioPlayer.play();
    setAudioState("playing");
    setStatus("Restarted audio from the beginning.");
  }

  async function refreshActiveCompany(message) {
    await loadCompanies(activeCompanyId);
    await loadCompanyDetails(activeCompanyId);
    setAnswer("");
    setSources([]);
    resetAudio();
    setStatus(message);
  }

  async function handleDeleteDocument(documentId, fileName) {
    const confirmed = window.confirm(`Delete ${fileName} from this company knowledge base?`);

    if (!confirmed) {
      return;
    }

    try {
      setIsLoading(true);
      const data = await deleteDocument(activeCompanyId, documentId);
      await refreshActiveCompany(data.message);
    } catch (error) {
      setStatus(error.message);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleClearDocuments() {
    const confirmed = window.confirm(`Delete all PDFs from ${activeCompany?.name}?`);

    if (!confirmed) {
      return;
    }

    try {
      setIsLoading(true);
      const data = await clearDocuments(activeCompanyId);
      await refreshActiveCompany(data.message);
    } catch (error) {
      setStatus(error.message);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleDeleteCompany() {
    const confirmed = window.confirm(`Delete ${activeCompany?.name} and all its documents?`);

    if (!confirmed) {
      return;
    }

    try {
      setIsLoading(true);
      const data = await deleteCompany(activeCompanyId);
      const nextCompanyId = companies.find((company) => company.id !== activeCompanyId)?.id || "";
      setCompanyDetails(null);
      setAnswer("");
      setSources([]);
      await loadCompanies(nextCompanyId);
      setStatus(data.message);
    } catch (error) {
      setStatus(error.message);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <Search size={22} />
          </div>
          <div>
            <p>Enterprise AI</p>
            <h1>Knowledge Hub</h1>
          </div>
        </div>

        <form className="company-form" onSubmit={handleCreateCompany}>
          <input
            value={companyName}
            onChange={(event) => setCompanyName(event.target.value)}
            placeholder="Add company"
          />
          <button type="submit" aria-label="Create company">
            <Plus size={18} />
          </button>
        </form>

        <div className="company-list">
          {companies.length === 0 ? (
            <p className="empty">Create a company to start.</p>
          ) : (
            companies.map((company) => (
              <button
                className={company.id === activeCompanyId ? "company active" : "company"}
                key={company.id}
                onClick={() => {
                  setActiveCompanyId(company.id);
                  setAnswer("");
                  setSources([]);
                  resetAudio();
                }}
              >
                <Building2 size={18} />
                <span>
                  <strong>{company.name}</strong>
                  <small>
                    {company.documentCount} docs - {company.chunkCount} chunks
                  </small>
                </span>
              </button>
            ))
          )}
        </div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p>Selected company</p>
            <h2>{activeCompany?.name || "No company selected"}</h2>
          </div>

          <div className="topbar-actions">
            <label className={activeCompanyId ? "upload-button" : "upload-button disabled"}>
              <Upload size={18} />
              Upload PDF
              <input
                type="file"
                accept="application/pdf"
                disabled={!activeCompanyId || isLoading}
                onChange={handleUpload}
              />
            </label>

            <button
              className="danger-button"
              disabled={!activeCompanyId || isLoading}
              onClick={handleDeleteCompany}
              title="Delete selected company"
            >
              <Trash2 size={18} />
              Delete company
            </button>
          </div>
        </header>

        <section className="content-grid">
          <div className="panel ask-panel">
            <div className="panel-title">
              <MessageSquareText size={20} />
              <h3>Ask company knowledge</h3>
            </div>

            <form onSubmit={handleAsk}>
              <textarea
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="Ask about uploaded PDFs..."
              />

              <div className="quick-questions" aria-label="Quick questions">
                {quickQuestions.map((item) => (
                  <button key={item} type="button" onClick={() => setQuestion(item)}>
                    {item}
                  </button>
                ))}
              </div>

              <button className="primary-button" type="submit" disabled={isLoading}>
                {isLoading ? <Loader2 className="spin" size={18} /> : <Search size={18} />}
                Ask AI
              </button>
            </form>

            {status && <p className="status">{status}</p>}
          </div>

          <div className="panel docs-panel">
            <div className="panel-title split">
              <div>
                <FileText size={20} />
                <h3>Uploaded documents</h3>
              </div>

              <button
                className="icon-danger"
                disabled={!companyDetails?.documents?.length || isLoading}
                onClick={handleClearDocuments}
                title="Clear all documents"
                aria-label="Clear all documents"
              >
                <FileX2 size={18} />
              </button>
            </div>

            {companyDetails?.documents?.length ? (
              <div className="document-list">
                {companyDetails.documents.map((doc) => (
                  <article className="document-item" key={doc.id}>
                    <div>
                      <strong>{doc.fileName}</strong>
                      <small>
                        {doc.chunkCount} chunks - {doc.characterCount.toLocaleString()} characters
                      </small>
                    </div>

                    <button
                      className="icon-danger"
                      disabled={isLoading}
                      onClick={() => handleDeleteDocument(doc.id, doc.fileName)}
                      title="Delete document"
                      aria-label={`Delete ${doc.fileName}`}
                    >
                      <Trash2 size={17} />
                    </button>
                  </article>
                ))}
              </div>
            ) : (
              <p className="empty">Upload PDFs for this company.</p>
            )}
          </div>
        </section>

        <section className="answer-area">
          <div className="answer-header">
            <div>
              <p>Generated answer</p>
              <h3>Sarvam AI response</h3>
            </div>

            <div className="audio-actions">
              <button
                className="listen-button"
                onClick={handleListen}
                disabled={!answer || isGeneratingAudio}
              >
                {isGeneratingAudio && <Loader2 className="spin" size={18} />}
                {!isGeneratingAudio && audioState === "playing" && <Pause size={18} />}
                {!isGeneratingAudio && audioState === "paused" && <Play size={18} />}
                {!isGeneratingAudio && audioState === "idle" && <Headphones size={18} />}
                {isGeneratingAudio && "Preparing"}
                {!isGeneratingAudio && audioState === "playing" && "Pause"}
                {!isGeneratingAudio && audioState === "paused" && "Resume audio"}
                {!isGeneratingAudio && audioState === "idle" && "Listen"}
              </button>

              {audioPlayer && (
                <button className="restart-button" onClick={handleRestartAudio} title="Start audio again">
                  <RotateCcw size={17} />
                  Start over
                </button>
              )}
            </div>
          </div>

          <div className="answer-box">
            {answer || "Your answer will appear here after asking a question."}
          </div>

          {sources.length > 0 && (
            <div className="sources">
              <h4>Sources used</h4>
              <div>
                {sources.map((source, index) => (
                  <span key={`${source.documentName}-${source.chunk}-${index}`}>
                    {source.documentName} - chunk {source.chunk}
                  </span>
                ))}
              </div>
            </div>
          )}
        </section>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
