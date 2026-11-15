import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

function App() {
  return <main><h1>Remote Robot Cell</h1><p>Phase 1 operator UI skeleton. Cloud API status will appear here in Phase 3.</p></main>;
}
createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);
