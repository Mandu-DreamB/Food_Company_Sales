import { Route, Routes } from "react-router-dom";
import "./App.css";
import { Sidebar } from "./components/Sidebar";
import { SourcesProvider } from "./context/SourcesContext";
import { Dashboard } from "./pages/Dashboard";
import { IndicatorDetail } from "./pages/IndicatorDetail";

function App() {
  return (
    <SourcesProvider>
      <Sidebar />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/indicator/:id" element={<IndicatorDetail />} />
        </Routes>
      </main>
    </SourcesProvider>
  );
}

export default App;
