// src/layouts/MainLayout.jsx
import Sidebar from "../components/common/Siderbar";

export default function MainLayout({ children }) {
    return (
        <div className="flex min-h-screen bg-gray-900">
            <Sidebar />

            <div className="flex-1 p-6 text-white">
                {children}
            </div>
        </div>
    );
}
