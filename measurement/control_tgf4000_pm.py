"""
Control TGF4000 function generator to enable phase modulation and query modulation frequency.

This script connects to a TGF4000 series function generator via USB (virtual COM port) or LAN,
enables phase modulation (PM), and queries the current modulation frequency.

The script tries multiple SCPI command formats to work with different firmware versions.
If commands fail, refer to the TGF4000 manual Section 25 (Remote Commands) for the exact syntax.

Prerequisites:
    pip install pyvisa pyvisa-py
    (pyserial is optional but recommended for listing COM ports on Windows)

Usage:
    # First, list available devices to find the address:
    python list_visa_devices.py
    
    # USB connection (virtual COM port)
    python control_tgf4000_pm.py --interface usb --address COM3  # Windows
    python control_tgf4000_pm.py --interface usb --address /dev/ttyUSB0  # Linux
    
    # LAN connection
    python control_tgf4000_pm.py --interface lan --address 192.168.1.100
    
    # Query only (don't enable PM)
    python control_tgf4000_pm.py --interface usb --address COM3 --query-only
    
    # Use channel 2 instead of channel 1
    python control_tgf4000_pm.py --interface usb --address COM3 --channel 2

Reference:
    TGF4000 Series Instruction Manual, Section 13.3 (Phase Modulation)
    and Section 25 (Remote Commands)
    https://resources.aimtti.com/manuals/TGF4000_Series_Instruction_Manual-Iss3.pdf
"""

import argparse
import sys
import time

try:
    import pyvisa
except ImportError:
    print("Error: pyvisa is required. Install it with: pip install pyvisa")
    print("For USB connections, you may also need: pip install pyvisa-py")
    sys.exit(1)


def connect_to_device(interface: str, address: str, timeout: int = 5000) -> pyvisa.Resource:
    """
    Connect to TGF4000 device via USB or LAN.
    
    Args:
        interface: 'usb' or 'lan'
        address: COM port (e.g., 'COM3') or IP address (e.g., '192.168.1.100')
        timeout: Communication timeout in milliseconds
        
    Returns:
        pyvisa.Resource: Connected device resource
    """
    # Use pyvisa-py backend for better COM port support, especially on Windows
    try:
        rm = pyvisa.ResourceManager('@py')
    except Exception:
        # Fallback to default backend
        rm = pyvisa.ResourceManager()
    
    if interface.lower() == 'usb':
        # USB virtual COM port connection
        # Format: 'ASRL<port>::INSTR' for serial/USB
        # Handle different port formats
        if address.upper().startswith('COM'):
            # Windows format: COM3 -> ASRL3::INSTR, COM10 -> ASRL10::INSTR
            # Extract the port number (remove COM prefix, case-insensitive)
            port_num = address[3:]
            resource_name = f"ASRL{port_num}::INSTR"
        elif address.startswith('/dev/'):
            # Linux format: /dev/ttyUSB0 -> ASRL/dev/ttyUSB0::INSTR
            resource_name = f"ASRL{address}::INSTR"
        else:
            # Try as-is (might already be in correct format or just the number)
            resource_name = f"ASRL{address}::INSTR"
        print(f"Connecting to USB device at {address} (resource: {resource_name})...")
    elif interface.lower() == 'lan':
        # LAN connection using TCP/IP
        # Format: 'TCPIP::<ip_address>::INSTR' or 'TCPIP0::<ip_address>::inst0::INSTR'
        resource_name = f"TCPIP::{address}::INSTR"
        print(f"Connecting to LAN device at {address}...")
    else:
        raise ValueError(f"Unknown interface: {interface}. Use 'usb' or 'lan'")
    
    try:
        device = rm.open_resource(resource_name, timeout=timeout)
        # Configure for SCPI communication
        device.write_termination = '\n'
        device.read_termination = '\n'
        return device
    except pyvisa.errors.VisaIOError as e:
        print(f"Error connecting to device: {e}")
        print(f"\nTroubleshooting:")
        print(f"1. Check that the device is powered on")
        print(f"2. For USB: Check the COM port/device path is correct")
        print(f"3. For LAN: Check the IP address and network connection")
        print(f"4. List available devices with: python list_visa_devices.py")
        if interface.lower() == 'usb' and sys.platform == 'win32':
            print(f"5. On Windows, ensure pyvisa-py is installed: pip install pyvisa-py")
            print(f"6. Check Device Manager to verify the COM port number")
        raise


def identify_device(device: pyvisa.Resource) -> str:
    """Query device identification."""
    try:
        idn = device.query("*IDN?")
        print(f"Device identified: {idn.strip()}")
        return idn.strip()
    except Exception as e:
        print(f"Warning: Could not identify device: {e}")
        return ""


def enable_phase_modulation(device: pyvisa.Resource, channel: int = 1) -> None:
    """
    Enable phase modulation on the specified channel.
    
    Based on TGF4000 manual, the commands may vary. This function tries
    common SCPI command formats and verifies the modulation status.
    
    Args:
        device: Connected device resource
        channel: Channel number (1 or 2)
    """
    print(f"\nEnabling phase modulation on Channel {channel}...")
    
    try:
        # Try standard SCPI format first
        # Select modulation type (Phase Modulation)
        device.write(f"SOUR{channel}:MOD:TYPE PM")
        time.sleep(0.1)
        
        # Enable modulation
        device.write(f"SOUR{channel}:MOD:STATE ON")
        time.sleep(0.1)
        
        print("Phase modulation enabled (using SOUR format).")
    except Exception as e1:
        try:
            # Try alternative format
            device.write(f"CH{channel}:MODE PM")
            time.sleep(0.1)
            device.write(f"CH{channel}:MOD:STATE ON")
            time.sleep(0.1)
            
            print("Phase modulation enabled (using CH format).")
        except Exception as e2:
            print(f"Warning: Could not enable PM with standard commands.")
            print(f"  SOUR format error: {e1}")
            print(f"  CH format error: {e2}")
            print(f"  You may need to check the manual for exact command syntax.")
            raise
    
    # Query modulation status to verify it was enabled correctly
    time.sleep(0.2)  # Give device time to process
    print("\nVerifying modulation status...")
    
    try:
        # Query modulation state
        state_cmds = [f"SOUR{channel}:MOD:STATE?", f"CH{channel}:MOD:STATE?"]
        mod_state = None
        for cmd in state_cmds:
            try:
                state = device.query(cmd)
                mod_state = state.strip().upper()
                break
            except:
                continue
        
        # Query modulation type
        mod_type_cmds = [f"SOUR{channel}:MOD:TYPE?", f"CH{channel}:MODE?", f"CH{channel}:MOD:TYPE?"]
        mod_type = None
        for cmd in mod_type_cmds:
            try:
                mod_type = device.query(cmd)
                mod_type = mod_type.strip().upper()
                break
            except:
                continue
        
        # Display status
        if mod_state:
            is_enabled = mod_state in ['ON', '1', 'TRUE']
            status_str = "ON" if is_enabled else "OFF"
            print(f"  Modulation state: {status_str}")
            if not is_enabled:
                print(f"  Warning: Modulation state is {mod_state}, expected ON")
        else:
            print(f"  Warning: Could not query modulation state")
        
        if mod_type:
            print(f"  Modulation type: {mod_type}")
            if mod_type != "PM":
                print(f"  Warning: Modulation type is {mod_type}, expected PM")
        else:
            print(f"  Warning: Could not query modulation type")
            
    except Exception as e:
        print(f"  Warning: Could not verify modulation status: {e}")


def get_modulation_frequency(device: pyvisa.Resource, channel: int = 1) -> float:
    """
    Query the modulation frequency.
    
    Args:
        device: Connected device resource
        channel: Channel number (1 or 2)
        
    Returns:
        float: Modulation frequency in Hz
    """
    # Try different command formats
    commands_to_try = [
        f"SOUR{channel}:MOD:FREQ?",
        f"CH{channel}:MOD:FREQ?",
        f"SOUR{channel}:MOD:PM:FREQ?",
        f"CH{channel}:MOD:PM:FREQ?",
    ]
    
    for cmd in commands_to_try:
        try:
            freq_str = device.query(cmd)
            freq = float(freq_str.strip())
            return freq
        except Exception:
            continue
    
    raise ValueError("Could not query modulation frequency with any known command format")


def get_modulation_state(device: pyvisa.Resource, channel: int = 1) -> dict:
    """
    Get current modulation state and parameters.
    
    Args:
        device: Connected device resource
        channel: Channel number (1 or 2)
        
    Returns:
        dict: Dictionary with modulation parameters
    """
    info = {}
    
    # Try different command formats for each parameter
    try:
        # Query modulation state
        state_cmds = [f"SOUR{channel}:MOD:STATE?", f"CH{channel}:MOD:STATE?"]
        for cmd in state_cmds:
            try:
                state = device.query(cmd)
                info['enabled'] = state.strip().upper() in ['ON', '1', 'TRUE']
                break
            except:
                continue
        
        # Query modulation type
        mod_type_cmds = [f"SOUR{channel}:MOD:TYPE?", f"CH{channel}:MODE?", f"CH{channel}:MOD:TYPE?"]
        for cmd in mod_type_cmds:
            try:
                mod_type = device.query(cmd)
                info['modulation_type'] = mod_type.strip()
                break
            except:
                continue
        
        # Query modulation frequency
        try:
            freq = get_modulation_frequency(device, channel)
            info['modulation_frequency_hz'] = freq
        except Exception as e:
            print(f"  Warning: Could not query modulation frequency: {e}")
        
        # Query modulation depth/deviation (for PM, this is phase deviation)
        pm_dev_cmds = [
            f"SOUR{channel}:MOD:PM:DEV?",
            f"CH{channel}:MOD:PM:DEV?",
            f"SOUR{channel}:MOD:PM:PHASE?",
            f"CH{channel}:MOD:PM:PHASE?",
        ]
        for cmd in pm_dev_cmds:
            try:
                depth = device.query(cmd)
                info['phase_deviation_deg'] = float(depth.strip())
                break
            except:
                continue
        
        # Query carrier frequency
        carrier_cmds = [f"SOUR{channel}:FREQ?", f"CH{channel}:FREQ?"]
        for cmd in carrier_cmds:
            try:
                carrier = device.query(cmd)
                info['carrier_frequency_hz'] = float(carrier.strip())
                break
            except:
                continue
            
    except Exception as e:
        print(f"Warning: Could not query all parameters: {e}")
    
    return info


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Control TGF4000 function generator phase modulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--interface",
        required=True,
        choices=['usb', 'lan'],
        help="Connection interface: 'usb' for virtual COM port or 'lan' for Ethernet"
    )
    
    parser.add_argument(
        "--address",
        required=True,
        help="Device address: COM port (e.g., 'COM3') or IP address (e.g., '192.168.1.100')"
    )
    
    parser.add_argument(
        "--channel",
        type=int,
        default=1,
        choices=[1, 2],
        help="Channel number (1 or 2, default: 1)"
    )
    
    parser.add_argument(
        "--query-only",
        action="store_true",
        help="Only query current settings, don't enable PM"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=5000,
        help="Communication timeout in milliseconds (default: 5000)"
    )
    
    args = parser.parse_args()
    
    # Connect to device
    try:
        device = connect_to_device(args.interface, args.address, args.timeout)
    except Exception as e:
        print(f"Failed to connect: {e}")
        sys.exit(1)
    
    try:
        # Identify device
        identify_device(device)
        
        # Get current state
        print(f"\n--- Current Channel {args.channel} State ---")
        current_state = get_modulation_state(device, args.channel)
        for key, value in current_state.items():
            print(f"  {key}: {value}")
        
        if not args.query_only:
            # Enable phase modulation
            enable_phase_modulation(device, args.channel)
            
            # Wait a moment for settings to take effect
            time.sleep(0.5)
            
            # Query updated state
            print(f"\n--- Updated Channel {args.channel} State ---")
            updated_state = get_modulation_state(device, args.channel)
            for key, value in updated_state.items():
                print(f"  {key}: {value}")
            
            # Display modulation frequency prominently
            if 'modulation_frequency_hz' in updated_state:
                freq = updated_state['modulation_frequency_hz']
                print(f"\n✓ Phase modulation frequency: {freq:.6f} Hz ({freq/1e3:.6f} kHz)")
        else:
            # Just display the modulation frequency if available
            if 'modulation_frequency_hz' in current_state:
                freq = current_state['modulation_frequency_hz']
                print(f"\n✓ Current modulation frequency: {freq:.6f} Hz ({freq/1e3:.6f} kHz)")
        
    except Exception as e:
        print(f"Error during operation: {e}")
        sys.exit(1)
    finally:
        device.close()
        print("\nConnection closed.")


if __name__ == "__main__":
    main()

