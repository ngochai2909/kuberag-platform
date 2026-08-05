import { ChatPage } from "./ChatPage";
import { NewsPage } from "./NewsPage";
import { useAppPath } from "./Layout";

export default function AppRouter() {
  const path = useAppPath();

  if (path === "/chat") {
    return <ChatPage path={path} />;
  }

  return <NewsPage path={path} />;
}
