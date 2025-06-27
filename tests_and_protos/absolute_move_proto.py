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

# Motor settings
FORWARD = bsm.MOT_Forwards
REVERSE = bsm.MOT_Reverse
ACCEL = 800000
VEL_SCALE = 200000
CENTER = 511
BUFFER = 2

bsm.SBC_SetVelParams(serial, 1, ACCEL, 1000000)
bsm.SBC_MoveAtVelocity(serial, 1, FORWARD)
