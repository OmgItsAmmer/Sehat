import { BrowserRouter, Navigate, Route, Routes, useParams } from "react-router-dom";
import { AnalyticsDashboard } from "@/pages/AnalyticsDashboard";
import { ClinicDashboard } from "@/pages/ClinicDashboard";
import { DesignSystem } from "@/pages/DesignSystem";
import { LandingPage } from "@/pages/LandingPage";
import { PatientChatPage } from "@/pages/PatientChatPage";
import { SlackAlertCard } from "@/pages/SlackAlertCard";

function CaseDetailRedirect() {
  const { phone = "" } = useParams();
  return (
    <Navigate
      to={`/dashboard?case=${encodeURIComponent(decodeURIComponent(phone))}`}
      replace
    />
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/chat" element={<PatientChatPage />} />
        <Route path="/dashboard" element={<ClinicDashboard />} />
        <Route path="/analytics" element={<AnalyticsDashboard />} />
        <Route path="/alerts/slack" element={<SlackAlertCard />} />
        <Route path="/design-system" element={<DesignSystem />} />

        {/* Legacy mobile routes → dashboard */}
        <Route path="/cases" element={<Navigate to="/dashboard" replace />} />
        <Route path="/cases/:phone" element={<CaseDetailRedirect />} />
        <Route path="/alerts/p1" element={<Navigate to="/dashboard" replace />} />
        <Route path="/chat/*" element={<Navigate to="/chat" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
