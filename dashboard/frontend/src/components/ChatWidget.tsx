import { useRef, useState, type FormEvent, type ReactNode } from "react";
import type { ChartResult } from "../api/types";
import { askChatbot } from "../api/ragClient";

/** 답변 텍스트 + (있으면) 대시보드에 띄울 차트. RAG 챗봇은 텍스트만 준다. */
export interface ChatReply {
  answer: string;
  chart?: ChartResult | null;
}

interface Message {
  role: "user" | "bot";
  text: string;
  at: Date;
}

const QUICK_REPLIES = ["삼양패키징 대표이사가 누구야?", "삼양사 계열회사 목록 알려줘", "삼양이노켐 매출실적 알려줘"];

interface ChatWidgetProps {
  /** 질문을 보낼 함수. 기본값은 공시 RAG 챗봇. */
  ask?: (question: string) => Promise<ChatReply>;
  /** 답변에 차트가 딸려 오면 호출된다 (챗 패널이 좁아서 차트는 페이지 쪽에 그린다). */
  onChart?: (chart: ChartResult) => void;
  title?: string;
  subtitle?: string;
  emptyHint?: string;
  quickReplies?: string[];
  /** 위젯 위치를 옮길 때 쓰는 추가 클래스 (한 화면에 위젯이 둘 이상일 때). */
  className?: string;
  /** 토글 버튼 아이콘. 위젯이 둘이라 아이콘으로 구분한다. */
  icon?: ReactNode;
}

const timeLabel = (d: Date) =>
  new Intl.DateTimeFormat("ko-KR", { hour: "numeric", minute: "2-digit", hour12: true }).format(d);

/** 공시 RAG 챗봇 — 문서를 읽고 답한다는 뜻의 문서 아이콘. */
function DocumentIcon() {
  return (
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M14 3H7a1.5 1.5 0 0 0-1.5 1.5v15A1.5 1.5 0 0 0 7 21h10a1.5 1.5 0 0 0 1.5-1.5V7.5L14 3Z"
        stroke="white"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path d="M13.8 3.2V7.5h4.3" stroke="white" strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M8.8 12h6.4M8.8 15.5h6.4" stroke="white" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

/** 지표 DB 챗봇 — DB를 조회해 차트를 만든다는 뜻의 막대차트 아이콘. */
export function ChartIcon() {
  return (
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M4 20h16" stroke="white" strokeWidth="1.6" strokeLinecap="round" />
      <path
        d="M7 20v-6M12 20V5M17 20v-9"
        stroke="white"
        strokeWidth="1.6"
        strokeLinecap="round"
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

export function ChatWidget({
  ask = (question: string) => askChatbot(question).then((answer) => ({ answer })),
  onChart,
  title = "삼양그룹 계열사 챗봇",
  subtitle = "공시 문서를 바탕으로 답변해 드려요",
  emptyHint = "계열사 공시(사업보고서 등)에 대해 물어보세요. 예시 질문을 눌러보세요.",
  quickReplies = QUICK_REPLIES,
  className = "",
  icon = <DocumentIcon />,
}: ChatWidgetProps = {}) {
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

    ask(question)
      .then((reply) => {
        setMessages((prev) => [...prev, { role: "bot", text: reply.answer, at: new Date() }]);
        if (reply.chart) onChart?.(reply.chart);
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
    <div className={`chat-widget ${className}`.trim()}>
      <div className={`chat-panel${open ? " chat-panel-open" : ""}`}>
        <div className="chat-panel-header">
          <div className="chat-panel-avatar">삼</div>
          <div className="chat-panel-heading">
            <div className="chat-panel-title">{title}</div>
            <div className="chat-panel-subtitle">{subtitle}</div>
          </div>
          <button className="chat-collapse" onClick={() => setOpen(false)} aria-label="챗봇 접기">
            <ChevronIcon />
          </button>
        </div>

        <div className="chat-messages" ref={listRef}>
          {messages.length === 0 && (
            <>
              <div className="chat-empty">{emptyHint}</div>
              <div className="chat-quick-replies">
                {quickReplies.map((q) => (
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
        <span className="chat-toggle-icon chat-toggle-icon-bubble">{icon}</span>
        <span className="chat-toggle-icon chat-toggle-icon-chevron">
          <ChevronIcon />
        </span>
      </button>
    </div>
  );
}
