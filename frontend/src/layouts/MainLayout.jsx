// src/layouts/MainLayout.jsx
import { Outlet, useLocation } from "react-router-dom";
import Sidebar from "../components/common/Siderbar";
import Header from "../components/common/Header";
import { useState } from "react";

export default function MainLayout() {
    const location = useLocation();
    const [isSidebarExpanded, setIsSidebarExpanded] = useState(true);

    // Mapa de rutas finales hacia títulos legibles
    const pageTitles = {
        "": "Chat con Molly",                // Ruta /dashboard
        "automatizations": "Automatizaciones",
        "dashboard": "Dashboard",
        "vulnerabilities": "Vulnerabilidades",
        "assets": "Activos",
        "reports": "Reportes",
        "summaries": "Informes",
        "monitoring": "Monitorización",
        "notifications": "Notificaciones",
        "settings": "Configuración",
    };

    // Obtener la ruta relativa dentro de /dashboard
    let path = location.pathname.replace("/dashboard", ""); // elimina /dashboard inicial
    path = path.replace(/^\/|\/$/g, ""); // elimina cualquier / al inicio o final
    const title = pageTitles[path] || "Dashboard";

    return (
        <div className="flex min-h-screen bg-gray-900">

            <Sidebar 
                isSidebarExpanded={isSidebarExpanded} 
                setIsSidebarExpanded={setIsSidebarExpanded} 
            />

            <div className="flex flex-col flex-1 overflow-hidden">
                <Header title={title} />

                <main className="flex-1 overflow-y-auto p-6 text-white">
                    <Outlet />
                </main>
            </div>
        </div>
    );
}
