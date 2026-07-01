from netmiko import ConnectHandler
from datetime import datetime


router = {
    "device_type": "cisco_ios",
    "host": "192.168.56.107",
    "username": "cisco",
    "password": "cisco123!",
    "secret": "cisco123!",
    "port": 22,
}

PROCESO_EIGRP = "REDLAB"
AS_NUMBER     = 100
INTERFAZ      = "GigabitEthernet1"     
RED_IPV4      = "192.168.56.0"
WILDCARD_IPV4 = "0.0.0.255"


def configurar_eigrp(conn):
    config_eigrp = [
        "ipv6 unicast-routing",

        f"router eigrp {PROCESO_EIGRP}",

        f"address-family ipv4 unicast autonomous-system {AS_NUMBER}",
        f"network {RED_IPV4} {WILDCARD_IPV4}",
        f"af-interface {INTERFAZ}",
        "passive-interface",
        "exit-af-interface",
        "exit-address-family",

        f"address-family ipv6 unicast autonomous-system {AS_NUMBER}",
        f"af-interface {INTERFAZ}",
        "passive-interface",
        "exit-af-interface",
        "exit-address-family",
    ]

    print("\n>>> Enviando configuración EIGRP...\n")
    salida = conn.send_config_set(config_eigrp)
    print(salida)

    conn.save_config()  # equivalente a "write memory"


def obtener_informacion(conn):
    comandos = {
        "EIGRP running-config":    "show running-config | section eigrp",
        "Interfaces IPv4":         "show ip interface brief",
        "Interfaces IPv6":         "show ipv6 interface brief",
        "Running config completa": "show running-config",
        "Version":                 "show version",
    }

    resultados = {}
    for nombre, cmd in comandos.items():
        salida = conn.send_command(cmd)
        resultados[nombre] = salida
        print(f"\n{'='*20} {nombre} {'='*20}\n{salida}")

    return resultados


def guardar_reporte(resultados):
    fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_archivo = f"reporte_csr1000v_{fecha}.txt"
    with open(nombre_archivo, "w") as f:
        for nombre, salida in resultados.items():
            f.write(f"\n{'='*20} {nombre} {'='*20}\n{salida}\n")
    print(f"\nReporte guardado en {nombre_archivo}")


def main():
    conn = ConnectHandler(**router)
    conn.enable()

    configurar_eigrp(conn)
    resultados = obtener_informacion(conn)
    guardar_reporte(resultados)

    conn.disconnect()


if __name__ == "__main__":
    main()