import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("diagnostic")

print(f"Python version: {sys.version}")

try:
    print("Testing win10toast import...")
    from win10toast import ToastNotifier
    print("win10toast import successful")
    toaster = ToastNotifier()
    print("ToastNotifier instance created")
except Exception as e:
    print(f"win10toast import/init FAILED: {e}")
    import traceback
    traceback.print_exc()

try:
    print("\nTesting pywinauto import...")
    import pywinauto
    print("pywinauto import successful")
except Exception as e:
    print(f"pywinauto import FAILED: {e}")
    import traceback
    traceback.print_exc()

try:
    import ctypes
    # Check COM threading mode
    # CoInitializeEx(None, COINIT_APARTMENTTHREADED) returns S_FALSE (1) if already initialized as STA
    # or RPC_E_CHANGED_MODE (0x80010106) if already initialized as MTA
    res = ctypes.windll.ole32.CoInitializeEx(None, 2) # 2 = COINIT_APARTMENTTHREADED (STA)
    print(f"\nCoInitializeEx(STA) result: {res} (0=S_OK, 1=S_FALSE/Already Init, 0x80010106=MTA already)")
    if res == 0:
        ctypes.windll.ole32.CoUninitialize()
except Exception as e:
    print(f"COM check failed: {e}")
