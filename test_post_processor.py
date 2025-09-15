import music_post_processor
from pathlib import Path
import shutil

def run_real_file_test():
    """
    Tests the post-processing module on a real, pre-existing audio file.
    It creates a copy of the file first to preserve the original.
    """
    print("--- Starting Post-Processor Test on Real Audio File ---")

    # --- 1. Define the paths for the original and test files ---
    original_file = Path("music_generated/world_theme_2025-09-15_03-00-06.wav")
    test_file = Path("music_generated/POST_PROCESSOR_TEST_FILE.wav")

    # --- 2. Check if the original file exists ---
    if not original_file.exists():
        print(f"\nError: The source file was not found at '{original_file}'")
        print("Please make sure the file exists before running the test.")
        print("\nTest FAILED.")
        return

    # --- 3. Create a safe copy to test on ---
    print(f"Creating a temporary copy for testing at: {test_file}")
    shutil.copy(original_file, test_file)

    # --- 4. Run the post-processor on the copy ---
    success = music_post_processor.process_and_replace(test_file)

    if success:
        print("\nTest PASSED. The copied file was processed successfully.")
        print(f"You can now listen to '{test_file.name}' to hear the fade effects.")
        print("The original file remains untouched.")
    else:
        print("\nTest FAILED. Check the error messages above.")


if __name__ == "__main__":
    run_real_file_test()