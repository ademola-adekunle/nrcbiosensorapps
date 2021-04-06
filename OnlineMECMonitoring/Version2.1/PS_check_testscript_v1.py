from koradserial import KoradSerial

try:
    ps = KoradSerial('/dev/ttyAMA0')
    print(ps.status)
except Exception:
    print("NOPE!")
