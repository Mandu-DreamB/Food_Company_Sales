const RAG_BASE_URL = import.meta.env.VITE_RAG_API_BASE_URL ?? "http://localhost:8001";

export async function askChatbot(question: string): Promise<string> {
  const res = await fetch(`${RAG_BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) throw new Error(`챗봇 응답을 받지 못했습니다 (${res.status})`);
  const data: { answer: string } = await res.json();
  return data.answer;
}
