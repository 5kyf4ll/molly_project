// src/components/common/Siderbar.jsx
import { Menu } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { LogOut } from "lucide-react";
import menuItems from "../../config/menuItems";
import { useState } from "react";
import LogoutModal from "./LogoutModal";

const Sidebar = ({ isSidebarExpanded, setIsSidebarExpanded }) => {
  const location = useLocation();
  const [showLogoutModal, setShowLogoutModal] = useState(false);

  return (
    <>
      <aside 
        className={`flex flex-col bg-gray-800 transition-all duration-300 ${
          isSidebarExpanded ? 'w-64' : 'w-20'
        } p-4 shadow-2xl`}
      >

        {/* Header */}
        <div className="relative flex items-center mb-8 h-8">
          {/* Botón menú */}
          <button 
            onClick={() => setIsSidebarExpanded(!isSidebarExpanded)}
            className="p-2 rounded-lg text-gray-400 hover:bg-gray-700 hover:text-white z-10"
          >
            <Menu className="w-6 h-6" />
          </button>

          {/* Texto MOLLY solo expandido */}
          {isSidebarExpanded && (
            <div className="absolute left-1/2 transform -translate-x-1/2 text-2xl font-bold text-indigo-400">
              MOLLY
            </div>
          )}
        </div>

        {/* NAV */}
        <nav className="flex-grow space-y-2">
          {menuItems.map(item => {
            const toPath = `/dashboard${item.path ? "/" + item.path : ""}`;
            const isActive = location.pathname === toPath;

            return (
              <Link
                key={item.path}
                to={toPath}
                className={`flex items-center w-full p-3 rounded-xl transition-all duration-200
                  ${isSidebarExpanded ? 'justify-start' : 'justify-center'}
                  ${isActive
                    ? 'bg-indigo-600 text-white shadow-md'
                    : 'text-gray-300 hover:bg-gray-700 hover:text-white'}
                `}
              >
                <item.icon className={`w-5 h-5 ${isSidebarExpanded && 'mr-3'}`} />
                {isSidebarExpanded && (
                  <span className="text-sm font-medium">{item.name}</span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Logout */}
        <div className="mt-8 pt-4 border-t border-gray-700">
          <button
            onClick={() => setShowLogoutModal(true)}
            className="flex items-center w-full p-3 text-red-400 hover:bg-gray-700 hover:text-red-300"
          >
            <LogOut className={`w-5 h-5 ${isSidebarExpanded && 'mr-3'}`} />
            {isSidebarExpanded && <span>Cerrar Sesion</span>}
          </button>
        </div>

      </aside>

      {/* Modal */}
      <LogoutModal
        open={showLogoutModal}
        onClose={() => setShowLogoutModal(false)}
        onConfirm={() => {
          // logout real aquí
          localStorage.removeItem("token");
          window.location.href = "/login";
        }}
      />
    </>
  );
};

export default Sidebar;
