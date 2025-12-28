"""
List available VISA devices (useful for finding TGF4000 connection address).

On Windows, this script also lists COM ports since pyvisa-py doesn't automatically
discover serial/USB devices.

Usage:
    python list_visa_devices.py

Dependencies:
    - pyvisa (required)
    - pyvisa-py (required)
    - pyserial (optional, for COM port listing on Windows)
"""

import sys

try:
    import pyvisa
except ImportError:
    print("Error: pyvisa is required. Install it with: pip install pyvisa pyvisa-py")
    sys.exit(1)

try:
    import serial.tools.list_ports
    HAS_SERIAL_TOOLS = True
except ImportError:
    HAS_SERIAL_TOOLS = False
    # Note: pyserial is optional - used only for COM port listing on Windows


def list_com_ports() -> list:
    """List available COM ports on Windows."""
    if not HAS_SERIAL_TOOLS:
        return []
    
    ports = serial.tools.list_ports.comports()
    return [(port.device, port.description) for port in ports]


def main() -> None:
    """List all available VISA resources."""
    print("Scanning for VISA devices...\n")
    
    try:
        rm = pyvisa.ResourceManager('@py')
        print("Using pyvisa-py backend")
    except Exception:
        # Fallback to default
        rm = pyvisa.ResourceManager()
        print("Using default backend")
    resources = rm.list_resources()
    
    # On Windows, pyvisa-py doesn't auto-detect COM ports, so we'll check manually
    com_ports = []
    if sys.platform == 'win32' and HAS_SERIAL_TOOLS:
        com_ports = list_com_ports()
    
    # Display VISA-discovered resources
    if resources:
        print(f"Found {len(resources)} VISA device(s):\n")
        
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
    else:
        print("No VISA devices found via automatic discovery.")
        if sys.platform == 'win32':
            print("Note: pyvisa-py on Windows may not auto-detect COM ports.")
    
    # Display COM ports (especially useful on Windows)
    if com_ports:
        if resources:
            print("\n" + "="*60)
        print("\nAvailable COM ports (may include USB devices):")
        for i, (port, desc) in enumerate(com_ports, 1):
            print(f"  {i}. {port} - {desc}")
    
    # Final summary and instructions
    if not resources and not com_ports:
        print("\nTroubleshooting:")
        print("1. Ensure the device is powered on and connected")
        print("2. For USB: Install device drivers if needed")
        print("3. For LAN: Ensure device is on the network")
        print("4. Check Device Manager (Windows) for COM ports")
        if not HAS_SERIAL_TOOLS and sys.platform == 'win32':
            print("5. Install pyserial to list COM ports: pip install pyserial")
    else:
        print("\n" + "="*60)
        print("\nTo use a device with control_tgf4000_pm.py:")
        if com_ports:
            print("  - USB: Use a COM port from the list above (e.g., COM3)")
        print("  - LAN: Use the IP address from the device settings")
        if com_ports:
            print("\nExample USB connection:")
            example_port = com_ports[0][0] if com_ports else "COM3"
            print(f"  python control_tgf4000_pm.py --interface usb --address {example_port}")


if __name__ == "__main__":
    main()

