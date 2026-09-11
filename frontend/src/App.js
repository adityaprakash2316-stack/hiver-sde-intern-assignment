import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8080/api/v1';

function App() {
  const [messages, setMessages] = useState([
    {
      role: 'system',
      content: 'AppleSupport AI Agent ready. Type a customer message to classify intent, draft a grounded reply, and get an escalation decision.',
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [lastResult, setLastResult] = useState(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || loading) return;

    setMessages((prev) => [...prev, { role: 'user', content: text }]);
    setInput('');
    setLoading(true);
    setLastResult(null);

    try {
      const res = await axios.post(`${API_BASE}/support`, { text });
      const data = res.data;
      setLastResult(data);

      const agentMsg = {
        role: 'agent',
        content: data.draftReply,
        meta: {
          intent: data.intent,
          confidence: data.intentConfidence,
          escalate: data.shouldEscalate,
          reason: data.escalationReason,
        },
      };
      setMessages((prev) => [...prev, agentMsg]);
    } catch (err) {
      const errMsg = err.response?.data?.message || err.message || 'Request failed';
      setMessages((prev) => [
        ...prev,
        { role: 'system', content: `Error: ${errMsg}. Is the backend (8080) and AI service (8000) running?` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const examples = [
    'My iPhone 13 battery is draining insanely fast after the latest update.',
    'I want to speak to a supervisor. This is the 4th time about the same issue.',
    'How do I transfer data from my old iPhone without iCloud?',
    'Green lines appeared on my screen today. Hardware issue?',
  ];

  return (
    <div className="app">
      <header className="header">
        <div className="logo">Hiver</div>
        <div className="subtitle">AppleSupport AI Agent · SDE Intern Assignment</div>
      </header>

      <div className="main">
        <div className="chat-panel">
          <div className="messages">
            {messages.map((m, i) => (
              <div key={i} className={`msg msg-${m.role}`}>
                <div className="msg-content">{m.content}</div>
                {m.meta && (
                  <div className="msg-meta">
                    <span className={`badge ${m.meta.escalate ? 'badge-escalate' : 'badge-auto'}`}>
                      {m.meta.escalate ? 'ESCALATE' : 'AUTO-HANDLE'}
                    </span>
                    <span className="badge badge-intent">{m.meta.intent}</span>
                    <span className="conf">conf { (m.meta.confidence * 100).toFixed(1) }%</span>
                    <div className="reason">{m.meta.reason}</div>
                  </div>
                )}
              </div>
            ))}
            {loading && <div className="msg msg-system">Thinking…</div>}
            <div ref={bottomRef} />
          </div>

          <div className="input-area">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="Type a customer support message…"
              rows={2}
              disabled={loading}
            />
            <button onClick={sendMessage} disabled={loading || !input.trim()}>
              Send
            </button>
          </div>

          <div className="examples">
            <span>Try:</span>
            {examples.map((ex, i) => (
              <button key={i} className="ex-btn" onClick={() => setInput(ex)}>
                {ex.slice(0, 40)}…
              </button>
            ))}
          </div>
        </div>

        <div className="side-panel">
          <h3>Last Decision</h3>
          {lastResult ? (
            <div className="result-card">
              <div className="row">
                <strong>Intent</strong>
                <span>{lastResult.intent}</span>
              </div>
              <div className="row">
                <strong>Confidence</strong>
                <span>{(lastResult.intentConfidence * 100).toFixed(1)}%</span>
              </div>
              <div className="row">
                <strong>Action</strong>
                <span className={lastResult.shouldEscalate ? 'escalate' : 'auto'}>
                  {lastResult.shouldEscalate ? 'Escalate to human' : 'Auto-handle'}
                </span>
              </div>
              <div className="row full">
                <strong>Reason</strong>
                <p>{lastResult.escalationReason}</p>
              </div>
              <div className="row full">
                <strong>Retrieved similar cases</strong>
                <ul className="retrieved">
                  {(lastResult.retrievedExamples || []).map((r, i) => (
                    <li key={i}>
                      <div className="sim">sim {r.similarity}</div>
                      <div className="cust">{r.customer_message}</div>
                      <div className="hist">{r.historical_reply}</div>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ) : (
            <p className="hint">Send a message to see classification, draft, and escalation decision.</p>
          )}

          <div className="info-box">
            <h4>What this agent does</h4>
            <ol>
              <li>Classifies into 14 intents learned from AppleSupport data</li>
              <li>Retrieves similar historical resolutions</li>
              <li>Drafts a reply grounded in those resolutions</li>
              <li>Decides auto-handle vs escalate with a stated reason</li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
