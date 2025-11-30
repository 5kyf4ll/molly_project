// src/pages/Auth/LoginPage.jsx
import { useState, useContext } from "react";
import { loginRequest } from "../../api/mollyApi";
import { AppContext } from "../../context/AppContext";
import { useNavigate } from "react-router-dom";
import { Bot, User, Lock, LogIn } from "lucide-react";

export default function LoginPage() {
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const navigate = useNavigate();
    const { login } = useContext(AppContext);

    const handleSubmit = async (e) => {
        e.preventDefault();

        const success = await loginRequest(username, password);

        if (success) {
            login(username);
            navigate("/dashboard");
        } else {
            alert("Credenciales incorrectas");
        }
    };


    return (
        <div className="min-h-screen bg-[#0f111a] flex items-center justify-center p-4">
            <div className="bg-[#1a1d29] p-10 rounded-2xl shadow-2xl w-full max-w-md border border-white/5">
                
                {/* Icono con glow */}
                <div className="flex justify-center mb-6">
                    <div className="p-4 bg-indigo-600 rounded-full shadow-[0_0_30px_#4f46e5]">
                        <Bot size={40} className="text-white" />
                    </div>
                </div>

                {/* Título */}
                <h2 className="text-3xl text-center font-bold text-white mb-2">
                    Bienvenido a Molly
                </h2>

                {/* Subtítulo */}
                <p className="text-center text-gray-400 mb-8 text-sm">
                    Asistente de Ciberseguridad IA. Inicia sesion para continuar.
                </p>

                {/* Form */}
                <form onSubmit={handleSubmit} className="space-y-5">

                    {/* Usuario */}
                    <div className="relative">
                        <User className="absolute left-3 top-3 text-gray-400" size={20} />
                        <input
                            className="w-full pl-10 p-3 rounded-lg bg-[#2a2e3d] text-white placeholder-gray-400 focus:ring-2 focus:ring-indigo-500 outline-none"
                            placeholder="Usuario"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                        />
                    </div>

                    {/* Password */}
                    <div className="relative">
                        <Lock className="absolute left-3 top-3 text-gray-400" size={20} />
                        <input
                            type="password"
                            className="w-full pl-10 p-3 rounded-lg bg-[#2a2e3d] text-white placeholder-gray-400 focus:ring-2 focus:ring-indigo-500 outline-none"
                            placeholder="Contrasena"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                        />
                    </div>

                    {/* Botón */}
                    <button
                        type="submit"
                        className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 py-3 rounded-lg text-white font-semibold transition-all"
                    >
                        <LogIn size={18} />
                        Iniciar Sesion
                    </button>
                </form>

                {/* Footer */}
                <p className="text-center text-gray-500 text-xs mt-8">
                    © 2024 Molly AI. Todos los derechos reservados.
                </p>
            </div>
        </div>
    );
}
