import { useState } from "react";
import { sendMessageToMolly } from "../api/mollyApi";

export function useMollyChat() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  async function sendMessage(text) {
    const userMsg = { sender: "user", text };
    setMessages((prev) => [...prev, userMsg]);

    setLoading(true);
    const res = await sendMessageToMolly(text);
    setLoading(false);

    const botMsg = {
      sender: "molly",
      text: res?.response?.response || "Error en la respuesta",
    };

    setMessages((prev) => [...prev, botMsg]);
  }

  return {
    messages,
    loading,
    sendMessage,
  };
}
