import { Route, Routes } from "react-router-dom";

import { AppStateProvider } from "./state/AppState";
import { DailyPage } from "./pages/DailyPage";
import { DataQualityPage } from "./pages/DataQualityPage";
import { DiagnosisPage } from "./pages/DiagnosisPage";
import { HomePage } from "./pages/HomePage";
import { MapPage } from "./pages/MapPage";
import { OnboardingPage } from "./pages/OnboardingPage";
import { RehearsalPage } from "./pages/RehearsalPage";
import { ResultPage } from "./pages/ResultPage";

export default function App() {
  return (
    <AppStateProvider>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/onboarding" element={<OnboardingPage />} />
        <Route path="/diagnosis" element={<DiagnosisPage />} />
        <Route path="/result" element={<ResultPage />} />
        <Route path="/rehearsal" element={<RehearsalPage />} />
        <Route path="/daily" element={<DailyPage />} />
        <Route path="/map" element={<MapPage />} />
        <Route path="/data-quality" element={<DataQualityPage />} />
      </Routes>
    </AppStateProvider>
  );
}
