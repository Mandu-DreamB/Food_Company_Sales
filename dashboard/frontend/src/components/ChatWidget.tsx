import { useRef, useState, type FormEvent } from "react";
import { askChatbot } from "../api/ragClient";

interface Message {
  role: "user" | "bot";
  text: string;
  at: Date;
}

const QUICK_REPLIES = ["삼양패키징 대표이사가 누구야?", "삼양사 계열회사 목록 알려줘", "삼양이노켐 매출실적 알려줘"];

const timeLabel = (d: Date) =>
  new Intl.DateTimeFormat("ko-KR", { hour: "numeric", minute: "2-digit", hour12: true }).format(d);

function ChatBubbleIcon() {
  return (
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M4 5.5C4 4.67 4.67 4 5.5 4h13c.83 0 1.5.67 1.5 1.5v9c0 .83-.67 1.5-1.5 1.5H9l-4 4v-4H5.5C4.67 15.5 4 14.83 4 14v-8.5Z"
        stroke="white"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function ChevronIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M6 9l6 6 6-6" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function SendIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M4 12l16-8-6 8 6 8-16-8Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
    </svg>
  );
}

export function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    requestAnimationFrame(() => {
      listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
    });
  };

  const sendQuestion = (question: string) => {
    if (!question || sending) return;

    setMessages((prev) => [...prev, { role: "user", text: question, at: new Date() }]);
    setInput("");
    setSending(true);
    scrollToBottom();

    askChatbot(question)
      .then((answer) => {
        setMessages((prev) => [...prev, { role: "bot", text: answer, at: new Date() }]);
      })
      .catch((err) => {
        setMessages((prev) => [...prev, { role: "bot", text: `오류: ${err.message}`, at: new Date() }]);
      })
      .finally(() => {
        setSending(false);
        scrollToBottom();
      });
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    sendQuestion(input.trim());
  };

  return (
    <div className="chat-widget">
      <div className={`chat-panel${open ? " chat-panel-open" : ""}`}>
        <div className="chat-panel-header">
          <div className="chat-panel-avatar">삼</div>
          <div className="chat-panel-heading">
            <div className="chat-panel-title">삼양그룹 계열사 챗봇</div>
            <div className="chat-panel-subtitle">공시 문서를 바탕으로 답변해 드려요</div>
          </div>
          <button className="chat-collapse" onClick={() => setOpen(false)} aria-label="챗봇 접기">
            <ChevronIcon />
          </button>
        </div>

        <div className="chat-messages" ref={listRef}>
          {messages.length === 0 && (
            <>
              <div className="chat-empty">
                계열사 공시(사업보고서 등)에 대해 물어보세요. 예시 질문을 눌러보세요.
              </div>
              <div className="chat-quick-replies">
                {QUICK_REPLIES.map((q) => (
                  <button key={q} type="button" className="chat-quick-reply" onClick={() => sendQuestion(q)}>
                    {q}
                  </button>
                ))}
              </div>
            </>
          )}

          {messages.map((m, i) => (
            <div key={i} className={`chat-row chat-row-${m.role}`}>
              {m.role === "bot" && <div className="chat-avatar">삼</div>}
              <div className="chat-bubble-col">
                {m.role === "bot" && <div className="chat-sender">삼양 챗봇</div>}
                <div className={`chat-bubble chat-bubble-${m.role}`}>{m.text}</div>
                <div className="chat-timestamp">{timeLabel(m.at)}</div>
              </div>
            </div>
          ))}

          {sending && (
            <div className="chat-row chat-row-bot">
              <div className="chat-avatar">삼</div>
              <div className="chat-bubble-col">
                <div className="chat-sender">삼양 챗봇</div>
                <div className="chat-bubble chat-bubble-bot chat-bubble-loading">
                  <span className="chat-typing-dot" />
                  <span className="chat-typing-dot" />
                  <span className="chat-typing-dot" />
                </div>
              </div>
            </div>
          )}
        </div>

        <form className="chat-input-row" onSubmit={handleSubmit}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="메시지 입력"
            disabled={sending}
          />
          <button type="submit" disabled={sending || !input.trim()} aria-label="전송">
            <SendIcon />
          </button>
        </form>
      </div>

      <button
        className={`chat-toggle${open ? " chat-toggle-open" : ""}`}
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? "챗봇 접기" : "챗봇 열기"}
      >
        <span className="chat-toggle-icon chat-toggle-icon-bubble">
          <ChatBubbleIcon />
        </span>
        <span className="chat-toggle-icon chat-toggle-icon-chevron">
          <ChevronIcon />
        </span>
      </button>
    </div>
  );
}
