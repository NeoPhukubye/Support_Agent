from langchain_core.tools import tool

from knowledge_base.vector_store import search_knowledge_base


@tool
def search_kb(query: str) -> str:
    """Search the support knowledge base for answers to customer questions about
    billing, technical issues, account management, features, policies,
    and troubleshooting."""
    results = search_knowledge_base(query)
    if not results:
        return "No relevant information found in the knowledge base."
    return "\n\n---\n".join(f"[{r['source']}]\n{r['content']}" for r in results)
