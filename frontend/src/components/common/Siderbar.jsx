// src/components/common/Siderbar.jsx
import { Link } from "react-router-dom";

export default function Sidebar() {
    return (
        <div className="w-64 bg-gray-800 p-4">
            <nav className="space-y-4">
                <Link to="/chat" className="block text-gray-300 hover:text-white">Chat</Link>
                <Link to="/dashboard" className="block text-gray-300 hover:text-white">Dashboard</Link>
                <Link to="/vulnerabilities" className="block text-gray-300 hover:text-white">Vulnerabilidades</Link>
                <Link to="/assets" className="block text-gray-300 hover:text-white">Activos</Link>
                <Link to="/reports" className="block text-gray-300 hover:text-white">Reportes</Link>
            </nav>
        </div>
    );
}
