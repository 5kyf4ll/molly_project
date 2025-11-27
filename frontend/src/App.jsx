// src/App.jsx
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import LoginPage from "./pages/Auth/LoginPage";
import ChatPage from "./pages/Dashboard/ChatPage";
import DashboardPage from "./pages/Dashboard/DashboardPage";
import ProtectedRoute from "./components/common/ProtectedRoute";
import MainLayout from "./layouts/MainLayout";

export default function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<Navigate to="/login" />} />

                <Route path="/login" element={<LoginPage />} />

                <Route
                    path="/chat"
                    element={
                        <ProtectedRoute>
                            <MainLayout>
                                <ChatPage />
                            </MainLayout>
                        </ProtectedRoute>
                    }
                />

                <Route
                    path="/dashboard"
                    element={
                        <ProtectedRoute>
                            <MainLayout>
                                <DashboardPage />
                            </MainLayout>
                        </ProtectedRoute>
                    }
                />

            </Routes>
        </BrowserRouter>
    );
}
