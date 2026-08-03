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

export type ApiMode = "mock" | "real";
