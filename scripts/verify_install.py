#!/usr/bin/env python3
"""
AstraGuard Installation Verification Script

Verifies environment setup and dependencies before running the system.
"""

import sys
import importlib
import subprocess
from typing import List, Tuple


def check_python_version() -> bool:
    """Verify Python version is 3.9+"""
    version = sys.version_info
    if version.major == 3 and version.minor >= 9:
        print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"✗ Python {version.major}.{version.minor} (requires 3.9+)")
        return False


def check_dependencies() -> Tuple[bool, List[str]]:
    """Check all required dependencies are installed"""
    required = [
        'numpy',
        'pandas',
        'sklearn',
        'pathway',
        'streamlit',
        'altair',
        'fastapi',
        'sentence_transformers',
        'torch',
        'pytest',
        'loguru'
    ]
    
    missing = []
    for package in required:
        try:
            importlib.import_module(package)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} (missing)")
            missing.append(package)
    
    return len(missing) == 0, missing


def check_directory_structure() -> bool:
    """Verify required directories exist"""
    import os
    
    required_dirs = [
        'memory_engine',
        'anomaly_agent',
        'response_orchestrator',
        'encoder',
        'pathway_ingestion',
        'dashboard',
        'tests',
        'examples',
        'docs'
    ]
    
    all_exist = True
    for directory in required_dirs:
        if os.path.isdir(directory):
            print(f"✓ {directory}/")
        else:
            print(f"✗ {directory}/ (missing)")
            all_exist = False
    
    return all_exist


def verify_installation() -> bool:
    """Run all verification checks"""
    print("=" * 60)
    print("AstraGuard Installation Verification")
    print("=" * 60)
    
    print("\n1. Checking Python version...")
    python_ok = check_python_version()
    
    print("\n2. Checking dependencies...")
    deps_ok, missing = check_dependencies()
    
    print("\n3. Checking directory structure...")
    dirs_ok = check_directory_structure()
    
    print("\n" + "=" * 60)
    
    if python_ok and deps_ok and dirs_ok:
        print("✓ All checks passed! System ready to run.")
        print("\nTo start the dashboard:")
        print("  streamlit run dashboard/app.py")
        print("\nTo run the demo:")
        print("  python examples/run_demo.py")
        return True
    else:
        print("✗ Installation incomplete. Please fix the issues above.")
        if missing:
            print(f"\nInstall missing packages:")
            print(f"  pip install {' '.join(missing)}")
        return False


if __name__ == "__main__":
    success = verify_installation()
    sys.exit(0 if success else 1)
