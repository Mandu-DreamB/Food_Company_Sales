import { Route, Routes } from "react-router-dom";
import "./App.css";
import { ChatWidget } from "./components/ChatWidget";
import { DashboardLayout } from "./components/DashboardLayout";
import { SourcesProvider } from "./context/SourcesContext";
import { CompanyLanding } from "./pages/CompanyLanding";
import { Dashboard } from "./pages/Dashboard";
import { IndicatorDetail } from "./pages/IndicatorDetail";

function App() {
  return (
    <SourcesProvider>
      <Routes>
        <Route path="/" element={<CompanyLanding />} />
        <Route element={<DashboardLayout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/indicator/:id" element={<IndicatorDetail />} />
        </Route>
      </Routes>
      <ChatWidget />
    </SourcesProvider>
  );
}

export default App;
