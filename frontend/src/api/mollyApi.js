// src/api/mollyApi.js

export async function loginRequest(username, password) {
  try {
    const res = await fetch("http://192.168.1.38:5000/api/login", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password })
    });

    return await res.json();
  } catch (e) {
    console.error("Error en login:", e);
    return { success: false, error: "Error conectando con el servidor" };
  }
}

export async function sendMessageToMolly(message) {
  try {
    const res = await fetch("http://192.168.1.38:5000/api/chat", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });

    return await res.json();
  } catch (error) {
    console.error("Error enviando mensaje a Molly:", error);
    return { error: "Error de conexion con Molly" };
  }
}
