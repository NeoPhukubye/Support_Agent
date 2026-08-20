import { useState, useRef, useEffect } from 'react'
import {
  MessageSquare, Ticket, RefreshCw, Send, Plus,
  Bot, Zap, Search, FileText, AlertTriangle, CheckCircle
} from 'lucide-react'

const API = 'http://localhost:8000'

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

function Message({ msg }) {
  const time = new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  return (
    <div className={`message ${msg.role}`}>
      <div className="message-avatar">
        {msg.role === 'assistant' ? '🤖' : '👤'}
      </div>
      <div className="message-content">
        <div className="message-bubble">{msg.content}</div>
        <div className="message-meta">
          <span className="message-time">{time}</span>
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

function TicketsPanel() {
  const [tickets, setTickets] = useState([])
  const [loading, setLoading] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const r = await fetch(`${API}/tickets`)
      setTickets(await r.json())
    } catch { }
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  return (
    <div className="tickets-panel">
      <h2>Support Tickets</h2>
      <button className="refresh-btn" onClick={load}>
        <RefreshCw size={13} className={loading ? 'spin' : ''} />
        Refresh
      </button>
      {tickets.length === 0 ? (
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

export default function App() {
  const [view, setView] = useState('chat')
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const sendMessage = async (text) => {
    const content = text || input.trim()
    if (!content || loading) return
    setInput('')

    const userMsg = { role: 'user', content, timestamp: Date.now() }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)

    try {
      const history = messages.map(m => ({ role: m.role, content: m.content }))
      const r = await fetch(`${API}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: content, history }),
      })
      const data = await r.json()
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.response,
        tools_used: data.tools_used,
        timestamp: Date.now(),
      }])
    } catch (e) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '⚠️ Connection error. Make sure the backend is running on port 8000.',
        tools_used: [],
        timestamp: Date.now(),
      }])
    }
    setLoading(false)
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="app">
      {/* Sidebar */}
      <div className="sidebar">
        <div className="sidebar-header">
          <div className="logo">
            <div className="logo-icon">🤖</div>
            <h1>SupportAI</h1>
          </div>
          <div className="logo-subtitle">Powered by Agentic AI</div>
        </div>

        <div className="sidebar-section">
          <button className="new-chat-btn" onClick={() => { setMessages([]); setView('chat') }}>
            <Plus size={15} /> New Conversation
          </button>
          <div className="sidebar-section-title">Navigation</div>
          <div className={`nav-item ${view === 'chat' ? 'active' : ''}`} onClick={() => setView('chat')}>
            <MessageSquare size={15} /> Chat with Alex
          </div>
          <div className={`nav-item ${view === 'tickets' ? 'active' : ''}`} onClick={() => setView('tickets')}>
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
            <div className="nav-item" key={label}>
              {icon} {label}
            </div>
          ))}
        </div>

        <div className="sidebar-footer">
          <div className="status-indicator">
            <div className="status-dot" />
            Alex is online — LLaMA 3 70B via Groq
          </div>
        </div>
      </div>

      {/* Main */}
      <div className="chat-area">
        {view === 'tickets' ? (
          <TicketsPanel />
        ) : (
          <>
            <div className="chat-header">
              <div className="chat-header-left">
                <div className="agent-avatar">🤖</div>
                <div className="agent-info">
                  <h2>Alex — AI Support Agent</h2>
                  <p><span style={{width:6,height:6,borderRadius:'50%',background:'#10b981',display:'inline-block'}}/>  Online · Typically replies instantly</p>
                </div>
              </div>
              <Bot size={18} style={{ color: 'var(--text-muted)' }} />
            </div>

            <div className="chat-messages">
              {messages.length === 0 ? (
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
                  {messages.map((m, i) => <Message key={i} msg={m} />)}
                  {loading && <TypingIndicator />}
                  <div ref={bottomRef} />
                </>
              )}
            </div>

            <div className="chat-input-area">
              <div className="input-wrapper">
                <textarea
                  ref={inputRef}
                  className="chat-input"
                  placeholder="Ask a question or describe your issue..."
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={handleKey}
                  rows={1}
                />
                <button className="send-btn" onClick={() => sendMessage()} disabled={!input.trim() || loading}>
                  <Send size={15} />
                </button>
              </div>
              <div className="input-hint">Press Enter to send · Shift+Enter for new line</div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
