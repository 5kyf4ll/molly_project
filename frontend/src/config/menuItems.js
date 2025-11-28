// src/config/menuItems.js
import { 
  Bot, Terminal, Globe, BarChart3, Shield, Briefcase, 
  FileText, Layers, Zap, Bell, Settings 
} from "lucide-react";

const menuItems = [
  { name: "IA", icon: Bot, path: "" }, // ChatPage /dashboard
  { name: "Automatizaciones", icon: Terminal, path: "automatizations" },
  { name: "Dashboard", icon: BarChart3, path: "dashboard" },
  { name: "Vulnerabilidades", icon: Shield, path: "vulnerabilities" },
  { name: "Activos", icon: Briefcase, path: "assets" },
  { name: "Reportes", icon: FileText, path: "reports" },
  { name: "Informes", icon: Layers, path: "summaries" },
  { name: "Monitorizacion", icon: Zap, path: "monitoring" },
  { name: "Notificaciones", icon: Bell, path: "notifications" },
  { name: "Configuracion", icon: Settings, path: "settings" },
];


export default menuItems;
