export type RAGSource = {
  title: string;
  url: string;
  source: string;
  thumbnail_url?: string | null;
};

export type RAGResponse = {
  answer: string;
  sources: RAGSource[];
  request_id: string;
  trace_id: string;
  retrieval_ms: number;
  generation_ms: number;
  total_ms: number;
};

export type CategoryCount = {
  category: string;
  count: number;
};

export type CategoriesResponse = {
  categories: CategoryCount[];
};

export type DocumentSummary = {
  id: string;
  title: string;
  url: string;
  source: string;
  published_at: string | null;
  category: string | null;
  summary: string | null;
  image_url: string | null;
};

export type DocumentsResponse = {
  documents: DocumentSummary[];
  limit: number;
  offset: number;
  total: number;
};

export type ApiMode = "mock" | "real";
