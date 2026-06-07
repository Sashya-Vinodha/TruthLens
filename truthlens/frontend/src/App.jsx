import React, { useEffect, useState } from "react";
import "./App.css";
import ReactMarkdown from 'react-markdown';

const API_BASE =
  typeof window !== "undefined" && window.location.port === "8000"
    ? window.location.origin
    : "http://127.0.0.1:8000";

function ThinkingWave() {
  return (
    <div className="thinking-wave" aria-label="Thinking">
      <span />
      <span />
      <span />
    </div>
  );
}

function LensMark({ small = false }) {
  return (
    <div className={small ? "lens-mark lens-mark-small" : "lens-mark"}>
      <svg viewBox="0 0 100 100" role="img" aria-label="TruthLens">
        <rect width="100" height="100" rx="24" fill="currentColor" />
        <circle cx="48" cy="47" r="23" fill="none" stroke="white" strokeWidth="7" />
        <path d="M65 65L79 79" stroke="white" strokeWidth="7" strokeLinecap="round" />
        <path
          d="M38 49L47 58L61 40"
          fill="none"
          stroke="white"
          strokeWidth="7"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
}

function App() {
  const [isLoaded, setIsLoaded] = useState(false);
  const [question, setQuestion] = useState("");
  const [k, setK] = useState(3);
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState([
    {
      id: "welcome",
      type: "ai",
      answer: "Hello. I am ready to verify facts for you.",
      abstain: false,
      retrieved_docs: [],
      timestamp: "Just now",
    },
  ]);

  useEffect(() => {
    const timer = setTimeout(() => setIsLoaded(true), 1200);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    const chat = document.querySelector(".chat-area");
    if (chat) chat.scrollTop = chat.scrollHeight;
  }, [messages, loading]);

  async function handleSubmit(event) {
    event.preventDefault();

    const text = question.trim();
    if (!text || loading) return;

    setMessages((current) => [
      ...current,
      {
        id: `user-${Date.now()}`,
        type: "user",
        answer: text,
        timestamp: new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        }),
      },
    ]);
    setQuestion("");
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: text, k: Number(k) || 3 }),
      });

      if (!response.ok) {
        const backendText = await response.text();
        throw new Error(`Backend error (${response.status}): ${backendText || response.statusText}`);
      }

      const data = await response.json();
      setMessages((current) => [
        ...current,
        {
          id: `ai-${Date.now()}`,
          type: "ai",
          answer: data.answer,
          safety_status: data.safety_status,     
          evidence_label: data.evidence_label,   
          abstain: data.abstain,
          retrieved_docs: data.retrieved_docs || [],
          timestamp: new Date().toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          }),
        },
      ]);
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          id: `error-${Date.now()}`,
          type: "ai",
          answer: `Error: ${error.message}`,
          safety_status: "Error",
          abstain: true,
          retrieved_docs: [],
          timestamp: new Date().toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          }),
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  if (!isLoaded) {
    return (
      <main className="entry-screen">
        <div className="entry-lens" aria-hidden="true">
          <span>🔍</span>
        </div>
        <h1>TruthLens</h1>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <header className="header">
        <LensMark />
        <div className="header-info">
          <h1>TruthLens AI</h1>
          <p>
            <span className="status-dot" />
            Online | Fact Verification
          </p>
        </div>
      </header>

      <div className="chat-area">
        {messages.map((message) => {
          const isAi = message.type === "ai";

          return (
            <div
              className={`message-row fade-up ${isAi ? "ai-row" : "user-row"}`}
              key={message.id}
            >
              {isAi && <LensMark small />}
              <div
                className={
                  isAi
                    ? `bubble ai-bubble ai-message ${!message.abstain && message.id !== 'welcome' ? "verified" : ""}`
                    : "bubble user-bubble"
                }
              >
                  <div className="markdown-body">
                    <ReactMarkdown>{message.answer}</ReactMarkdown>
                  </div>

                {/* THE NEW DUAL-BADGE RENDER BLOCK */}
                {isAi && message.safety_status && message.id !== 'welcome' && (
                  <div className="result-row">
                    <span className={message.abstain ? "badge badge-blocked" : "badge badge-safe"}>
                      {message.abstain ? "🛑 " : "🟢 "}{message.safety_status}
                    </span>
                    
                    {message.evidence_label && (
                      <span className={
                        message.evidence_label === "Direct Evidence" ? "badge badge-direct" : 
                        message.evidence_label === "Inferred From Sources" ? "badge badge-inferred" : 
                        message.evidence_label === "Domain Extrapolation" ? "badge badge-extrapolation" :
                        message.evidence_label === "Out Of Corpus" ? "badge badge-out-of-corpus" :
                        "badge badge-unsupported"
                      }>
                        {message.evidence_label === "Direct Evidence" ? "🎯 Direct Evidence" : 
                          message.evidence_label === "Inferred From Sources" ? "🔗 Inferred From Sources" : 
                          message.evidence_label === "Domain Extrapolation" ? "⚖️ Domain Extrapolation" : 
                          message.evidence_label === "Out Of Corpus" ? "⚪ Out Of Corpus" : 
                          "⚠️ Contradicted / Unsupported"}
                      </span>
                    )}
                  </div>
                )}

                {/* THE NEW SOURCE AUDIT TRAIL BLOCK */}
                {isAi && message.retrieved_docs?.length > 0 && (
                  <div className="sources-box">
                    <strong>Audit Trail:</strong>
                    {message.retrieved_docs.map((doc, index) => (
                      <div className="source-item" key={`doc-${index}`}>
                        <div className="source-header">
                          <span className="source-doc">📄 Source Document</span>
                          <span className="source-section">{doc.title || "Untitled Section"}</span>
                        </div>
                        {doc.text && (
                          <div className="source-snippet">
                            "{doc.text.substring(0, 140)}..."
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                <span className="timestamp">{message.timestamp}</span>
              </div>
            </div>
          );
        })}

        {loading && (
          <div className="message-row fade-up ai-row">
            <LensMark small />
            <div className="bubble ai-bubble ai-message">
              <ThinkingWave />
            </div>
          </div>
        )}
      </div>

      <form className="footer" onSubmit={handleSubmit}>
        <label className="docs-pill" title="Number of documents">
          <span>Docs</span>
          <input
            max="5"
            min="1"
            onChange={(event) => setK(event.target.value)}
            type="number"
            value={k}
          />
        </label>
        <label className="input-pill">
          <input
            autoComplete="off"
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ask TruthLens to verify a claim..."
            type="text"
            value={question}
          />
        </label>
        <button className="send-btn" disabled={loading} type="submit" aria-label="Send question">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
          </svg>
        </button>
      </form>
    </main>
  );
}

export default App;