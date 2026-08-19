# SupportAI — Agentic Customer Support

> **AWS Summit Hackathon: From Idea to MVP with Agentic AI**

An intelligent AI customer support agent powered by LangGraph, Groq (LLaMA 3), and a vector knowledge base — architected for AWS Bedrock deployment.

## 🏗️ Architecture

```
User (React UI)
      ↓
FastAPI Server (API Gateway equivalent)
      ↓
LangGraph ReAct Agent (Bedrock Agents equivalent)
      ↓ ↓ ↓ ↓ ↓
   Tools:
   🔍 search_kb          — ChromaDB vector search (Bedrock Knowledge Base)
   🎫 create_ticket      — SQLite ticket store (DynamoDB)
   📋 get_ticket_status  — Ticket lookup
   📂 list_my_tickets    — Customer ticket history
   🚨 escalate_to_human  — Human handoff (SES email)
```

## 🤖 Agent Capabilities

| Capability | Description |
|-----------|-------------|
| **Issue Classification** | Automatically categorizes billing, technical, account issues |
| **Knowledge Base Search** | Semantic search over FAQ, policies, troubleshooting docs |
| **Ticket Management** | Create, retrieve, list support tickets |
| **Human Escalation** | Routes complex/urgent cases to human agents |
| **Multi-turn Conversation** | Maintains full conversation context |

## 🚀 Running Locally

### Backend
```bash
cd backend
source venv/bin/activate
python main.py
# API running at http://localhost:8000
```

### Frontend
```bash
cd frontend
npm run dev
# UI running at http://localhost:5173
```

## 🌩️ AWS Production Architecture

| Local | AWS Equivalent |
|-------|---------------|
| FastAPI | API Gateway + Lambda |
| Groq LLaMA 3 | Amazon Bedrock (Claude 3.5) |
| ChromaDB | Bedrock Knowledge Bases + OpenSearch |
| SQLite | Amazon DynamoDB |
| Console mock | Amazon SES |
| Local server | AWS App Runner / ECS |

## 📁 Project Structure

```
support-agent/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── agent.py             # LangGraph ReAct agent + tools
│   ├── database.py          # SQLite ticket store
│   └── knowledge_base/
│       ├── vector_store.py  # ChromaDB semantic search
│       └── docs/            # FAQ, policies, troubleshooting
├── frontend/
│   └── src/
│       ├── App.jsx          # React chat UI
│       └── index.css        # Styling
└── README.md
```

## 🎯 Demo Scenarios

1. **KB Answer**: "How do I reset my password?" → Agent searches KB, answers directly
2. **Ticket Creation**: "I can't access my account, email: user@test.com" → Creates ticket
3. **Escalation**: "This is urgent, I've been charged $500 wrongly" → Escalates to human
4. **Ticket Lookup**: "What's the status of ticket #ABC123?" → Retrieves from DB
5. **Multi-turn**: Complex billing dispute across multiple messages
