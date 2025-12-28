"""
List available VISA devices (useful for finding TGF4000 connection address).

Usage:
    python list_visa_devices.py
"""

import sys

try:
    import pyvisa
except ImportError:
    print("Error: pyvisa is required. Install it with: pip install pyvisa pyvisa-py")
    sys.exit(1)


def main() -> None:
    """List all available VISA resources."""
    print("Scanning for VISA devices...\n")
    
    rm = pyvisa.ResourceManager()+
    resources = rm.list_resources()
    
    if not resources:
        print("No VISA devices found.")
        print("\nTroubleshooting:")
        print("1. Ensure the device is powered on and connected")
        print("2. For USB: Install device drivers if needed")
        print("3. For LAN: Ensure device is on the network")
        return
    
    print(f"Found {len(resources)} device(s):\n")
    
    for i, resource in enumerate(resources, 1):
        print(f"{i}. {resource}")
        
        # Try to open and identify the device
        try:
            device = rm.open_resource(resource, timeout=2000)
            device.write_termination = '\n'
            device.read_termination = '\n'
            
            try:
                idn = device.query("*IDN?")
                print(f"   ID: {idn.strip()}")
            except:
                print("   (Could not query device ID)")
            
            device.close()
        except Exception as e:
            print(f"   (Could not open: {e})")
        
        print()
    
    print("\nTo use a device with control_tgf4000_pm.py:")
    print("  - USB: Use the COM port or /dev/tty* path")
    print("  - LAN: Use the IP address from the device settings")


if __name__ == "__main__":
    main()

