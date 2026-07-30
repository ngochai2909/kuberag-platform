import { FormEvent, KeyboardEvent, useEffect, useState } from "react";

import { getApiMode, queryRag, RAGApiError } from "./api";
import { createClientId } from "./ids";
import type { RAGResponse, RAGSource } from "./types";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  response?: RAGResponse;
};

const suggestedQuestions = [
  "Công nghệ nào đang được VnExpress đề cập gần đây?",
  "Nguồn tin trong hệ thống đến từ đâu?",
  "Tóm tắt các chủ đề khoa học nổi bật.",
];

function SourceList({ sources }: { sources: RAGSource[] }) {
  if (sources.length === 0) {
    return <p className="muted">Chưa có nguồn nào trong phiên này.</p>;
  }

  return (
    <ul className="source-list">
      {sources.map((source) => (
        <li className="source-card" key={source.url}>
          {source.thumbnail_url ? (
            <img
              className="source-thumbnail"
              src={source.thumbnail_url}
              alt=""
              loading="lazy"
              referrerPolicy="no-referrer"
              onError={(event) => {
                event.currentTarget.hidden = true;
              }}
            />
          ) : null}
          <div className="source-copy">
            <span className="source-name">{source.source}</span>
            <a href={source.url} target="_blank" rel="noreferrer">
              {source.title}
            </a>
          </div>
        </li>
      ))}
    </ul>
  );
}

function AnswerMeta({ response }: { response: RAGResponse }) {
  return (
    <div className="answer-details">
      <dl className="answer-meta">
        <div>
          <dt>Tổng thời gian</dt>
          <dd>{response.total_ms} ms</dd>
        </div>
      </dl>
      <details className="technical-details">
        <summary>Chi tiết xử lý</summary>
        <dl className="technical-meta">
          <div>
            <dt>Truy xuất</dt>
            <dd>{response.retrieval_ms} ms</dd>
          </div>
          <div>
            <dt>Sinh câu trả lời</dt>
            <dd>{response.generation_ms} ms</dd>
          </div>
          <div>
            <dt>Request ID</dt>
            <dd>{response.request_id}</dd>
          </div>
          <div>
            <dt>Trace ID</dt>
            <dd>{response.trace_id}</dd>
          </div>
        </dl>
      </details>
    </div>
  );
}

export default function App() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    return window.localStorage.getItem("kuberag-theme") === "dark" ? "dark" : "light";
  });

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("kuberag-theme", theme);
  }, [theme]);

  const latestSources = [...messages]
    .reverse()
    .find((message) => message.response)?.response?.sources ?? [];

  async function submitQuestion(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    const normalizedQuestion = question.trim();
    if (!normalizedQuestion || isLoading) {
      return;
    }

    setError(null);
    setQuestion("");
    setMessages((current) => [
      ...current,
      { id: createClientId(), role: "user", content: normalizedQuestion },
    ]);
    setIsLoading(true);

    try {
      const response = await queryRag(normalizedQuestion);
      setMessages((current) => [
        ...current,
        { id: createClientId(), role: "assistant", content: response.answer, response },
      ]);
    } catch (caught) {
      const message = caught instanceof RAGApiError ? caught.message : "Đã có lỗi không xác định.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }

  function handleComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void submitQuestion();
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">RAG workspace</p>
          <h1>KubeRAG</h1>
        </div>
        <div className="header-actions">
          <div className="runtime-status" aria-label="API mode">
            <span className="status-dot" />
            {getApiMode() === "mock" ? "Mock mode" : "API mode"}
          </div>
          <button
            className="theme-toggle"
            type="button"
            onClick={() => setTheme((current) => (current === "light" ? "dark" : "light"))}
            aria-label="Chuyển chế độ sáng tối"
            title="Chuyển chế độ sáng tối"
          >
            <span className="theme-icon" aria-hidden="true" />
          </button>
        </div>
      </header>

      <div className="workspace">
        <section className="conversation" aria-label="KubeRAG conversation">
          <div className="conversation-heading">
            <div>
              <p className="eyebrow">VnExpress RSS</p>
              <h2>Hỏi đáp theo nguồn đã truy xuất</h2>
            </div>
          </div>

          {messages.length === 0 ? (
            <div className="empty-state">
              <p>Chọn một câu hỏi hoặc nhập câu hỏi của bạn.</p>
              <div className="question-list">
                {suggestedQuestions.map((suggestion) => (
                  <button key={suggestion} type="button" onClick={() => setQuestion(suggestion)}>
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="message-list">
              {messages.map((message) => (
                <article className={`message ${message.role}`} key={message.id}>
                  <p className="message-label">{message.role === "user" ? "Bạn" : "KubeRAG"}</p>
                  <p className="message-content">{message.content}</p>
                  {message.response ? <AnswerMeta response={message.response} /> : null}
                </article>
              ))}
              {isLoading ? (
                <article className="message assistant loading" aria-live="polite">
                  <p className="message-label">KubeRAG</p>
                  <p className="message-content">Đang truy xuất nguồn và tạo câu trả lời...</p>
                </article>
              ) : null}
            </div>
          )}

          {error ? <p className="error-state" role="alert">{error}</p> : null}

          <form className="composer" onSubmit={submitQuestion}>
            <label htmlFor="question">Câu hỏi</label>
            <textarea
              id="question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={handleComposerKeyDown}
              placeholder="Nhập câu hỏi về nội dung VnExpress..."
              rows={3}
              disabled={isLoading}
            />
            <button type="submit" disabled={isLoading || !question.trim()}>
              {isLoading ? "Đang xử lý" : "Gửi"}
            </button>
          </form>
        </section>

        <aside className="sources-panel" aria-label="Nguồn tham khảo">
          <p className="eyebrow">Evidence</p>
          <h2>Nguồn tham khảo</h2>
          <SourceList sources={latestSources} />
        </aside>
      </div>
    </main>
  );
}
