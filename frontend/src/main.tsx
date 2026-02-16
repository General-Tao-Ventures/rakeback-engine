import { createRoot } from "react-dom/client";
import App from "./app/App.tsx";
import { AppErrorBoundary } from "./app/components/error-boundary";
import "./styles/index.css";

const root = document.getElementById("root");
if (!root) {
  throw new Error("Root element #root not found");
}
createRoot(root).render(
  <AppErrorBoundary>
    <App />
  </AppErrorBoundary>
);
  