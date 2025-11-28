// src/pages/Dashboard/ChatPage.jsx
import { useState } from "react";
import { Loader2, Send } from "lucide-react";

// -------------- Componente de Chat Panel --------------
const ChatPanel = ({ sendMessage, messages, isSending }) => {
  const [inputMessage, setInputMessage] = useState('');
  const messagesEndRef = useRef(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (inputMessage.trim() && !isSending) {
      sendMessage(inputMessage.trim());
      setInputMessage('');
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages]);

  return (
    <div className="flex flex-col h-full p-4">

      {/* Lista de mensajes */}
      <div className="flex-grow overflow-y-auto space-y-4 pr-2">
        {messages.map((msg, index) => (
          <div 
            key={index} 
            className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div 
              className={`max-w-3xl p-3 rounded-xl shadow-lg transition-all duration-300 ${
                msg.sender === 'user'
                  ? 'bg-indigo-600 text-white rounded-br-none'
                  : 'bg-gray-700 text-gray-100 rounded-tl-none'
              }`}
            >
              {/* Cabecera */}
              <div className="font-semibold text-xs mb-1 opacity-70">
                {msg.sender === 'user' ? 'Tú' : 'Molly'}
              </div>

              <p className="whitespace-pre-wrap">{msg.text}</p>
            </div>
          </div>
        ))}

        {/* Indicador escribiendo */}
        {isSending && (
          <div className="flex justify-start">
            <div className="max-w-xs p-3 rounded-xl bg-gray-700 text-gray-100 rounded-tl-none flex items-center space-x-2">
              <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
              <span>Molly está escribiendo...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Caja de texto */}
      <form onSubmit={handleSubmit} className="mt-4 flex items-center p-3 bg-gray-800 rounded-xl shadow-inner">
        <input
          type="text"
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          placeholder="Escribe tu mensaje aquí..."
          className="flex-grow bg-transparent text-gray-200 placeholder-gray-400 focus:outline-none text-base"
          disabled={isSending}
        />
        <button
          type="submit"
          disabled={!inputMessage.trim() || isSending}
          className={`ml-3 p-3 rounded-full transition-all duration-200 ${
            !inputMessage.trim() || isSending
              ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
              : 'bg-indigo-600 text-white hover:bg-indigo-500 shadow-md hover:shadow-lg'
          }`}
        >
          {isSending ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
        </button>
      </form>
    </div>
  );
};

// --------------------------------------------------------
// ---------------------- CHAT PAGE ------------------------
// --------------------------------------------------------

import { useEffect, useRef } from "react";

export default function ChatPage() {
  const [messages, setMessages] = useState([]);
  const [isSending, setIsSending] = useState(false);

  // --- FUNCION PARA SIMULAR RESPUESTA DE MOLLY ---
  const sendMessage = async (text) => {
    // Añadir mensaje del usuario
    setMessages(prev => [...prev, { sender: "user", text }]);
    setIsSending(true);

    // Simular generacion de respuesta
    await new Promise(resolve => setTimeout(resolve, 1200));

    // Respuesta dummy (luego conectarás con tu backend real)
    const mollyReply = "Hola, soy Molly. Te ayudare con lo que necesites.";

    setMessages(prev => [...prev, { sender: "molly", text: mollyReply }]);
    setIsSending(false);
  };

  return (
    <div className="h-full">
      <ChatPanel 
        sendMessage={sendMessage}
        messages={messages}
        isSending={isSending}
      />
    </div>
  );
}
