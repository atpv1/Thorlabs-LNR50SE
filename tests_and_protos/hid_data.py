import hid

device = hid.device()
device.open(0x1313, 0x2005)
default = [255, 1, 255, 1, 255, 1, 0, 0]

while True:
    print(device.read(8))