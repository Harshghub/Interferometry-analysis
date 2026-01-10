address = '/dev/ttyACM0'
timeout = 5000
import argparse
import sys
import time
import pyvisa
rm = pyvisa.ResourceManager('@py')

port_num = address[:]
resource_name = f"ASRL{port_num}::INSTR"

def arguments():
    parser = argparse.ArgumentParser(
            description="Control TGF4000 function generator phase modulation",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=__doc__
        )
        
    parser.add_argument(
        "--modulation",
        required=True,
        choices=['on', 'off'],
        help="Connection interface: 'usb' for virtual COM port or 'lan' for Ethernet"
    )

    args = parser.parse_args()

    return args

if __name__ == "__main__":
    args = arguments()

    device = rm.open_resource(resource_name, timeout=timeout)
    idn = device.query("*IDN?")
    print(f"Device identified: {idn.strip()}")
    print(f"Modulation: {args.modulation}")
    set_modulation = "PM" if args.modulation == "on" else "OFF"
    device.write("CHN 1")
    device.write(f"MOD {set_modulation}")
    device.write(f"MODPMSHAPE RAMPUP")
    device.write(f"MODPMFREQ {10e3}")

    device.close()
