#to do, import this code into stage_set, make sure it matches with the different changes. fix random stops, fix velocity not changing

import time
import threading
import hid
import thorlabs_kinesis.benchtop_stepper_motor as bsm

serial = b'70268564'
bsm.TLI_BuildDeviceList()
bsm.SBC_Open(serial)
bsm.SBC_StartPolling(serial, 1, 200)
bsm.SBC_EnableChannel(serial, 1)

time.sleep(2)
bsm.SBC_Home(serial, 1)
print('homed')
 
 
# HID setup
device = hid.device()
device.open(0x1313, 0x2005)
default = [255, 1, 255, 1, 255, 1, 0, 0]

# Motor settings
FORWARD = bsm.MOT_Forwards
REVERSE = bsm.MOT_Reverse
ACCEL = 800000
VEL_SCALE = 200000
CENTER = 511
BUFFER = 2

# Shared data and lock
last_data = default
data_lock = threading.Lock()

def cont_read_data(dev):
    global last_data
    while True:
        data = dev.read(8, timeout_ms = 200)
        if not data:
            data = default
        with data_lock:
            last_data = data

# Start reading thread
threading.Thread(target=cont_read_data, args=(device,), daemon=True).start()

def get_delta():
    with data_lock:
        data = last_data.copy()
    pos = data[0] + data[1] * 256
    return pos - CENTER, data[6]

while True:
    delta, flag = get_delta()
    enter_delta = 0

    if flag == 4:
        print("Exit command received")
        bsm.SBC_StopProfiled(serial, 1)
        break

    if delta > BUFFER:
        enter_delta = delta
        velocity = min(VEL_SCALE * delta, 5000000)  # cap velocity if needed
        bsm.SBC_SetVelParams(serial, 1, ACCEL, int(velocity))
        bsm.SBC_MoveAtVelocity(serial, 1, FORWARD)
        while True:
            delta, flag = get_delta()
            if delta - enter_delta > 10:
                velocity = min(VEL_SCALE * delta, 5000000)
                bsm.SBC_SetVelParams(serial, 1, ACCEL, int(velocity))
            if delta <= BUFFER or flag == 4:
                break
        bsm.SBC_StopProfiled(serial, 1)

    elif delta < -BUFFER:
        enter_delta = delta
        velocity = min(VEL_SCALE * abs(delta), 50000000)
        bsm.SBC_SetVelParams(serial, 1, ACCEL, int(velocity))
        bsm.SBC_MoveAtVelocity(serial, 1, REVERSE)
        while True:
            delta, flag = get_delta()
            if delta - enter_delta < -10:
                velocity = min(VEL_SCALE * delta, 5000000)
                bsm.SBC_SetVelParams(serial, 1, ACCEL, int(velocity))
            if delta >= -BUFFER or flag == 4:
                break
        bsm.SBC_StopProfiled(serial, 1)

    else:
        bsm.SBC_StopProfiled(serial, 1)
        time.sleep(0.01)  # avoid busy spin
