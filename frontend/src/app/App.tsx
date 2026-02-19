import "../polyfills";
import { Suspense } from "react";
import { RouterProvider } from "react-router";
import { router } from "./routes";
import { ThemeProvider } from "next-themes";
import { ArchiveNodeProvider } from "../context/archive-node-context";

function AppContent() {
  return (
    <ThemeProvider attribute="class" defaultTheme="dark" forcedTheme="dark">
      <ArchiveNodeProvider>
      <Suspense
        fallback={
          <div
            style={{
              minHeight: "100vh",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              background: "#18181b",
              color: "#a1a1aa",
            }}
          >
            Loading…
          </div>
        }
      >
        <RouterProvider router={router} />
      </Suspense>
      </ArchiveNodeProvider>
    </ThemeProvider>
  );
}

export default function App() {
  return <AppContent />;
}