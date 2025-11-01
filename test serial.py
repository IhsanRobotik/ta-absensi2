import serial, time
ser = serial.Serial("COM21", 9600)
time.sleep(2)
while True:
    ser.write(b"Hello Arduino\n")
    time.sleep(1)
