import { BrowserRouter, Navigate, Route, Routes, useParams } from "react-router-dom";
import { AnalyticsDashboard } from "@/pages/AnalyticsDashboard";
import { ClinicDashboard } from "@/pages/ClinicDashboard";
import { DesignSystem } from "@/pages/DesignSystem";
import { SlackAlertCard } from "@/pages/SlackAlertCard";

function CaseDetailRedirect() {
  const { phone = "" } = useParams();
  return <Navigate to={`/?case=${encodeURIComponent(decodeURIComponent(phone))}`} replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ClinicDashboard />} />
        <Route path="/analytics" element={<AnalyticsDashboard />} />
        <Route path="/alerts/slack" element={<SlackAlertCard />} />
        <Route path="/design-system" element={<DesignSystem />} />

        {/* Legacy mobile routes → dashboard */}
        <Route path="/cases" element={<Navigate to="/" replace />} />
        <Route path="/cases/:phone" element={<CaseDetailRedirect />} />
        <Route path="/alerts/p1" element={<Navigate to="/" replace />} />
        <Route path="/chat/*" element={<Navigate to="/" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
