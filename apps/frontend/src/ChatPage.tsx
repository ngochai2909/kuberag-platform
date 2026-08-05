import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";

import { BrandMark } from "./BrandMark";
import { Layout } from "./Layout";
import { queryRag, RAGApiError } from "./api";
import { createClientId } from "./ids";
import type { AppPath } from "./router";
import type { RAGResponse, RAGSource } from "./types";

type Message = {
    id: string;
    role: "user" | "assistant";
    content: string;
    response?: RAGResponse;
};

const suggestedQuestions = [
    "Tin công nghệ nổi bật gần đây là gì?",
    "Xu hướng AI mới nhất hiện nay?",
    "Hãy cho tôi tin tức về Google",
];

function SourceList({ sources }: { sources: RAGSource[] }) {
    if (sources.length === 0) {
        return null;
    }

    return (
        <div className="inline-sources">
            <p className="inline-sources-label">Nguồn</p>
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
                        ) : (
                            <span
                                className="source-thumbnail source-thumbnail-fallback"
                                aria-hidden="true"
                            />
                        )}
                        <div className="source-copy">
                            <span className="source-name">{source.source}</span>
                            <a
                                href={source.url}
                                target="_blank"
                                rel="noreferrer"
                            >
                                {source.title}
                            </a>
                        </div>
                    </li>
                ))}
            </ul>
        </div>
    );
}

function AnswerMeta({ response }: { response: RAGResponse }) {
    return (
        <div className="answer-details">
            <p className="latency-chip">{response.total_ms} ms</p>
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

export function ChatPage({ path }: { path: AppPath }) {
    const [question, setQuestion] = useState("");
    const [messages, setMessages] = useState<Message[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const threadRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const node = threadRef.current;
        if (!node) {
            return;
        }
        node.scrollTop = node.scrollHeight;
    }, [messages, isLoading, error]);

    async function ask(rawQuestion: string) {
        const normalizedQuestion = rawQuestion.trim();
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
                {
                    id: createClientId(),
                    role: "assistant",
                    content: response.answer,
                    response,
                },
            ]);
        } catch (caught) {
            const message =
                caught instanceof RAGApiError
                    ? caught.message
                    : "Đã có lỗi không xác định.";
            setError(message);
        } finally {
            setIsLoading(false);
        }
    }

    async function submitQuestion(event?: FormEvent<HTMLFormElement>) {
        event?.preventDefault();
        await ask(question);
    }

    function handleComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            void ask(question);
        }
    }

    function clearChat() {
        if (isLoading) {
            return;
        }
        setMessages([]);
        setError(null);
        setQuestion("");
    }

    return (
        <Layout
            path={path}
            subtitle="Hỏi đáp tin VnExpress"
            actions={
                messages.length > 0 ? (
                    <>
                        <span className="header-divider" aria-hidden="true" />
                        <button
                            className="ghost-button"
                            type="button"
                            onClick={clearChat}
                            disabled={isLoading}
                        >
                            Hội thoại mới
                        </button>
                    </>
                ) : null
            }
        >
            <main className="chat-shell">
                <section className="chat-panel" aria-label="KubeRAG chat">
                    <div className="chat-thread" ref={threadRef}>
                        {messages.length === 0 ? (
                            <div className="empty-state">
                                <h2>Bắt đầu hội thoại</h2>
                                <p>Tìm và hỏi đáp thông tin bài báo</p>
                            </div>
                        ) : (
                            <div
                                className="message-list"
                                role="log"
                                aria-live="polite"
                            >
                                {messages.map((message) => (
                                    <article
                                        className={`message ${message.role}`}
                                        key={message.id}
                                    >
                                        {message.role === "assistant" ? (
                                            <div
                                                className="assistant-avatar"
                                                aria-hidden="true"
                                            >
                                                <BrandMark />
                                            </div>
                                        ) : null}
                                        <div className="message-stack">
                                            <p className="message-label">
                                                {message.role === "user"
                                                    ? "Bạn"
                                                    : "KubeRAG"}
                                            </p>
                                            <div className="message-bubble">
                                                <p className="message-content">
                                                    {message.content}
                                                </p>
                                                {message.response ? (
                                                    <>
                                                        <SourceList
                                                            sources={
                                                                message.response
                                                                    .sources
                                                            }
                                                        />
                                                        <AnswerMeta
                                                            response={
                                                                message.response
                                                            }
                                                        />
                                                    </>
                                                ) : null}
                                            </div>
                                        </div>
                                    </article>
                                ))}
                                {isLoading ? (
                                    <article className="message assistant loading">
                                        <div
                                            className="assistant-avatar"
                                            aria-hidden="true"
                                        >
                                            <BrandMark />
                                        </div>
                                        <div className="message-stack">
                                            <p className="message-label">
                                                KubeRAG
                                            </p>
                                            <div className="message-bubble">
                                                <p className="message-content">
                                                    Đang truy xuất nguồn và tạo
                                                    câu trả lời...
                                                </p>
                                            </div>
                                        </div>
                                    </article>
                                ) : null}
                            </div>
                        )}

                        {error ? (
                            <p className="error-state" role="alert">
                                {error}
                            </p>
                        ) : null}
                    </div>

                    <div className="composer-dock">
                        <div
                            className="question-list"
                            aria-label="Câu hỏi gợi ý"
                        >
                            {suggestedQuestions.map((suggestion) => (
                                <button
                                    key={suggestion}
                                    type="button"
                                    disabled={isLoading}
                                    onClick={() => void ask(suggestion)}
                                >
                                    {suggestion}
                                </button>
                            ))}
                        </div>

                        <form className="composer" onSubmit={submitQuestion}>
                            <label
                                className="visually-hidden"
                                htmlFor="question"
                            >
                                Câu hỏi
                            </label>
                            <textarea
                                id="question"
                                value={question}
                                onChange={(event) =>
                                    setQuestion(event.target.value)
                                }
                                onKeyDown={handleComposerKeyDown}
                                placeholder="Nhập câu hỏi về nội dung VnExpress..."
                                rows={2}
                                disabled={isLoading}
                            />
                            <button
                                type="submit"
                                disabled={isLoading || !question.trim()}
                            >
                                {isLoading ? "Đang xử lý" : "Gửi"}
                            </button>
                        </form>
                    </div>
                </section>
            </main>
        </Layout>
    );
}
