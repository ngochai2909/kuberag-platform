import { useEffect, useState } from "react";

import { Layout } from "./Layout";
import { listCategories, listDocuments, RAGApiError } from "./api";
import type { AppPath } from "./router";
import type { CategoryCount, DocumentSummary } from "./types";

const PAGE_SIZE = 24;

/** Display order aligned with VnExpress DEFAULT_FEEDS (tin mới nhất before tin xem nhiều). */
const CATEGORY_ORDER: readonly string[] = [
  "tin-moi-nhat",
  "tin-noi-bat",
  "thoi-su",
  "the-gioi",
  "kinh-doanh",
  "bat-dong-san",
  "khoa-hoc-cong-nghe",
  "giai-tri",
  "the-thao",
  "phap-luat",
  "giao-duc",
  "suc-khoe",
  "doi-song",
  "du-lich",
  "oto-xe-may",
  "y-kien",
  "tam-su",
  "cuoi",
  "tin-xem-nhieu",
];

const CATEGORY_LABELS: Record<string, string> = {
  "tin-moi-nhat": "Tin mới nhất",
  "tin-noi-bat": "Tin nổi bật",
  "thoi-su": "Thời sự",
  "the-gioi": "Thế giới",
  "kinh-doanh": "Kinh doanh",
  "bat-dong-san": "Bất động sản",
  "khoa-hoc-cong-nghe": "Khoa học công nghệ",
  "giai-tri": "Giải trí",
  "the-thao": "Thể thao",
  "phap-luat": "Pháp luật",
  "giao-duc": "Giáo dục",
  "suc-khoe": "Sức khỏe",
  "doi-song": "Đời sống",
  "du-lich": "Du lịch",
  "oto-xe-may": "Xe",
  "y-kien": "Ý kiến",
  "tam-su": "Tâm sự",
  cuoi: "Cười",
  "tin-xem-nhieu": "Tin xem nhiều",
};

function categoryRank(category: string): number {
  const index = CATEGORY_ORDER.indexOf(category);
  return index === -1 ? CATEGORY_ORDER.length : index;
}

function sortCategories(categories: CategoryCount[]): CategoryCount[] {
  return [...categories].sort((left, right) => {
    const rankDiff = categoryRank(left.category) - categoryRank(right.category);
    if (rankDiff !== 0) {
      return rankDiff;
    }
    return left.category.localeCompare(right.category);
  });
}

function categoryLabel(category: string): string {
  return CATEGORY_LABELS[category] ?? category;
}

function formatPublishedAt(value: string | null): string | null {
    if (!value) {
        return null;
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return null;
    }
    return new Intl.DateTimeFormat("vi-VN", {
        dateStyle: "medium",
        timeStyle: "short",
    }).format(date);
}

export function NewsPage({ path }: { path: AppPath }) {
    const [categories, setCategories] = useState<CategoryCount[]>([]);
    const [selectedCategory, setSelectedCategory] = useState<string | null>(
        null,
    );
    const [documents, setDocuments] = useState<DocumentSummary[]>([]);
    const [total, setTotal] = useState(0);
    const [isLoading, setIsLoading] = useState(true);
    const [isLoadingMore, setIsLoadingMore] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let cancelled = false;
        async function loadCategories() {
            try {
                const response = await listCategories();
                if (!cancelled) {
                    setCategories(sortCategories(response.categories));
                }
            } catch (caught) {
                if (!cancelled) {
                    const message =
                        caught instanceof RAGApiError
                            ? caught.message
                            : "Không tải được danh mục.";
                    setError(message);
                }
            }
        }
        void loadCategories();
        return () => {
            cancelled = true;
        };
    }, []);

    useEffect(() => {
        let cancelled = false;
        async function loadDocuments() {
            setIsLoading(true);
            setError(null);
            try {
                const response = await listDocuments({
                    category: selectedCategory ?? undefined,
                    limit: PAGE_SIZE,
                    offset: 0,
                });
                if (!cancelled) {
                    setDocuments(response.documents);
                    setTotal(response.total);
                }
            } catch (caught) {
                if (!cancelled) {
                    const message =
                        caught instanceof RAGApiError
                            ? caught.message
                            : "Không tải được danh sách tin.";
                    setError(message);
                    setDocuments([]);
                    setTotal(0);
                }
            } finally {
                if (!cancelled) {
                    setIsLoading(false);
                }
            }
        }
        void loadDocuments();
        return () => {
            cancelled = true;
        };
    }, [selectedCategory]);

    async function loadMore() {
        if (isLoadingMore || documents.length >= total) {
            return;
        }
        setIsLoadingMore(true);
        setError(null);
        try {
            const response = await listDocuments({
                category: selectedCategory ?? undefined,
                limit: PAGE_SIZE,
                offset: documents.length,
            });
            setDocuments((current) => [...current, ...response.documents]);
            setTotal(response.total);
        } catch (caught) {
            const message =
                caught instanceof RAGApiError
                    ? caught.message
                    : "Không tải thêm được tin.";
            setError(message);
        } finally {
            setIsLoadingMore(false);
        }
    }

    return (
        <Layout path={path} subtitle="VnExpress Crawler">
            <main className="news-shell">
                <section className="news-panel" aria-label="Tin đã nạp">
                    <div className="news-intro">
                        <h2>Tin Tức</h2>
                        <p>Chọn chuyên mục, mở bài trên VnExpress gốc.</p>
                    </div>

                    <div
                        className="category-chips"
                        role="tablist"
                        aria-label="Chuyên mục"
                    >
                        <button
                            type="button"
                            role="tab"
                            aria-selected={selectedCategory === null}
                            className={
                                selectedCategory === null
                                    ? "category-chip active"
                                    : "category-chip"
                            }
                            onClick={() => setSelectedCategory(null)}
                        >
                            Tất cả
                        </button>
                        {categories.map((item) => (
                            <button
                                key={item.category}
                                type="button"
                                role="tab"
                                aria-selected={
                                    selectedCategory === item.category
                                }
                                className={
                                    selectedCategory === item.category
                                        ? "category-chip active"
                                        : "category-chip"
                                }
                                onClick={() =>
                                    setSelectedCategory(item.category)
                                }
                            >
                                {categoryLabel(item.category)}
                                <span className="category-count">
                                    {item.count}
                                </span>
                            </button>
                        ))}
                    </div>

                    {error ? (
                        <p className="error-state" role="alert">
                            {error}
                        </p>
                    ) : null}

                    {isLoading ? (
                        <p className="news-status">Đang tải tin...</p>
                    ) : documents.length === 0 ? (
                        <p className="news-status">
                            Chưa có bài trong chuyên mục này.
                        </p>
                    ) : (
                        <>
                            <ul className="news-grid">
                                {documents.map((document) => {
                                    const published = formatPublishedAt(
                                        document.published_at,
                                    );
                                    return (
                                        <li key={document.id}>
                                            <a
                                                className="news-card"
                                                href={document.url}
                                                target="_blank"
                                                rel="noreferrer"
                                            >
                                                {document.image_url ? (
                                                    <img
                                                        className="news-card-image"
                                                        src={document.image_url}
                                                        alt=""
                                                        loading="lazy"
                                                        referrerPolicy="no-referrer"
                                                        onError={(event) => {
                                                            event.currentTarget.hidden = true;
                                                        }}
                                                    />
                                                ) : (
                                                    <span
                                                        className="news-card-image news-card-image-fallback"
                                                        aria-hidden="true"
                                                    />
                                                )}
                                                <div className="news-card-body">
                                                    <div className="news-card-meta">
                                                        {document.category ? (
                                                            <span className="news-card-category">
                                                                {categoryLabel(
                                                                    document.category,
                                                                )}
                                                            </span>
                                                        ) : null}
                                                        {published ? (
                                                            <time
                                                                dateTime={
                                                                    document.published_at ??
                                                                    undefined
                                                                }
                                                            >
                                                                {published}
                                                            </time>
                                                        ) : null}
                                                    </div>
                                                    <h3 className="news-card-title">
                                                        {document.title}
                                                    </h3>
                                                    {document.summary ? (
                                                        <p className="news-card-summary">
                                                            {document.summary}
                                                        </p>
                                                    ) : null}
                                                    <span className="news-card-cta">
                                                        Mở trên VnExpress
                                                    </span>
                                                </div>
                                            </a>
                                        </li>
                                    );
                                })}
                            </ul>

                            {documents.length < total ? (
                                <div className="news-load-more">
                                    <button
                                        type="button"
                                        onClick={() => void loadMore()}
                                        disabled={isLoadingMore}
                                    >
                                        {isLoadingMore
                                            ? "Đang tải..."
                                            : `Tải thêm (${documents.length}/${total})`}
                                    </button>
                                </div>
                            ) : (
                                <p className="news-status">
                                    Hiển thị {documents.length}/{total} bài
                                </p>
                            )}
                        </>
                    )}
                </section>
            </main>
        </Layout>
    );
}
