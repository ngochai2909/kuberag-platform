import { ReactNode, useEffect, useState } from "react";

import { BrandMark } from "./BrandMark";
import { AppPath, navigate, normalizePath } from "./router";

type LayoutProps = {
  path: AppPath;
  children: ReactNode;
  subtitle: string;
  actions?: ReactNode;
};

export function Layout({ path, children, subtitle, actions }: LayoutProps) {
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    return window.localStorage.getItem("kuberag-theme") === "dark" ? "dark" : "light";
  });

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("kuberag-theme", theme);
    document.querySelector('meta[name="theme-color"]')?.setAttribute(
      "content",
      theme === "dark" ? "#152028" : "#eef5f4",
    );
  }, [theme]);

  return (
    <div className="app-shell">
      <div className="atmosphere" aria-hidden="true" />

      <header className="app-topbar">
        <div className="brand-block">
          <BrandMark />
          <div>
            <h1 className="brand-title">
              <span className="brand-kube">Kube</span>
              <span className="brand-rag">RAG</span>
            </h1>
            <p className="brand-subtitle">{subtitle}</p>
          </div>
        </div>

        <nav className="primary-nav" aria-label="Điều hướng chính">
          <button
            type="button"
            className={path === "/" ? "nav-link active" : "nav-link"}
            aria-current={path === "/" ? "page" : undefined}
            onClick={() => navigate("/")}
          >
            Tin
          </button>
          <button
            type="button"
            className={path === "/chat" ? "nav-link active" : "nav-link"}
            aria-current={path === "/chat" ? "page" : undefined}
            onClick={() => navigate("/chat")}
          >
            Chat
          </button>
        </nav>

        <div className="header-actions">
          {actions}
          <button
            className={`theme-toggle theme-${theme}`}
            type="button"
            onClick={() => setTheme((current) => (current === "light" ? "dark" : "light"))}
            aria-label="Chuyển chế độ sáng tối"
            title="Chuyển chế độ sáng tối"
          >
            <span className="theme-knob" aria-hidden="true" />
          </button>
        </div>
      </header>

      {children}
    </div>
  );
}

export function useAppPath(): AppPath {
  const [path, setPath] = useState<AppPath>(() => normalizePath(window.location.pathname));

  useEffect(() => {
    function onPopState() {
      setPath(normalizePath(window.location.pathname));
    }
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  return path;
}
