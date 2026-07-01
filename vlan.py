# vlan.py
print("====================================")
print("     VERIFICADOR DE RANGOS VLAN     ")
print("====================================")

try:
    
    vlan = int(input("Por favor, ingrese el número de VLAN a consultar: "))

    if 1 <= vlan <= 1005:
        print(f"\n[Resultado]: La VLAN {vlan} corresponde al RANGO NORMAL.")
    elif 1006 <= vlan <= 4094:
        print(f"\n[Resultado]: La VLAN {vlan} corresponde al RANGO EXTENDIDO.")
    else:
        print(f"\n[Error]: El número {vlan} está fuera del rango estándar de VLANs (1 - 4094).")

except ValueError:
    print("\n[Error]: Entrada inválida. Por favor, ingrese solo números enteros.")

