// src/App.jsx
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import LoginPage from "./pages/Auth/LoginPage";
import ProtectedRoute from "./components/common/ProtectedRoute";
import MainLayout from "./layouts/MainLayout";

import ChatPage from "./pages/Dashboard/ChatPage";
import AutomationPage from "./pages/Dashboard/AutomationPage";
import DashboardPage from "./pages/Dashboard/DashboardPage";
import VulnerabilitiesPage from "./pages/Dashboard/VulnerabilitiesPage";
import AssetsPage from "./pages/Dashboard/AssetsPage";
import ReportsPage from "./pages/Dashboard/ReportsPage";
import SummariesPage from "./pages/Dashboard/SummariesPage";
import MonitoringPage from "./pages/Dashboard/MonitoringPage";
import NotificationPage from "./pages/Dashboard/NotificationPage"
import SettingsPage from "./pages/Dashboard/SettingsPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Redireccion inicial */}
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<LoginPage />} />

        {/* Rutas protegidas */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <MainLayout />
            </ProtectedRoute>
          }
        >
          {/* Chat como página principal al cargar layout */}
          <Route index element={<ChatPage />} />

          {/* Otras páginas */}
          <Route path="automatizations" element={<AutomationPage />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="vulnerabilities" element={<VulnerabilitiesPage />} />
          <Route path="assets" element={<AssetsPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="summaries" element={<SummariesPage />} />
          <Route path="monitoring" element={<MonitoringPage />} />
          <Route path="notifications" element={<NotificationPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>

        {/* Ruta catch-all */}
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
