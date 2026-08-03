import type { ApiMode, RAGResponse } from "./types";
import { createClientId } from "./ids";

export class RAGApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
  }
}

const mode: ApiMode = import.meta.env.VITE_API_MODE === "real" ? "real" : "mock";
const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

function mockResponse(question: string): RAGResponse {
  const requestId = createClientId();
  return {
    answer: `Dựa trên các bài VnExpress đã được nạp, câu hỏi "${question}" có thể được trả lời từ những nguồn bên dưới.`,
    sources: [
      {
        title: "VnExpress - Khoa học công nghệ",
        source: "vnexpress",
        url: "https://vnexpress.net/rss/khoa-hoc-cong-nghe.rss",
        thumbnail_url:
          "https://i1-vnexpress.vnecdn.net/2026/07/29/VNEMine-1785320066-8603-1785320131.jpg?w=1200&h=0&q=100&dpr=1&fit=crop&s=yB9jGFPz57fJNcx5tQCGGg",
      },
      {
        title: "Dữ liệu RAG đã được chunk và lập chỉ mục",
        source: "kuberag",
        url: "https://vnexpress.net/rss/",
      },
    ],
    request_id: requestId,
    trace_id: `mock-${requestId.slice(0, 8)}`,
    retrieval_ms: 48,
    generation_ms: 812,
    total_ms: 860,
  };
}

export async function queryRag(question: string): Promise<RAGResponse> {
  if (mode === "mock") {
    await new Promise((resolve) => window.setTimeout(resolve, 850));
    return mockResponse(question);
  }

  const response = await fetch(`${baseUrl}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, top_k: 3 }),
  });

  if (!response.ok) {
    if (response.status === 429) {
      throw new RAGApiError("Hệ thống đang nhận nhiều yêu cầu. Vui lòng thử lại sau.", 429);
    }
    if (response.status === 401) {
      throw new RAGApiError("API chưa được cấu hình xác thực cho trình duyệt.", 401);
    }
    throw new RAGApiError("Không thể nhận phản hồi từ KubeRAG.", response.status);
  }

  return (await response.json()) as RAGResponse;
}

export function getApiMode(): ApiMode {
  return mode;
}
