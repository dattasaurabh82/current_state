import RPi.GPIO as GPIO
import time
import sys

# --- CONFIGURATION ---
LEDS = {"LED_NET": 24, "LED_PLAYER": 25, "LED_RADAR_STATE": 23}

# Note: Buttons connect to GND.
# Code looks for LOW signal (Falling edge).
BUTTONS = {
    "NET_RESET_BTN": 26,
    "BTN_POWER": 3,
    "BTN_RUN_FULL_CYCLE": 17,
    "BTN_PLAY_PAUSE": 22,
    "BTN_STOP": 27,
}

SWITCHES = {"SW_RADAR_ENABLE": 6}


# --- SETUP ---
def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)  # Handle I2C pin warnings gracefully

    # LEDs: Output, Start Low
    for name, pin in LEDS.items():
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)

    # Inputs: Input, Pull Up
    # (Pin is held at 3.3V internally. Connecting to GND pulls it LOW)
    all_inputs = {**BUTTONS, **SWITCHES}
    for name, pin in all_inputs.items():
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)


# --- TESTS ---


def test_leds():
    print("\n" + "=" * 40)
    print("PHASE 1: LED VISUAL CHECK")
    print("=" * 40)
    print("Verify LEDs blink in order...")
    time.sleep(4)

    for name, pin in LEDS.items():
        print(f" -> Blinking {name} (GPIO {pin})...")
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(5)
        GPIO.output(pin, GPIO.LOW)
        time.sleep(2)

    # We ask, but we don't stop the script. Just record the report.
    ans = input("\nDid they look okay? (y/n): ").strip().lower()
    return ans == "y"


def test_buttons():
    print("\n" + "=" * 40)
    print("PHASE 2: BUTTON INPUT CHECK")
    print("=" * 40)
    print("NOTE: If a button is broken, press 'Ctrl+C' to SKIP it.\n")

    results = {}

    for name, pin in BUTTONS.items():
        print(f"Waiting for press: [ {name} ] on GPIO {pin}...")

        try:
            # 1. Wait for Press (LOW)
            while GPIO.input(pin) == GPIO.HIGH:
                time.sleep(0.05)

            # 2. Debounce/Confirm
            time.sleep(0.05)
            if GPIO.input(pin) == GPIO.LOW:
                print(f"   >>> SUCCESS: {name} detected!")
                results[name] = True

            # 3. Wait for Release (HIGH) so we don't accidentally trigger the next one
            while GPIO.input(pin) == GPIO.LOW:
                time.sleep(0.05)

        except KeyboardInterrupt:
            # This catches Ctrl+C
            print(f"   >>> SKIPPING {name} (User Interrupt)")
            results[name] = False
            # We must wait a tiny bit to clear the interrupt signal
            time.sleep(0.5)

    return results


def test_switch():
    print("\n" + "=" * 40)
    print("PHASE 3: SWITCH CHECK")
    print("=" * 40)

    name = "SW_RADAR_ENABLE"
    pin = SWITCHES[name]

    # Dynamic Logic: Check current state first
    is_currently_high = GPIO.input(pin)

    # Determine what to tell the user
    current_status = "OFF (Open)" if is_currently_high else "ON (Closed)"
    target_action = "CLOSE (Turn ON)" if is_currently_high else "OPEN (Turn OFF)"

    print(f"Switch '{name}' is currently: {current_status}")
    print(f"ACTION REQUIRED: Please {target_action} the switch.")

    try:
        # Wait for the state to flip to the opposite of what it started as
        while GPIO.input(pin) == is_currently_high:
            time.sleep(0.05)

        print(f"   >>> SUCCESS: Switch toggle detected!")
        return True

    except KeyboardInterrupt:
        print(f"   >>> SKIPPED Switch Test")
        return False


# --- MAIN ---
def main():
    try:
        setup_gpio()

        # Run Tests
        led_result = test_leds()
        time.sleep(1)
        btn_results = test_buttons()
        time.sleep(1)
        sw_result = test_switch()
        time.sleep(1)

        # Final Report
        print("\n\n")
        print("########################################")
        print("#             TEST REPORT              #")
        print("########################################")

        # LED Report
        print(f"LEDS VISUAL:       {'[PASS]' if led_result else '[FAIL]'}")

        # Button Report
        for name, res in btn_results.items():
            status = "[PASS]" if res else "[FAIL/SKIP]"
            print(f"{name:<18} {status}")

        # Switch Report
        print(f"SW_RADAR_ENABLE:   {'[PASS]' if sw_result else '[FAIL/SKIP]'}")
        print("########################################\n")

    except Exception as e:
        print(f"\nAn error occurred: {e}")
    finally:
        GPIO.cleanup()


if __name__ == "__main__":
    main()
