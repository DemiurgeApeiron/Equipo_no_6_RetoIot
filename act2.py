import serial

ser = serial.Serial("/dev/cu.usbmodem14101", 115200)
while 1:
    try:
        lineBytes = ser.readline()
        line = lineBytes.decode("ascii")
        line = line.rstrip()
        partes = line.split(";")
        ir = int(partes[0].split(":")[1])
        red = int(partes[1].split(":")[1])
        milis = int(partes[2].split(":")[1])
        print(f"ir {ir}, red {red}, milis {milis}")
    except e:
        continue
