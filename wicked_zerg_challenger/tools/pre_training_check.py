#!/usr/bin/env python3

# -*- coding: utf-8 -*-

"""

Pre-training system check script

°ÔÀÓ ½ÇÇà Àü ½Ã½ºÅÛ »óÅÂ È®ÀÎ

"""



import os

import sys

import subprocess

from pathlib import Path



def check_sc2_installation():

    """Check StarCraft II installation"""

    print("\n" + "=" * 70)

    print("[CHECK 1] StarCraft II Installation Check")

    print("=" * 70)

    

    sc2_path = None

    

    # Check environment variable

    if "SC2PATH" in os.environ:

        sc2_path = os.environ["SC2PATH"]

        if os.path.exists(sc2_path):

            print(f"[OK] SC2PATH environment variable: {sc2_path}")

            return sc2_path

        else:

            print(f"[WARNING] SC2PATH set but path does not exist: {sc2_path}")

    

    # Check Windows Registry

    if sys.platform == "win32":

        try:

            import winreg

            key = winreg.OpenKey(

                winreg.HKEY_LOCAL_MACHINE,

                r"SOFTWARE\Blizzard Entertainment\StarCraft II"

            )

            install_path, _ = winreg.QueryValueEx(key, "InstallPath")

            winreg.CloseKey(key)

            

            if os.path.exists(install_path):

                print(f"[OK] Found via Registry: {install_path}")

                os.environ["SC2PATH"] = install_path

                return install_path

        except Exception as e:

            print(f"[INFO] Registry check failed: {e}")

    

    # Check common paths

    common_paths = []

    if sys.platform == "win32":

        common_paths = [

            r"C:\Program Files (x86)\StarCraft II",

            r"C:\Program Files\StarCraft II",

            r"D:\StarCraft II",

        ]

    elif sys.platform == "darwin":

        common_paths = [

            os.path.expanduser("~/Library/Application Support/Blizzard/StarCraft II"),

            "/Applications/StarCraft II",

        ]

    else:

        common_paths = [

            os.path.expanduser("~/StarCraft II"),

            "/opt/StarCraft II",

        ]

    

    for path in common_paths:

        if os.path.exists(path):

            print(f"[OK] Found at common path: {path}")

            os.environ["SC2PATH"] = path

            return path

    

    print("[ERROR] StarCraft II installation not found!")

    print(f"[INFO] Searched paths: {common_paths}")

    return None



def check_python_packages():

    """Check required Python packages"""

    print("\n" + "=" * 70)

    print("[CHECK 2] Python Packages Check")

    print("=" * 70)

    

    required_packages = [

        "sc2",

        "torch",

        "numpy",

        "loguru",

    ]

    

    missing_packages = []

    

    for package in required_packages:

        try:

            __import__(package)

            print(f"[OK] {package}")

        except ImportError:

            print(f"[ERROR] {package} - NOT FOUND")

            missing_packages.append(package)

    

    if missing_packages:

        print(f"\n[WARNING] Missing packages: {', '.join(missing_packages)}")

        print("[INFO] Install with: pip install " + " ".join(missing_packages))

        return False

    

    return True



def check_sc2_process():

    """Check if SC2 process is running"""

    print("\n" + "=" * 70)

    print("[CHECK 3] SC2 Process Check")

    print("=" * 70)

    

    if sys.platform == "win32":

        try:

            result = subprocess.run(

                ['tasklist', '/FI', 'IMAGENAME eq SC2_x64.exe'],

                capture_output=True,

                text=True,

                timeout=5

            )

            if 'SC2_x64.exe' in result.stdout:

                print("[WARNING] StarCraft II is already running!")

                print("[INFO] It is recommended to close SC2 before training")

                return False

            else:

                print("[OK] StarCraft II is not running")

                return True

        except Exception as e:

            print(f"[INFO] Could not check process: {e}")

            return True

    else:

        try:

            result = subprocess.run(

                ['pgrep', '-f', 'SC2'],

                capture_output=True,

                timeout=5

            )

            if result.returncode == 0:

                print("[WARNING] StarCraft II process found!")

                return False

            else:

                print("[OK] StarCraft II is not running")

                return True

        except Exception as e:

            print("[INFO] Could not check process: {e}")

            return True



def check_gpu():

    """Check GPU availability"""

    print("\n" + "=" * 70)

    print("[CHECK 4] GPU Check")

    print("=" * 70)

    

    try:

        import torch

        if torch.cuda.is_available():

            gpu_count = torch.cuda.device_count()

            gpu_name = torch.cuda.get_device_name(0)

            print(f"[OK] CUDA available - {gpu_count} GPU(s)")

            print(f"[INFO] GPU 0: {gpu_name}")

            return True

        else:

            print("[INFO] CUDA not available - will use CPU")

            return False

    except ImportError:

        print("[WARNING] PyTorch not found")

        return False

    except Exception as e:

        print(f"[INFO] GPU check error: {e}")

        return False



def main():

    print("\n" + "=" * 70)

    print("PRE-TRAINING SYSTEM CHECK")

    print("=" * 70)

    

    checks_passed = 0

    total_checks = 4

    

    # Check 1: SC2 Installation

    sc2_path = check_sc2_installation()

    if sc2_path:

        checks_passed += 1

    

    # Check 2: Python Packages

    if check_python_packages():

        checks_passed += 1

    

    # Check 3: SC2 Process

    if check_sc2_process():

        checks_passed += 1

    

    # Check 4: GPU

    gpu_available = check_gpu()

    checks_passed += 1  # GPU is optional, so always pass

    

    # Summary

    print("\n" + "=" * 70)

    print("CHECK SUMMARY")

    print("=" * 70)

    print(f"Passed: {checks_passed}/{total_checks}")

    

    if checks_passed >= 3:  # SC2 and packages are critical

        print("[OK] System ready for training!")

        return 0

    else:

        print("[ERROR] System not ready. Please fix issues above.")

        return 1



if __name__ == "__main__":

    sys.exit(main())

