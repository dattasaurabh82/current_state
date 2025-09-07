#!/usr/bin/env python3

# --------------
# SIMPLE EXAMPLE
# --------------
# import sounddevice as sd

# # List all audio devices with details
# print("--- Available Audio Devices ---")
# try:
#     devices = sd.query_devices()
#     if not devices:
#         print("No audio devices found.")
#     else:
#         for i, device in enumerate(devices):
#             print(f"Device {i}: {device['name']}")
#             print(f"  Channels: {device['max_input_channels']} in, {device['max_output_channels']} out")
#             print(f"  Sample rates: {device['default_samplerate']} Hz (default)")
#             print(f"  Device type: {'Input' if device['max_input_channels'] > 0 else ''}"
#                   f"{' & ' if device['max_input_channels'] > 0 and device['max_output_channels'] > 0 else ''}"
#                   f"{'Output' if device['max_output_channels'] > 0 else ''}")
#             print()
# except Exception as e:
#     print(f"Error querying devices: {e}")

# print("\n--- Default Devices ---")

# # Safely get the default input device
# try:
#     default_input = sd.query_devices(kind='input')
#     print(f"Default input device: {default_input['name']}")
# except sd.PortAudioError:
#     print("No default input device found.")

# # Safely get the default output device
# try:
#     default_output = sd.query_devices(kind='output')
#     print(f"Default output device: {default_output['name']}")
# except sd.PortAudioError:
#    print("No default output device found.")

# ----------------------
# MORE ELABORATE EXAMPLE
# ----------------------
import sounddevice as sd
import textwrap
import platform

# Try to import colorama for colored output, but work without it too
try:
    from colorama import Fore, Style, init

    init()  # Initialize colorama
    color_support = True
except ImportError:
    # Create dummy color class if colorama isn't available
    class DummyColor:
        def __getattr__(self, name):
            return ""

    Fore = DummyColor()
    Style = DummyColor()
    color_support = False


def get_os_info():
    """Get operating system information"""
    return f"{platform.system()} {platform.release()} ({platform.machine()})"


def print_header(title, width=80):
    """Print a formatted header"""
    print(f"\n{Fore.CYAN}{Style.BRIGHT}" + "=" * width + Style.RESET_ALL)
    print(f"{Fore.CYAN}{Style.BRIGHT} {title} {Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}" + "=" * width + Style.RESET_ALL)


def print_section(title, width=80):
    """Print a formatted section header"""
    print(f"\n{Fore.YELLOW}{Style.BRIGHT} {title} {Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{Style.BRIGHT}" + "-" * width + Style.RESET_ALL)


def format_device_info(device):
    """Format a single piece of device info nicely"""
    return f"{Fore.GREEN}{device}{Style.RESET_ALL}"


def get_supported_sample_rates(device_index):
    """Try to determine supported sample rates for a device"""
    # Common sample rates to test
    test_rates = [
        8000,
        11025,
        16000,
        22050,
        24000,
        32000,
        44100,
        48000,
        88200,
        96000,
    ]
    supported = []

    for rate in test_rates:
        try:
            # Check for output devices only
            sd.check_output_settings(device=device_index, samplerate=rate)
            supported.append(rate)
        except Exception:
            # Silently ignore rates that are not supported
            pass

    return supported


def wrap_text(text, initial_indent="", subsequent_indent="  ", width=70):
    """Wrap text to the specified width with indentation"""
    wrapper = textwrap.TextWrapper(
        width=width, initial_indent=initial_indent, subsequent_indent=subsequent_indent
    )
    return wrapper.fill(text)


def main():
    """Main function to display audio device information"""
    # Get all audio devices
    devices = sd.query_devices()

    # --- Safely get default devices --- #
    try:
        default_input = sd.query_devices(kind="input")
    except sd.PortAudioError:
        default_input = None

    try:
        default_output = sd.query_devices(kind="output")
    except sd.PortAudioError:
        default_output = None

    # Count device types
    total_devices = len(devices)
    input_devices = sum(1 for d in devices if d["max_input_channels"] > 0)
    output_devices = sum(1 for d in devices if d["max_output_channels"] > 0)

    # Print system information
    print_header(f"Sound Device Information - {get_os_info()}")

    # Print summary
    print(f"\n{Fore.WHITE}Found {format_device_info(total_devices)} audio devices:")
    print(f" • {format_device_info(input_devices)} input devices")
    print(f" • {format_device_info(output_devices)} output devices")

    # Print all devices
    print_section("All Audio Devices")

    for i, device in enumerate(devices):
        # --- Check if default devices exist before comparing --- #
        is_default_input = False
        if default_input:
            is_default_input = (
                device["name"] == default_input["name"]
                and device["hostapi"] == default_input["hostapi"]
            )
        
        is_default_output = False
        if default_output:
            is_default_output = (
                device["name"] == default_output["name"]
                and device["hostapi"] == default_output["hostapi"]
            )

        # Device header
        default_markers = []
        if is_default_input:
            default_markers.append(f"{Fore.MAGENTA}DEFAULT INPUT{Style.RESET_ALL}")
        if is_default_output:
            default_markers.append(f"{Fore.MAGENTA}DEFAULT OUTPUT{Style.RESET_ALL}")

        default_str = f" ({' & '.join(default_markers)})" if default_markers else ""

        print(
            f"\n{Fore.BLUE}{Style.BRIGHT}Device {i}: {Fore.WHITE}{device['name']}{Style.RESET_ALL}{default_str}"
        )

        # Device type
        device_type = []
        if device["max_input_channels"] > 0:
            device_type.append("Input")
        if device["max_output_channels"] > 0:
            device_type.append("Output")

        print(f"  Type:         {Fore.GREEN}{' & '.join(device_type)}{Style.RESET_ALL}")

        # Channel information
        print(
            f"  Channels:     {Fore.GREEN}{device['max_input_channels']}{Style.RESET_ALL} in, "
            f"{Fore.GREEN}{device['max_output_channels']}{Style.RESET_ALL} out"
        )

        # Sample rate information
        print(
            f"  Default Rate: {Fore.GREEN}{device['default_samplerate']:.0f} Hz{Style.RESET_ALL}"
        )

        # Latency information
        if device["max_input_channels"] > 0:
            print(
                f"  Input Latency: {Fore.GREEN}{device['default_low_input_latency'] * 1000:.2f}{Style.RESET_ALL} ms (low), "
                f"{Fore.GREEN}{device['default_high_input_latency'] * 1000:.2f}{Style.RESET_ALL} ms (high)"
            )

        if device["max_output_channels"] > 0:
            print(
                f"  Output Latency: {Fore.GREEN}{device['default_low_output_latency'] * 1000:.2f}{Style.RESET_ALL} ms (low), "
                f"{Fore.GREEN}{device['default_high_output_latency'] * 1000:.2f}{Style.RESET_ALL} ms (high)"
            )

        # Host API information
        print(
            f"  Host API:     {Fore.GREEN}{sd.query_hostapis(device['hostapi'])['name']}{Style.RESET_ALL}"
        )

        # Try to determine supported sample rates (only for output devices)
        if device["max_output_channels"] > 0:
            supported_rates = get_supported_sample_rates(i)
            if supported_rates:
                rates_str = ", ".join(
                    f"{rate / 1000:.1f}k" if rate >= 1000 else str(rate)
                    for rate in supported_rates
                )
                print(
                    wrap_text(
                        f"  Supported Rates: {Fore.GREEN}{rates_str}{Style.RESET_ALL}",
                        initial_indent="  "
                    )
                )

    # Print detailed information about default devices
    print_section("Default Devices")

    # --- Check if default devices exist before printing details --- #
    # Default input
    print(f"\n{Fore.WHITE}{Style.BRIGHT}Default Input Device:{Style.RESET_ALL}")
    if default_input:
        print(f"  Name:         {Fore.GREEN}{default_input['name']}{Style.RESET_ALL}")
        print(f"  Channels:     {Fore.GREEN}{default_input['max_input_channels']}{Style.RESET_ALL}")
        print(
            f"  Sample Rate:  {Fore.GREEN}{default_input['default_samplerate']:.0f} Hz{Style.RESET_ALL}"
        )
        print(
            f"  Latency:      {Fore.GREEN}{default_input['default_low_input_latency'] * 1000:.2f}{Style.RESET_ALL} ms (low), "
            f"{Fore.GREEN}{default_input['default_high_input_latency'] * 1000:.2f}{Style.RESET_ALL} ms (high)"
        )
    else:
        print(f"  {Fore.RED}No default input device found.{Style.RESET_ALL}")

    # Default output
    print(f"\n{Fore.WHITE}{Style.BRIGHT}Default Output Device:{Style.RESET_ALL}")
    if default_output:
        print(f"  Name:         {Fore.GREEN}{default_output['name']}{Style.RESET_ALL}")
        print(f"  Channels:     {Fore.GREEN}{default_output['max_output_channels']}{Style.RESET_ALL}")
        print(
            f"  Sample Rate:  {Fore.GREEN}{default_output['default_samplerate']:.0f} Hz{Style.RESET_ALL}"
        )
        print(
            f"  Latency:      {Fore.GREEN}{default_output['default_low_output_latency'] * 1000:.2f}{Style.RESET_ALL} ms (low), "
            f"{Fore.GREEN}{default_output['default_high_output_latency'] * 1000:.2f}{Style.RESET_ALL} ms (high)"
        )
    else:
        print(f"  {Fore.RED}No default output device found.{Style.RESET_ALL}")

    # Note about color
    if not color_support:
        print("\n(Install 'colorama' package for colored output)")


if __name__ == "__main__":
    main()