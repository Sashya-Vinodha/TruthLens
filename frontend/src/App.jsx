import React, { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import "./App.css";

const API_BASE =
  typeof window !== "undefined" && window.location.port === "8000"
    ? window.location.origin
    : "http://127.0.0.1:8000";

const LensMark = ({ small = false }) => (
  <div className={small ? "lens-mark lens-mark-small" : "lens-mark"}>
    <svg viewBox="0 0 100 100" fill="none">
      <rect width="100" height="100" rx="24" fill="currentColor" />
      <circle cx="48" cy="47" r="23" stroke="white" strokeWidth="7" />
      <path d="M65 65L79 79" stroke="white" strokeWidth="7" strokeLinecap="round" />
      <path d="M38 49L47 58L61 40" stroke="white" strokeWidth="7" strokeLinecap="round" />
    </svg>
  </div>
);

export default function App() {
  const [showSplash, setShowSplash] = useState(true);
  
  const [messages, setMessages] = useState([
    {
      role: "ai",
      content: "Hello. I am ready to verify facts for you.",
      safety_status: null,
      evidence_label: null,
      sources: [],
    },
  ]);

  const [input, setInput] = useState("");
  const [docsCount, setDocsCount] = useState(3);
  const [isLoading, setIsLoading] = useState(false);

  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages, isLoading]);

  useEffect(() => {
    const timer = setTimeout(() => {
      setShowSplash(false);
    }, 2500);

    return () => clearTimeout(timer);
  }, []);

  const handleSend = async (e) => {
    if (e) e.preventDefault();

    if (!input.trim() || isLoading) return;

    const question = input.trim();

    const userMessage = {
      role: "user",
      content: question,
      timestamp: new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE}/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question,
          k: Number(docsCount),
        }),
      });

      if (!response.ok) {
        throw new Error(`Backend returned ${response.status}`);
      }

      const data = await response.json();

      const assistantMessage = {
        role: "ai",
        content:
          data.answer ||
          data.response ||
          "No response generated.",

        safety_status: data.safety_status,
        evidence_label: data.evidence_label,
        confidence: data.confidence,
        sources: data.retrieved_docs || [],
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      console.error(err);

      setMessages((prev) => [
        ...prev,
        {
          role: "ai",
          content:
            "Unable to connect to the TruthLens backend. Verify that FastAPI is running and reachable.",
          safety_status: "Blocked",
          evidence_label: "Contradicted / Unsupported",
          sources: [],
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const renderSafetyBadge = (status) => {
    if (!status) return null;

    if (status.includes("Blocked")) {
      return (
        <span className="badge badge-blocked">
          🛑 {status}
        </span>
      );
    }

    if (status.includes("Boundary")) {
      return (
        <span className="badge badge-safe">
          🛡️ Safe (Abstain)
        </span>
      );
    }

    return (
      <span className="badge badge-safe">
        🟢 {status}
      </span>
    );
  };

  const renderEvidenceBadge = (label) => {
    if (!label) return null;

    switch (label) {
      case "Direct Evidence":
        return (
          <span className="badge badge-direct">
            🎯 Direct Evidence
          </span>
        );

      case "Inferred From Sources":
        return (
          <span className="badge badge-inferred">
            🔗 Inferred From Sources
          </span>
        );

      case "Out Of Corpus":
        return (
          <span className="badge badge-out-of-corpus">
            ⚪ Out Of Corpus
          </span>
        );

      default:
        return (
          <span className="badge badge-unsupported">
            ⚠️ Contradicted / Unsupported
          </span>
        );
    }
  };

  if (showSplash) {
    return (
      <div className="entry-screen">
        <div className="entry-lens">
          <span>🛡️</span>
        </div>
        <h1>TruthLens</h1>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <header className="header">
        <LensMark small />
        <div className="header-info">
          <h1>TruthLens AI</h1>
          <p>
            <span className="status-dot" />
            Online | Retrieval-Augmented Verification
          </p>
        </div>
      </header>

      <main className="chat-area">
        {messages.map((msg, index) => (
          <div
            key={index}
            className={`message-row ${
              msg.role === "user" ? "user-row" : "ai-row"
            } fade-up`}
          >
            {msg.role === "ai" && <LensMark small />}

            <div
              className={`bubble ${
                msg.role === "user"
                  ? "user-bubble"
                  : "ai-bubble"
              }`}
            >
              {msg.role === "ai" ? (
                <ReactMarkdown>
                  {msg.content}
                </ReactMarkdown>
              ) : (
                <p style={{ margin: 0 }}>
                  {msg.content}
                </p>
              )}

              {msg.timestamp && (
                <span className="timestamp">
                  {msg.timestamp}
                </span>
              )}

              {msg.role === "ai" &&
                (msg.safety_status ||
                  msg.evidence_label) && (
                  <div className="result-row">
                    {renderSafetyBadge(
                      msg.safety_status
                    )}
                    {renderEvidenceBadge(
                      msg.evidence_label
                    )}
                  </div>
                )}

              {msg.sources?.length > 0 && (
                <div className="sources-box">
                  <strong>
                    Evidence Audit Trail
                  </strong>

                  {msg.sources.map(
                    (source, sourceIndex) => (
                      <div
                        key={sourceIndex}
                        className="source-item"
                      >
                        <div className="source-header">
                          <span className="source-doc">
                            📄{" "}
                            {source.title ||
                              "Source Document"}
                          </span>
                        </div>

                        <div className="source-snippet">
                          "
                          {source.text?.slice(
                            0,
                            320
                          )}
                          ..."
                        </div>
                      </div>
                    )
                  )}
                </div>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="message-row ai-row fade-up">
            <LensMark small />

            <div className="bubble ai-bubble">
              <div className="thinking-wave">
                <span />
                <span />
                <span />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </main>

      <footer className="footer">
        <div className="docs-pill">
          Docs

          <input
            type="number"
            min="1"
            max="10"
            value={docsCount}
            onChange={(e) =>
              setDocsCount(Number(e.target.value))
            }
          />
        </div>

        <form
          className="input-pill"
          onSubmit={handleSend}
          style={{
            display: "flex",
            alignItems: "center",
          }}
        >
          <input
            type="text"
            value={input}
            disabled={isLoading}
            placeholder="Ask TruthLens to verify a claim..."
            onChange={(e) =>
              setInput(e.target.value)
            }
          />
        </form>

        <button
          type="submit"
          onClick={handleSend}
          className="send-btn"
          disabled={
            isLoading || !input.trim()
          }
        >
          <svg viewBox="0 0 24 24">
            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
          </svg>
        </button>
      </footer>
    </div>
  );
}