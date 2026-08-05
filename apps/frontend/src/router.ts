export type AppPath = "/" | "/chat";

export function normalizePath(pathname: string): AppPath {
  const path = pathname.replace(/\/+$/, "") || "/";
  return path === "/chat" ? "/chat" : "/";
}

export function navigate(path: AppPath): void {
  if (normalizePath(window.location.pathname) === path) {
    return;
  }
  window.history.pushState({}, "", path);
  window.dispatchEvent(new PopStateEvent("popstate"));
}
