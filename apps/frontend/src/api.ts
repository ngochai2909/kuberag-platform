import type {
  ApiMode,
  CategoriesResponse,
  DocumentsResponse,
  RAGResponse,
} from "./types";
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

const MOCK_DOCUMENTS: DocumentsResponse["documents"] = [
  {
    id: "11111111-1111-1111-1111-111111111111",
    title: "Google triển khai AI Agent cho người dùng Việt Nam",
    url: "https://vnexpress.net/google-ai-agent-1.html",
    source: "vnexpress",
    published_at: "2026-08-05T08:00:00+00:00",
    category: "khoa-hoc-cong-nghe",
    summary: "Google mở rộng trợ lý AI tại Việt Nam với nhiều tính năng mới.",
    image_url:
      "https://i1-vnexpress.vnecdn.net/2026/07/29/VNEMine-1785320066-8603-1785320131.jpg?w=1200&h=0&q=100&dpr=1&fit=crop&s=yB9jGFPz57fJNcx5tQCGGg",
  },
  {
    id: "22222222-2222-2222-2222-222222222222",
    title: "Người Việt dành hàng trăm triệu giờ cho ứng dụng AI",
    url: "https://vnexpress.net/ai-usage-2.html",
    source: "vnexpress",
    published_at: "2026-08-04T11:30:00+00:00",
    category: "khoa-hoc-cong-nghe",
    summary: "Thống kê cho thấy mức độ sử dụng AI tăng nhanh trong năm qua.",
    image_url: null,
  },
  {
    id: "33333333-3333-3333-3333-333333333333",
    title: "Đội tuyển Việt Nam chuẩn bị cho vòng loại",
    url: "https://vnexpress.net/the-thao-3.html",
    source: "vnexpress",
    published_at: "2026-08-03T15:00:00+00:00",
    category: "the-thao",
    summary: "HLV công bố danh sách sơ bộ trước trận đấu quan trọng.",
    image_url: null,
  },
  {
    id: "44444444-4444-4444-4444-444444444444",
    title: "Thị trường bất động sản quý này",
    url: "https://vnexpress.net/bat-dong-san-4.html",
    source: "vnexpress",
    published_at: "2026-08-02T09:00:00+00:00",
    category: "bat-dong-san",
    summary: "Giá và thanh khoản biến động theo từng phân khúc.",
    image_url: null,
  },
];

function mockResponse(question: string): RAGResponse {
  const requestId = createClientId();
  return {
    answer: `Dựa trên các bài VnExpress đã được nạp, câu hỏi "${question}" có thể được trả lời từ những nguồn bên dưới.`,
    sources: MOCK_DOCUMENTS.slice(0, 5).map((document) => ({
      title: document.title,
      source: document.source,
      url: document.url,
      thumbnail_url: document.image_url,
    })),
    request_id: requestId,
    trace_id: `mock-${requestId.slice(0, 8)}`,
    retrieval_ms: 48,
    generation_ms: 812,
    total_ms: 860,
  };
}

function mockCategories(): CategoriesResponse {
  const counts = new Map<string, number>();
  for (const document of MOCK_DOCUMENTS) {
    if (!document.category) {
      continue;
    }
    counts.set(document.category, (counts.get(document.category) ?? 0) + 1);
  }
  return {
    categories: [...counts.entries()].map(([category, count]) => ({ category, count })),
  };
}

function mockDocuments(params: {
  category?: string;
  limit: number;
  offset: number;
}): DocumentsResponse {
  const filtered = MOCK_DOCUMENTS.filter(
    (document) => !params.category || document.category === params.category,
  );
  return {
    documents: filtered.slice(params.offset, params.offset + params.limit),
    limit: params.limit,
    offset: params.offset,
    total: filtered.length,
  };
}

async function handleApiError(response: Response): Promise<never> {
  if (response.status === 429) {
    throw new RAGApiError("Hệ thống đang nhận nhiều yêu cầu. Vui lòng thử lại sau.", 429);
  }
  if (response.status === 401) {
    throw new RAGApiError("API chưa được cấu hình xác thực cho trình duyệt.", 401);
  }
  throw new RAGApiError("Không thể nhận phản hồi từ KubeRAG.", response.status);
}

export async function queryRag(question: string): Promise<RAGResponse> {
  if (mode === "mock") {
    await new Promise((resolve) => window.setTimeout(resolve, 850));
    return mockResponse(question);
  }

  const response = await fetch(`${baseUrl}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, top_k: 5 }),
  });

  if (!response.ok) {
    await handleApiError(response);
  }

  return (await response.json()) as RAGResponse;
}

export async function listCategories(): Promise<CategoriesResponse> {
  if (mode === "mock") {
    await new Promise((resolve) => window.setTimeout(resolve, 200));
    return mockCategories();
  }

  const response = await fetch(`${baseUrl}/categories`);
  if (!response.ok) {
    await handleApiError(response);
  }
  return (await response.json()) as CategoriesResponse;
}

export async function listDocuments(options?: {
  category?: string;
  limit?: number;
  offset?: number;
}): Promise<DocumentsResponse> {
  const limit = options?.limit ?? 24;
  const offset = options?.offset ?? 0;

  if (mode === "mock") {
    await new Promise((resolve) => window.setTimeout(resolve, 250));
    return mockDocuments({ category: options?.category, limit, offset });
  }

  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  if (options?.category) {
    params.set("category", options.category);
  }

  const response = await fetch(`${baseUrl}/documents?${params.toString()}`);
  if (!response.ok) {
    await handleApiError(response);
  }
  return (await response.json()) as DocumentsResponse;
}

export function getApiMode(): ApiMode {
  return mode;
}
