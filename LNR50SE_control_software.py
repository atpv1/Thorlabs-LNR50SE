#by adam
import tkinter as tk
from tkinter import ttk
import time
import hid
import threading
from ctypes import c_char_p
import thorlabs_kinesis.benchtop_stepper_motor as bsm


# ===INITIALIZE===
encoder_scale = 409.600

exit_event = threading.Event()

#stages
bsm.TLI_BuildDeviceList()

def init_stage(serial, channel): 
    print(f'Connecting to Device {serial}')
    bsm.SBC_Open(serial)
    bsm.SBC_LoadSettings(serial, channel)
    bsm.SBC_StartPolling(serial, channel, 200)
    bsm.SBC_EnableChannel(serial, channel)
    bsm.SBC_ClearMessageQueue(serial, channel)

    time.sleep(2)

def home():
    print('Homing Devices')
    bsm.SBC_Home(serial_x, channel_x)
    bsm.SBC_Home(serial_y, channel_y)

#hid
device = hid.device()
device.open(0x1313, 0x2005)

#constants
serial_x = c_char_p(bytes("70268564", "utf-8"))
serial_y = c_char_p(bytes("70268564", "utf-8"))

channel_x = 2
channel_y = 1

default_data = [255, 1, 255, 1, 255, 1, 0, 1]
FORWARD = bsm.MOT_Forwards
REVERSE = bsm.MOT_Reverse
ACCEL = 800000
VEL_SCALE = 250000
CENTER = 511
BUFFER = 0
MAX_VELO = 30000000
speed_change = 20

#init stage
init_stage(serial_x, channel_x)
init_stage(serial_y, channel_y)


#artifical polling
last_data = default_data
data_lock = threading.Lock()

def cont_read_data(dev):
    global last_data
    while True:
        data = dev.read(8, timeout_ms = 100)
        if not data:
            data = default_data
        with data_lock:
            last_data = data
        

#start thread
threading.Thread(target=cont_read_data, args=(device,), daemon=True).start()

# ===STAGE CONTROLS===

def get_delta(channel):
    with data_lock:
        data = last_data.copy()
    if channel == channel_x:
        return (data[0] + data[1] * 256) - CENTER
    else:
        return (data[2] + data[3] * 256) - CENTER

def stage_on(serial, channel):
    prev_direction = None
    prev_velocity = 0

    while not exit_event.is_set():
        delta = get_delta(channel)
        if (channel == channel_x and x_button == 1) or (channel == channel_y and y_button == 1):
            delta = 0

        if abs(delta) <= BUFFER:
            if prev_direction is not None:
                bsm.SBC_StopImmediate(serial, channel)
                prev_direction = None
            time.sleep(0.01)
            continue

        # Determine direction and velocity
        direction = FORWARD if delta > 0 else REVERSE
        velocity = int(min(VEL_SCALE * abs(delta), MAX_VELO))

        # Only update direction or velocity if it changed significantly
        if direction != prev_direction or abs(velocity - prev_velocity) > 3000000:
            bsm.SBC_StopImmediate(serial, channel)
            bsm.SBC_SetVelParams(serial, channel, ACCEL, velocity)
            bsm.SBC_MoveAtVelocity(serial, channel, direction)
            prev_direction = direction
            prev_velocity = velocity


#button threading
x_button = 0
y_button = 0
lights = [255, 96, 255]



def button_controls(): 
    global x_button
    global y_button
    global lights
    global is_button_on

    is_button_on = True

    prev_data = default_data

    while is_button_on:  
        with data_lock:
            data = last_data.copy()
        #turn off/on lights
        if data[6] == 1 and prev_data[6] != 1:
            if x_button == 0:
                lights[1] = 0
                device.write(lights)
                x_button = 1
            else:
                lights[1] = 255
                device.write(lights)
                x_button = 0
        elif data[6] == 2 and prev_data[6] != 2:
            if y_button == 0:
                lights[2] = 0
                device.write(lights)
                y_button = 1
            else:
                lights[2] = 255 
                device.write(lights)
                y_button = 0
        prev_data = data

def controller_on():
    exit_event.clear()
    status_canvas.itemconfig(status_circle, fill = 'green')
    device.write(lights)
    print('Manual Control On')

    threading.Thread(target = button_controls, daemon=True).start()
    threading.Thread(target = stage_on, args=(serial_x, channel_x), daemon=True).start()
    threading.Thread(target = stage_on, args=(serial_y, channel_y), daemon=True).start()

def stop():
    print('Stopping')
    bsm.SBC_StopProfiled(serial_x, channel_x)
    bsm.SBC_StopProfiled(serial_y, channel_y)

def stop_controller():
    global is_button_on

    print("Stopping controller...")
    exit_event.set()
    bsm.SBC_StopImmediate(serial_x, channel_x)
    time.sleep(0.2)
    bsm.SBC_ClearMessageQueue(serial_x, channel_x)

    bsm.SBC_StopImmediate(serial_y, channel_y)
    time.sleep(0.2)
    bsm.SBC_ClearMessageQueue(serial_y, channel_y)

    is_button_on = False
    status_canvas.itemconfig(status_circle, fill='red')
    device.write([0, 0, 0])
    print("Manual Control Off")

# === GUI Back End ===
def read_position():
    device_x = bsm.SBC_GetPositionCounter(serial_x, channel_x) / encoder_scale
    device_y = bsm.SBC_GetPositionCounter(serial_y, channel_y) / encoder_scale
    return device_x, device_y

def move(x, y):
    print(f'Moving: {x}, {y}')
    default_speed = (int(100000 * encoder_scale))
    bsm.SBC_SetVelParams(serial_x, channel_x, ACCEL, default_speed)
    bsm.SBC_SetVelParams(serial_y, channel_y, ACCEL, default_speed)

    x_position = int(x * encoder_scale)
    bsm.SBC_MoveToPosition(serial_x, channel_x, x_position)

    y_position = int(y * encoder_scale)
    bsm.SBC_MoveToPosition(serial_y, channel_y, y_position)


def restart():
    print("Restarting...")

    stop()
    stop_controller()
    bsm.SBC_StopPolling(serial_x, channel_x)
    bsm.SBC_Close(serial_x, channel_x)
    bsm.SBC_ClearMessageQueue(serial_x, channel_x)
    bsm.SBC_StopPolling(serial_y, channel_y)
    bsm.SBC_Close(serial_y, channel_y)
    bsm.SBC_ClearMessageQueue(serial_y, channel_y)

    init_stage(serial_x, channel_x)
    init_stage(serial_y, channel_y)
    
    print('Devices Restarted')

# == GUI vars ==
root = tk.Tk()

x_position = tk.StringVar()
x_position.set('NA_X')
y_position = tk.StringVar()
y_position.set('NA_Y')

x_velo = tk.StringVar()
x_velo.set('NA_X')
y_velo = tk.StringVar()
y_velo.set('NA_Y')

# ========== GUI ==========
FONT_TITLE = ("Segoe UI", 14, "bold")
FONT_BODY = ("Segoe UI", 10)

root.title("Stage Setter by Adam")
root.geometry("550x320")
root.configure(padx=15, pady=10)

# === Position Display Frame ===
position_frame = tk.LabelFrame(root, text="Current Positions", font=FONT_BODY, padx=10, pady=10)
position_frame.grid(row=1, column=0, sticky="w", padx=(0, 10), pady=(0, 10))

POS_FONT = ("Segoe UI", 13, "bold")
POS_STYLE = {
    "font": POS_FONT,
    "bg": "white",
    "width": 20,
    "anchor": "w",
    "relief": "solid",
    "bd": 1,
    "padx": 5,
    "pady": 2
}

x_position_label = tk.Label(position_frame, textvariable=x_position, **POS_STYLE)
x_position_label.grid(row=0, column=0, sticky="w", pady=(0, 4))

y_position_label = tk.Label(position_frame, textvariable=y_position, **POS_STYLE)
y_position_label.grid(row=1, column=0, sticky="w")

def update_position_labels():
    try:
        x, y = read_position()
        x_position.set(f"X: {x:.3f} microns")
        y_position.set(f"Y: {y:.3f} microns")
    except Exception as e:
        print("Failed to read position:", e)
    root.after(100, update_position_labels)

update_position_labels()

name_label = tk.Label(root, text="Name current position:", font=FONT_BODY)
name_label.grid(row=2, column=1, columnspan=2, sticky="w", pady=(0, 3))

name_entry = tk.Entry(root, width=25, font=("Segoe UI", 10))
name_entry.grid(row=3, column=1, sticky="w", pady=(0, 5))

saved_positions = {}

selected_position = tk.StringVar(value="Select...")

position_menu = ttk.OptionMenu(root, selected_position, "Select...")
position_menu.grid(row=4, column=1, sticky="w", pady=(0, 5))

def update_dropdown():
    menu = position_menu["menu"]
    menu.delete(0, "end")
    for name in saved_positions:
        menu.add_command(label=name, command=lambda v=name: selected_position.set(v))

def save_position_name():
    x_pos, y_pos = read_position()
    name = f'{name_entry.get()}: {x_pos: .3f} X, {y_pos: .3f} Y'
    if name:
        saved_positions[name] = (x_pos, y_pos)
        print(f"Saved '{name}': {saved_positions[name]}")
        update_dropdown()
    else:
        print("No name entered.")

def go_to_position():
    name = selected_position.get()
    if name in saved_positions:
        pos = saved_positions[name]
        x, y = pos
        print(f"Going to position '{name}'")
        move(x, y)
    else:
        print("No valid position selected.")

go_button = tk.Button(root, text="Recall", font=FONT_BODY,
                      command=go_to_position, width=10)
go_button.grid(row=4, column=2, sticky="w", padx=(6, 0), pady=(0, 5))

save_button = tk.Button(root, text="Save", font=FONT_BODY,
                        command=save_position_name, width=10)
save_button.grid(row=3, column=2, sticky="w", padx=(6, 0), pady=(0, 5))

# === Manual Buttons===
button_frame = tk.Frame(root)
button_frame.grid(row=1, column=1, sticky="n", pady=(5, 10))

manual_button_row = tk.Frame(button_frame)
manual_button_row.pack(pady=(0, 6))

manual_button = tk.Button(manual_button_row, text="Manual Movement", font=FONT_BODY,
                          command = lambda: threading.Thread(target=controller_on, daemon=True).start(),
                          width=16,)
manual_button.pack(side="left")

stop_button = tk.Button(button_frame, text="Manual Off", font=FONT_BODY, command = lambda: stop_controller(), width=16)
stop_button.pack(side = 'left')

status_canvas = tk.Canvas(manual_button_row, width=16, height=16, highlightthickness=0)
status_circle = status_canvas.create_oval(2, 2, 14, 14, fill = 'red')
status_canvas.pack(side="left", padx=(6, 0))

home_button = tk.Button(root, text="Home", font=FONT_BODY,
                        command= lambda: home(), width=10)
home_button.grid(row=3, column=0, rowspan=2, sticky="ns", padx=(0, 5), pady=0)


move_entry_frame = tk.Frame(root)
move_entry_frame.grid(row = 5, column = 1, sticky = 'w')

move_label = tk.Label(move_entry_frame, text = 'Command Move:', font = ("Segoe UI", 10))
move_label.grid(row = 0, column = 0, sticky = 'w')

move_entry_x = tk.Entry(move_entry_frame, width = 7, font=("Segoe UI", 11))
move_entry_x.grid(row=1, column = 0, sticky="w", padx = (0, 10), pady=(5, 5))

move_entry_y = tk.Entry(move_entry_frame, width = 7, font=("Segoe UI", 11))
move_entry_y.grid(row=1, column = 1, sticky="w", pady=(5, 5))

move_button = tk.Button(root, text = 'Move', font = FONT_BODY, command = lambda: move(float(move_entry_x.get()), float(move_entry_y.get())), width = 10)
move_button.grid(row= 5, column = 2, sticky = 'w', padx = (5, 0), pady = (0, 5))

master_stop_button = tk.Button(root, text = 'STOP', font = FONT_BODY, command = lambda: stop(), width = 10)
master_stop_button.grid(row=5, column=0, padx=(0, 5), pady=0)

reset_device_button = tk.Button(root, text = 'Reset Device', font = FONT_BODY, command = lambda: restart(), width = 15)
reset_device_button.grid(row = 0, column = 0, padx=(0, 5), pady = 0, sticky = 'w')

def on_close():
    print("Shutting down...")
    stop()
    stop_controller()
    bsm.SBC_StopPolling(serial_x, channel_x)
    bsm.SBC_Close(serial_x, channel_x)
    bsm.SBC_StopProfiled(serial_x, channel_x)
    time.sleep(0.2)
    bsm.SBC_ClearMessageQueue(serial_x, channel_x)
    
    bsm.SBC_StopPolling(serial_y, channel_y)
    bsm.SBC_Close(serial_y, channel_y)
    bsm.SBC_StopProfiled(serial_y, channel_y)
    time.sleep(0.2)
    bsm.SBC_ClearMessageQueue(serial_y, channel_y)
    
    device.write([0, 0, 0])
    root.destroy()

root.protocol("WM_DELETE_WINDOW", lambda: on_close())

root.mainloop()

