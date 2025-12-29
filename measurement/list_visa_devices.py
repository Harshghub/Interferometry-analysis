"""
List available VISA devices (useful for finding TGF4000 connection address).

On Windows and WSL, this script also lists COM ports/serial devices since pyvisa-py 
doesn't automatically discover serial/USB devices.

Usage:
    python list_visa_devices.py

Dependencies:
    - pyvisa (required)
    - pyvisa-py (required)
    - pyserial (optional, for serial port listing on Windows/WSL/Linux)
"""

import sys
import os

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
    # Note: pyserial is optional - used only for serial port listing


def is_wsl() -> bool:
    """Detect if running in Windows Subsystem for Linux (WSL)."""
    # Check for WSL-specific indicators
    if os.path.exists('/proc/version'):
        with open('/proc/version', 'r') as f:
            version_info = f.read().lower()
            if 'microsoft' in version_info or 'wsl' in version_info:
                print("came out true")
                return True
    # Check environment variable (WSL2)
    if os.environ.get('WSL_DISTRO_NAME') or os.environ.get('WSL_INTEROP'):
        return True
    return False


def list_serial_ports() -> list:
    """List available serial ports (COM ports on Windows, /dev/tty* on Linux/WSL)."""
    if not HAS_SERIAL_TOOLS:
        return []
    
    ports = serial.tools.list_ports.comports()
    return [(port.device, port.description) for port in ports]


def main() -> None:
    """List all available VISA resources."""
    print("Scanning for VISA devices...\n")
    
    # Detect environment
    is_wsl_env = is_wsl()
    is_windows = sys.platform == 'win32'
    
    if is_wsl_env:
        print("Detected WSL environment")
    print()
    
    try:
        rm = pyvisa.ResourceManager('@py')
        print("Using pyvisa-py backend")
    except Exception:
        # Fallback to default
        rm = pyvisa.ResourceManager()
        print("Using default backend")
    resources = rm.list_resources()
    
    # On Windows/WSL/Linux, pyvisa-py may not auto-detect serial ports, so we'll check manually
    serial_ports = []
    if HAS_SERIAL_TOOLS:
        serial_ports = list_serial_ports()
    
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
        if is_windows or is_wsl_env:
            print("Note: pyvisa-py may not auto-detect serial/COM ports.")
    
    # Display serial ports (especially useful on Windows/WSL/Linux)
    if serial_ports:
        if resources:
            print("\n" + "="*60)
        if is_windows:
            print("\nAvailable COM ports (may include USB devices):")
        else:
            print("\nAvailable serial ports (may include USB devices):")
        for i, (port, desc) in enumerate(serial_ports, 1):
            print(f"  {i}. {port} - {desc}")
    
    # Final summary and instructions
    if not resources and not serial_ports:
        print("\nTroubleshooting:")
        print("1. Ensure the device is powered on and connected")
        print("2. For USB: Install device drivers if needed")
        if is_wsl_env:
            print("   - In WSL, you may need to configure USB passthrough")
            print("   - Serial ports from Windows appear as /dev/ttyS* devices")
        print("3. For LAN: Ensure device is on the network")
        if is_windows:
            print("4. Check Device Manager (Windows) for COM ports")
        if not HAS_SERIAL_TOOLS:
            print("5. Install pyserial to list serial ports: pip install pyserial")
    else:
        print("\n" + "="*60)
        print("\nTo use a device with control_tgf4000_pm.py:")
        if serial_ports:
            if is_windows:
                print("  - USB: Use a COM port from the list above (e.g., COM3)")
            elif is_wsl_env:
                print("  - USB: Use a serial port from the list above (e.g., /dev/ttyS3)")
                print("    Note: Windows COM ports appear as /dev/ttyS* in WSL")
                print("    If you see COM3 in Windows, it may appear as /dev/ttyS3 in WSL")
            else:
                print("  - USB: Use a serial port from the list above (e.g., /dev/ttyUSB0 or /dev/ttyS3)")
        print("  - LAN: Use the IP address from the device settings")
        if serial_ports:
            print("\nExample USB connection:")
            if is_windows:
                example_port = serial_ports[0][0] if serial_ports else "COM3"
            elif is_wsl_env:
                print("wsl is true")
                example_port = serial_ports[0][0] if serial_ports else "/dev/ttyS3"
            else:
                example_port = serial_ports[0][0] if serial_ports else "/dev/ttyUSB0"
            print(f"  python control_tgf4000_pm.py --interface usb --address {example_port}")
            if is_wsl_env:
                print("\nWSL-specific notes:")
                print("  - Serial ports from Windows are typically /dev/ttyS0, /dev/ttyS1, etc.")
                print("  - You may need to set permissions: sudo chmod 666 /dev/ttyS*")
                print("  - Or add your user to the dialout group: sudo usermod -aG dialout $USER")
                print("  - After adding to dialout group, log out and back in for changes to take effect")


if __name__ == "__main__":
    main()

