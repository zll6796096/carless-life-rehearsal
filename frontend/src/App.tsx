import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { AppStateProvider, useAppState } from "./state/AppState";
import { isHakusanPilot } from "./services/api";
import { departureError } from "./utils/departures";
import { DailyPage } from "./pages/DailyPage";
import { DataQualityPage } from "./pages/DataQualityPage";
import { DiagnosisPage } from "./pages/DiagnosisPage";
import { HomePage } from "./pages/HomePage";
import { MapPage } from "./pages/MapPage";
import { OnboardingPage } from "./pages/OnboardingPage";
import { RehearsalPage } from "./pages/RehearsalPage";
import { ResultPage } from "./pages/ResultPage";

function PilotInputGate({ children }: { children: ReactNode }) {
  const { fixture, outboundDeparture, returnDeparture, selectedDestinationIds } = useAppState();
  if (isHakusanPilot() && (!fixture || !selectedDestinationIds.length ||
    departureError(fixture, outboundDeparture, returnDeparture))) {
    return <Navigate to="/onboarding" replace />;
  }
  return children;
}

export default function App() {
  return (
    <AppStateProvider>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/onboarding" element={<OnboardingPage />} />
        <Route path="/diagnosis" element={<PilotInputGate><DiagnosisPage /></PilotInputGate>} />
        <Route path="/result" element={<PilotInputGate><ResultPage /></PilotInputGate>} />
        <Route path="/rehearsal" element={<PilotInputGate><RehearsalPage /></PilotInputGate>} />
        <Route path="/daily" element={<PilotInputGate><DailyPage /></PilotInputGate>} />
        <Route path="/map" element={<PilotInputGate><MapPage /></PilotInputGate>} />
        <Route path="/data-quality" element={<DataQualityPage />} />
      </Routes>
    </AppStateProvider>
  );
}
