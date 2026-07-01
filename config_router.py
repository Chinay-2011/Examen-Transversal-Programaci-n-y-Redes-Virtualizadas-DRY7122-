from ncclient import manager
import xml.dom.minidom


ROUTER_IP = "192.168.56.104"
ROUTER_PORT = 830
USER = "cisco"
PASS = "cisco123!"


config_xml = """
<config>
  <native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">
    
    <hostname>Chery-Gatica</hostname>
    
    <interface>
      <Loopback>
        <name>11</name>
        <description>Creada via NETCONF - Examen DRY7122</description>
        <ip>
          <address>
            <primary>
              <address>11.11.11.11</address>
              <mask>255.255.255.255</mask>
            </primary>
          </address>
        </ip>
      </Loopback>
    </interface>
    
  </native>
</config>
"""

def main():
    print(f"\n[1] Iniciando conexión NETCONF hacia el router {ROUTER_IP} por el puerto {ROUTER_PORT}...")
    
    try:
        
        with manager.connect(host=ROUTER_IP, port=ROUTER_PORT, username=USER, password=PASS, hostkey_verify=False) as m:
            print("[2] ¡Conexión exitosa demostrada!")
            
            print("[3] Enviando configuración XML (Hostname y Loopback 11)...")
            
            respuesta = m.edit_config(target='running', config=config_xml)
            
            print("[4] ¡Configuración aplicada correctamente!\n")
            
            
            xml_respuesta = xml.dom.minidom.parseString(respuesta.xml).toprettyxml()
            print("Respuesta del Router (RPC Reply):")
            print(xml_respuesta)
            
    except Exception as e:
        print(f"\n[Error]: Falló la conexión o la configuración. Detalles: {e}")

if __name__ == '__main__':
    main()
