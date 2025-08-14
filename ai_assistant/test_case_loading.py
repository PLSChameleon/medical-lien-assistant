#!/usr/bin/env python3
"""
Test script to debug case loading issue
"""

import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from case_manager import CaseManager

print("Testing CaseManager initialization...")
print("-" * 50)

try:
    # Initialize CaseManager
    case_manager = CaseManager()
    
    print(f"[SUCCESS] CaseManager initialized successfully")
    print(f"[INFO] DataFrame shape: {case_manager.df.shape}")
    print(f"[INFO] Cases loaded: {len(case_manager.df)} cases")
    
    if not case_manager.df.empty:
        print("\n[SAMPLE] First case:")
        first_row = case_manager.df.iloc[0]
        formatted_case = case_manager.format_case(first_row)
        for key, value in formatted_case.items():
            print(f"  {key}: {value}")
    else:
        print("\n[WARNING] DataFrame is empty!")
        
except Exception as e:
    print(f"[ERROR] Error initializing CaseManager: {e}")
    import traceback
    print("\nFull traceback:")
    print(traceback.format_exc())

print("-" * 50)
print("Test complete")