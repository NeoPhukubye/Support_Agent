import { useState, useRef, useEffect, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  MessageSquare, Ticket, RefreshCw, Send, Plus,
  Bot, Zap, Search, FileText, AlertTriangle, CheckCircle,
  Menu, X, AlertCircle, RotateCcw,
} from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const TOOL_ICONS = {
  search_kb: '🔍',
  create_support_ticket: '🎫',
  get_ticket_status: '📋',
  list_my_tickets: '📂',
  escalate_to_human: '🚨',
}

const SUGGESTIONS = [
  "I can't log into my account",
  "How do I cancel my subscription?",
  "I was charged twice this month",
  "Check ticket status",
  "The app is loading very slowly",
  "I need a refund",
]

const AUTOCOMPLETE_SUGGESTIONS = [
  "I can't log into my account",
  "How do I cancel my subscription?",
  "I was charged twice this month",
  "Check ticket status",
  "The app is loading very slowly",
  "I need a refund",
  "How do I reset my password?",
  "Where can I find my invoice?",
  "How do I update my payment method?",
  "I want to upgrade my plan",
  "I want to downgrade my plan",
  "How long does shipping take?",
  "My order hasn't arrived",
  "I received the wrong item",
  "How do I return a product?",
  "I need to change my email address",
  "How do I delete my account?",
  "I'm getting an error message",
  "The app keeps crashing",
  "I can't connect to the service",
  "My data is missing",
  "I was charged the wrong amount",
  "How do I contact a human agent?",
  "I need urgent help",
  "What are your support hours?",
  "How do I export my data?",
  "I forgot my username",
  "How do I enable two-factor authentication?",
  "I think my account was hacked",
  "I need to cancel my order",
]

// ── Markdown renderer ──────────────────────────────────────────────────────────

function MarkdownContent({ content }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        // Inline code
        code({ _node, inline, _className, children, ...props }) {
          return inline ? (
            <code className="md-code-inline" {...props}>{children}</code>
          ) : (
            <pre className="md-code-block"><code {...props}>{children}</code></pre>
          )
        },
        // Links open in new tab
        a({ href, children }) {
          return <a href={href} target="_blank" rel="noopener noreferrer" className="md-link">{children}</a>
        },
        p({ children }) { return <p className="md-p">{children}</p> },
        ul({ children }) { return <ul className="md-ul">{children}</ul> },
        ol({ children }) { return <ol className="md-ol">{children}</ol> },
        li({ children }) { return <li className="md-li">{children}</li> },
        strong({ children }) { return <strong className="md-strong">{children}</strong> },
        h1({ children }) { return <h1 className="md-h">{children}</h1> },
        h2({ children }) { return <h2 className="md-h">{children}</h2> },
        h3({ children }) { return <h3 className="md-h">{children}</h3> },
        blockquote({ children }) { return <blockquote className="md-blockquote">{children}</blockquote> },
        hr() { return <hr className="md-hr" /> },
      }}
    >
      {content}
    </ReactMarkdown>
  )
}

// ── Autocomplete dropdown ──────────────────────────────────────────────────────

function SuggestionDropdown({ suggestions, activeIndex, onSelect, onHover }) {
  if (suggestions.length === 0) return null
  return (
    <ul className="autocomplete-dropdown" role="listbox">
      {suggestions.map((s, i) => (
        <li
          key={s}
          role="option"
          aria-selected={i === activeIndex}
          className={`autocomplete-item${i === activeIndex ? ' active' : ''}`}
          onMouseDown={e => { e.preventDefault(); onSelect(s) }}
          onMouseEnter={() => onHover(i)}
        >
          <Search size={12} className="autocomplete-icon" />
          {s}
        </li>
      ))}
    </ul>
  )
}

// ── Typing indicator ───────────────────────────────────────────────────────────

function TypingIndicator() {
  return (
    <div className="typing-indicator">
      <div className="message-avatar">🤖</div>
      <div className="typing-bubble">
        <div className="typing-dot" />
        <div className="typing-dot" />
        <div className="typing-dot" />
      </div>
    </div>
  )
}

// ── Streaming tool badge row ───────────────────────────────────────────────────

function StreamingTools({ tools }) {
  if (!tools.length) return null
  return (
    <div className="tools-used streaming-tools">
      {tools.map((t, i) => (
        <span key={i} className="tool-badge tool-badge-live">
          <span className="tool-pulse" />
          {TOOL_ICONS[t] || '⚙️'} {t.replace(/_/g, ' ')}
        </span>
      ))}
    </div>
  )
}

// ── Message ────────────────────────────────────────────────────────────────────

function Message({ msg, onRetry }) {
  const time = new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  const isError = msg.isError

  return (
    <div className={`message ${msg.role}${isError ? ' message-error' : ''}`}>
      <div className="message-avatar">
        {msg.role === 'assistant' ? '🤖' : '👤'}
      </div>
      <div className="message-content">
        <div className={`message-bubble${isError ? ' bubble-error' : ''}`}>
          {msg.role === 'assistant' && !isError ? (
            <MarkdownContent content={msg.content} />
          ) : isError ? (
            <div className="error-content">
              <AlertCircle size={16} className="error-icon" />
              <span>{msg.content}</span>
            </div>
          ) : (
            <span>{msg.content}</span>
          )}
        </div>
        <div className="message-meta">
          <span className="message-time">{time}</span>
          {isError && onRetry && (
            <button className="retry-btn" onClick={onRetry} title="Retry">
              <RotateCcw size={12} /> Retry
            </button>
          )}
        </div>
        {msg.tools_used?.length > 0 && (
          <div className="tools-used">
            {msg.tools_used.map((t, i) => (
              <span key={i} className="tool-badge">
                {TOOL_ICONS[t] || '⚙️'} {t.replace(/_/g, ' ')}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Tickets panel ──────────────────────────────────────────────────────────────

function TicketsPanel() {
  const [tickets, setTickets] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const r = await fetch(`${API}/tickets`)
      if (!r.ok) {
        throw new Error(`Failed to load tickets (${r.status})`)
      }
      setTickets(await r.json())
    } catch (err) {
      setError(err.message || 'Failed to load tickets')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const fetchData = async () => {
      await load()
    }
    fetchData()
  }, [load])

  return (
    <div className="tickets-panel">
      <h2>Support Tickets</h2>
      <button className="refresh-btn" onClick={load}>
        <RefreshCw size={13} className={loading ? 'spin' : ''} />
        Refresh
      </button>
      {error ? (
        <div className="empty-state">
          <AlertCircle size={40} strokeWidth={1} />
          <p>{error}</p>
          <button className="refresh-btn" onClick={load}>
            <RefreshCw size={13} className={loading ? 'spin' : ''} />
            Retry
          </button>
        </div>
      ) : tickets.length === 0 ? (
        <div className="empty-state">
          <Ticket size={40} strokeWidth={1} />
          <p>No tickets yet. Start a chat to create one!</p>
        </div>
      ) : (
        tickets.map(t => (
          <div className="ticket-card" key={t.id}>
            <div className="ticket-header">
              <span className="ticket-id">#{t.id}</span>
              <span className={`badge badge-${t.status}`}>{t.status}</span>
            </div>
            <div className="ticket-subject">{t.subject}</div>
            <div className="ticket-desc">{t.description?.slice(0, 100)}...</div>
            <div className="ticket-footer">
              <span className={`badge badge-${t.category}`}>{t.category}</span>
              <span className={`badge badge-${t.priority}`}>{t.priority}</span>
            </div>
          </div>
        ))
      )}
    </div>
  )
}

// ── Main App ───────────────────────────────────────────────────────────────────

export default function App() {
  const [view, setView] = useState('chat')
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [suggestions, setSuggestions] = useState([])
  const [activeSuggestion, setActiveSuggestion] = useState(-1)
  const [sidebarOpen, setSidebarOpen] = useState(false)

  // Streaming state
  const [streamingContent, setStreamingContent] = useState('')
  const [streamingTools, setStreamingTools] = useState([])
  const [isStreaming, setIsStreaming] = useState(false)

  // Last user message for retry
  const lastUserMessageRef = useRef(null)

  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading, streamingContent])

  // Auto-resize textarea
  useEffect(() => {
    const el = inputRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`
  }, [input])

  // Close sidebar on mobile when navigating
  const navigate = (v) => {
    setView(v)
    setSidebarOpen(false)
  }

  const sendMessage = useCallback(async (text) => {
    const content = (text || input).trim()
    if (!content || loading || isStreaming) return
    setInput('')
    setSuggestions([])
    setActiveSuggestion(-1)

    const userMsg = { role: 'user', content, timestamp: Date.now() }
    lastUserMessageRef.current = content

    setMessages(prev => [...prev, userMsg])
    setIsStreaming(true)
    setStreamingContent('')
    setStreamingTools([])

    const history = messages.map(m => ({ role: m.role, content: m.content }))

    try {
      const controller = new AbortController()
      const timeout = setTimeout(() => controller.abort(), 120_000)

      const response = await fetch(`${API}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: content, history }),
        signal: controller.signal,
      })

      clearTimeout(timeout)

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let accumulated = ''
      let toolsUsed = []

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop()

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const raw = line.slice(6).trim()
          if (!raw) continue

          let event
          try { event = JSON.parse(raw) } catch { continue }

          if (event.type === 'token') {
            accumulated += event.content
            setStreamingContent(accumulated)
          } else if (event.type === 'tool') {
            toolsUsed = [...toolsUsed, event.name]
            setStreamingTools([...toolsUsed])
          } else if (event.type === 'done') {
            toolsUsed = event.tools_used ?? toolsUsed
          } else if (event.type === 'error') {
            throw new Error(event.detail)
          }
        }
      }

      // Commit streamed message
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: accumulated || '(no response)',
        tools_used: toolsUsed,
        timestamp: Date.now(),
      }])
    } catch {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Connection error — make sure the backend is running on port 8000.',
        tools_used: [],
        timestamp: Date.now(),
        isError: true,
      }])
    }

    setIsStreaming(false)
    setStreamingContent('')
    setStreamingTools([])
    setLoading(false)
  }, [input, messages, loading, isStreaming])

  const handleRetry = () => {
    if (lastUserMessageRef.current) {
      // Remove the last error message
      setMessages(prev => prev.filter((_, i) => i !== prev.length - 1))
      sendMessage(lastUserMessageRef.current)
    }
  }

  const handleInputChange = (e) => {
    const val = e.target.value
    setInput(val)
    if (val.trim().length >= 2) {
      const lower = val.toLowerCase()
      const filtered = AUTOCOMPLETE_SUGGESTIONS.filter(s =>
        s.toLowerCase().includes(lower)
      ).slice(0, 6)
      setSuggestions(filtered)
      setActiveSuggestion(-1)
    } else {
      setSuggestions([])
      setActiveSuggestion(-1)
    }
  }

  const handleSuggestionSelect = (s) => {
    setInput(s)
    setSuggestions([])
    setActiveSuggestion(-1)
    inputRef.current?.focus()
  }

  const handleKey = (e) => {
    if (suggestions.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setActiveSuggestion(i => Math.min(i + 1, suggestions.length - 1))
        return
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault()
        setActiveSuggestion(i => Math.max(i - 1, -1))
        return
      }
      if (e.key === 'Escape') {
        setSuggestions([])
        setActiveSuggestion(-1)
        return
      }
      if (e.key === 'Tab' || (e.key === 'Enter' && activeSuggestion >= 0)) {
        e.preventDefault()
        handleSuggestionSelect(suggestions[activeSuggestion] ?? suggestions[0])
        return
      }
    }
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const charCount = input.length
  const overLimit = charCount > 2000

  return (
    <div className="app">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Sidebar */}
      <div className={`sidebar${sidebarOpen ? ' sidebar-open' : ''}`}>
        <div className="sidebar-header">
          <div className="logo">
            <div className="logo-icon">🤖</div>
            <h1>SupportAI</h1>
          </div>
          <div className="logo-subtitle">Powered by Agentic AI</div>
          {/* Close button — mobile only */}
          <button className="sidebar-close-btn" onClick={() => setSidebarOpen(false)} aria-label="Close menu">
            <X size={18} />
          </button>
        </div>

        <div className="sidebar-section">
          <button className="new-chat-btn" onClick={() => { setMessages([]); navigate('chat') }}>
            <Plus size={15} /> New Conversation
          </button>
          <div className="sidebar-section-title">Navigation</div>
          <div className={`nav-item ${view === 'chat' ? 'active' : ''}`} onClick={() => navigate('chat')}>
            <MessageSquare size={15} /> Chat with Alex
          </div>
          <div className={`nav-item ${view === 'tickets' ? 'active' : ''}`} onClick={() => navigate('tickets')}>
            <Ticket size={15} /> Tickets
          </div>
        </div>

        <div className="sidebar-nav">
          <div className="sidebar-section-title">Agent Capabilities</div>
          {[
            { icon: <Search size={13}/>, label: 'Knowledge Base Search' },
            { icon: <FileText size={13}/>, label: 'Ticket Management' },
            { icon: <AlertTriangle size={13}/>, label: 'Human Escalation' },
            { icon: <CheckCircle size={13}/>, label: 'Status Lookup' },
            { icon: <Zap size={13}/>, label: 'Issue Classification' },
          ].map(({ icon, label }) => (
            <div className="nav-item" key={label}>{icon} {label}</div>
          ))}
        </div>

        <div className="sidebar-footer">
          <div className="status-indicator">
            <div className="status-dot" />
            {/* Task 1 fix: accurate branding — Bedrock Claude, not Groq/LLaMA */}
            Alex is online — Claude 3.5 via Bedrock
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="chat-area">
        {view === 'tickets' ? (
          <>
            {/* Mobile header for tickets view */}
            <div className="chat-header">
              <div className="chat-header-left">
                <button className="mobile-menu-btn" onClick={() => setSidebarOpen(true)} aria-label="Open menu">
                  <Menu size={18} />
                </button>
                <div className="agent-info">
                  <h2>Support Tickets</h2>
                </div>
              </div>
            </div>
            <TicketsPanel />
          </>
        ) : (
          <>
            <div className="chat-header">
              <div className="chat-header-left">
                <button className="mobile-menu-btn" onClick={() => setSidebarOpen(true)} aria-label="Open menu">
                  <Menu size={18} />
                </button>
                <div className="agent-avatar">🤖</div>
                <div className="agent-info">
                  <h2>Alex — AI Support Agent</h2>
                  <p>
                    <span style={{width:6,height:6,borderRadius:'50%',background:'#10b981',display:'inline-block'}}/>
                    &nbsp;Online · Typically replies instantly
                  </p>
                </div>
              </div>
              <Bot size={18} style={{ color: 'var(--text-muted)' }} />
            </div>

            <div className="chat-messages">
              {messages.length === 0 && !isStreaming ? (
                <div className="welcome">
                  <div className="welcome-icon">🤖</div>
                  <h2>Hi! I'm Alex, your AI support agent</h2>
                  <p>I can answer questions, look up your tickets, create support cases, and escalate complex issues to humans.</p>
                  <div className="suggestion-chips">
                    {SUGGESTIONS.map(s => (
                      <div className="chip" key={s} onClick={() => sendMessage(s)}>{s}</div>
                    ))}
                  </div>
                </div>
              ) : (
                <>
                  {messages.map((m, i) => (
                    <Message
                      key={i}
                      msg={m}
                      onRetry={m.isError ? handleRetry : null}
                    />
                  ))}

                  {/* Live streaming assistant bubble */}
                  {isStreaming && (
                    <div className="message assistant">
                      <div className="message-avatar" style={{background:'linear-gradient(135deg,var(--primary),#8b5cf6)'}}>🤖</div>
                      <div className="message-content">
                        <div className="message-bubble">
                          {streamingContent
                            ? <MarkdownContent content={streamingContent} />
                            : <TypingIndicator inline />
                          }
                          <span className="streaming-cursor" />
                        </div>
                        {streamingTools.length > 0 && <StreamingTools tools={streamingTools} />}
                      </div>
                    </div>
                  )}

                  <div ref={bottomRef} />
                </>
              )}
            </div>

            <div className="chat-input-area">
              <div className="input-container">
                <SuggestionDropdown
                  suggestions={suggestions}
                  activeIndex={activeSuggestion}
                  onSelect={handleSuggestionSelect}
                  onHover={setActiveSuggestion}
                />
                <div className={`input-wrapper${overLimit ? ' input-over-limit' : ''}`}>
                  <textarea
                    ref={inputRef}
                    className="chat-input"
                    placeholder="Ask a question or describe your issue..."
                    value={input}
                    onChange={handleInputChange}
                    onKeyDown={handleKey}
                    rows={1}
                    aria-autocomplete="list"
                    aria-expanded={suggestions.length > 0}
                    disabled={isStreaming}
                  />
                  <div className="input-right">
                    {charCount > 1800 && (
                      <span className={`char-count${overLimit ? ' over' : ''}`}>
                        {charCount}/2000
                      </span>
                    )}
                    <button
                      className="send-btn"
                      onClick={() => sendMessage()}
                      disabled={!input.trim() || loading || isStreaming || overLimit}
                    >
                      <Send size={15} />
                    </button>
                  </div>
                </div>
              </div>
              <div className="input-hint">Press Enter to send · Shift+Enter for new line · ↑↓ to navigate suggestions</div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
