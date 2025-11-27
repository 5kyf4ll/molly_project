# src/modules/nmap_tool/nmap_runner.py
from utils.command_runner import CommandRunner, CommandResult
from typing import Dict, Any

class NmapRunner:
    """
    Gestiona la construcción y ejecución de comandos Nmap.
    """
    def __init__(self, command_runner: CommandRunner):
        self.command_runner = command_runner
        self.nmap_executable = "nmap" # Podría ser configurable
        print("[NmapRunner] Inicializado.")

    def build_command(self, target: str, profile: str = 'default_scan', ports: str = None) -> str:
        """
        Construye un comando Nmap basado en un perfil predefinido.
        Args:
            target (str): Dirección IP o rango de red objetivo.
            profile (str): Nombre del perfil de escaneo (ej. 'default_scan', 'os_detection').
            ports (str, optional): Puertos específicos a escanear (ej. "22,80,443").

        Returns:
            str: El comando Nmap completo a ejecutar.
        """
        base_command = f"{self.nmap_executable} -T4" # -T4 para un escaneo más rápido por defecto

        if profile == 'default_scan':
            # Escaneo SYN, detección de servicios/versiones, detección de SO, solo puertos abiertos, timeout.
            # -p- escanea todos los puertos (1-65535). Usar con cuidado o definir un rango.
            # --max-rate para no inundar. --open para mostrar solo puertos abiertos.
            # Puedes ajustar los timeouts según tu necesidad y entorno.
            command_options = "-sS -sV -O --min-rate 500 --max-rate 1000 --min-rtt-timeout 100ms --max-rtt-timeout 1000ms --initial-rtt-timeout 500ms --open"
        elif profile == 'os_detection':
            # Solo detección de SO.
            command_options = "-O"
        elif profile == 'full_tcp_udp_scan':
            # Escaneo TCP y UDP de puertos comunes. Requires root/sudo.
            command_options = "-sS -sU -p 1-1024 --max-rate 500 --open" # Puede ser muy lento, ajustar.
        elif profile == 'vulnerability_script_scan':
            # Escaneo con scripts de vulnerabilidades básicas (requiere root/sudo).
            command_options = "-sV -sC --script vuln" # -sC: default scripts, --script vuln: common vulns
        else:
            # Perfil por defecto o un perfil personalizado simple.
            command_options = "-sS -sV" 
        
        if ports:
            # Si se especifican puertos, sobrescriben el comportamiento de escaneo de puertos del perfil.
            command_options += f" -p {ports}"
        else:
            # Si no se especifican puertos y el perfil usa -p-, lo limitamos para la prueba
            # o se deja como está para un escaneo real. Para evitar escaneos de 65k puertos
            # en la prueba inicial, podemos poner un rango por defecto si 'default_scan' implica todos los puertos.
            if profile == 'default_scan' and "-p-" in base_command: # Esto no es robusto, pero es un ejemplo.
                print("ADVERTENCIA: El perfil 'default_scan' con -p- puede ser muy lento. Considera especificar puertos.")
                # Aquí podrías forzar un rango de puertos para la simulación si no se especifica.
                # O Nmap lo maneja si no se da -p- y solo -sS
                pass

        return f"{base_command} {command_options} {target}"

    def run_nmap_scan(self, target: str, profile: str = 'default_scan', ports: str = None, timeout: int = 600) -> CommandResult:
        """
        Ejecuta un escaneo Nmap y retorna el objeto CommandResult.
        """
        command = self.build_command(target, profile, ports)
        self._log(f"Ejecutando Nmap command: {command}")
        return self.command_runner.run_command(command, timeout)

    def _log(self, message: str):
        """Método simple de logging para NmapRunner."""
        print(f"[NmapRunner] {message}")

# Ejemplo de uso (para pruebas)
if __name__ == '__main__':
    # Simulación de CommandRunner para la prueba de NmapRunner
    class MockCommandRunner:
        def run_command(self, command: str, timeout: int) -> CommandResult:
            print(f"[MockCommandRunner] Ejecutando comando simulado: {command}")
            if "nmap -sS -sV -O" in command and "127.0.0.1" in command:
                simulated_output = """
Nmap scan report for 127.0.0.1
Host is up (0.000040s latency).
Not shown: 997 closed ports
PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 8.9 (Ubuntu)
80/tcp   open  http    Apache httpd 2.4.52 ((Ubuntu))
443/tcp  open  https   Apache httpd 2.4.52 ((Ubuntu))

Nmap done: 1 IP address (1 host up) scanned in 0.50 seconds
"""
                return CommandResult(command, True, simulated_output, "", 0, 0.5)
            elif "nmap -O" in command:
                 simulated_output = """
Nmap scan report for 192.168.1.1
Host is up (0.000040s latency).
Running: Linux 3.X|4.X
OS details: Linux 3.2 - 4.9
"""
                 return CommandResult(command, True, simulated_output, "", 0, 0.2)
            else:
                return CommandResult(command, False, "", "Comando simulado falló.", 1, 0.1)

    mock_runner = MockCommandRunner()
    nmap_runner = NmapRunner(mock_runner)

    print("\n--- Probando escaneo por defecto ---")
    result = nmap_runner.run_nmap_scan("127.0.0.1", profile='default_scan')
    print(f"Éxito: {result.success}\nSTDOUT:\n{result.stdout}")

    print("\n--- Probando detección de SO ---")
    result = nmap_runner.run_nmap_scan("192.168.1.1", profile='os_detection')
    print(f"Éxito: {result.success}\nSTDOUT:\n{result.stdout}")

    print("\n--- Probando escaneo de puertos específicos ---")
    result = nmap_runner.run_nmap_scan("10.0.0.1", profile='default_scan', ports="21,22,23,80")
    print(f"Éxito: {result.success}\nSTDOUT:\n{result.stdout}")