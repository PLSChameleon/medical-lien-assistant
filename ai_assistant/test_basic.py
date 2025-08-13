#!/usr/bin/env python3
"""
Basic tests for AI Assistant
Run with: python test_basic.py
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from config import Config
from case_manager import CaseManager

class TestConfig(unittest.TestCase):
    """Test configuration management"""
    
    def test_default_values(self):
        """Test default configuration values"""
        self.assertEqual(Config.LOG_LEVEL, "INFO")
        self.assertEqual(Config.MAX_EMAIL_RESULTS, 10)
        self.assertIsInstance(Config.GMAIL_SCOPES, list)
        self.assertGreater(len(Config.GMAIL_SCOPES), 0)
    
    def test_file_path_generation(self):
        """Test file path generation"""
        path = Config.get_file_path("test.txt")
        self.assertIsInstance(path, str)
        self.assertTrue(path.endswith("test.txt"))
    
    @patch.dict(os.environ, {"OPEN_AI_API_KEY": "test_key"})
    def test_validate_required_vars_success(self):
        """Test successful validation of required variables"""
        # Should not raise an exception
        result = Config.validate_required_vars()
        self.assertTrue(result)
    
    @patch.dict(os.environ, {}, clear=True)
    def test_validate_required_vars_failure(self):
        """Test validation failure for missing variables"""
        with self.assertRaises(ValueError) as cm:
            Config.validate_required_vars()
        self.assertIn("Missing required environment variables", str(cm.exception))

class TestCaseManager(unittest.TestCase):
    """Test case management functionality"""
    
    def setUp(self):
        """Set up test data"""
        # Create test DataFrame
        self.test_data = pd.DataFrame([
            ["CMS001", "PV001", "Active", "John Doe", "2024-01-15", "", "", "", "", "", "", "", "Smith Law", "", "", "", "", "", "john@law.com", "555-1234"],
            ["CMS002", "PV002", "Closed", "Jane Smith", "2024-02-20", "", "", "", "", "", "", "", "Jones & Associates", "", "", "", "", "", "jane@jones.com", "555-5678"],
        ])
    
    @patch('case_manager.pd.read_excel')
    def test_load_cases_success(self, mock_read_excel):
        """Test successful case loading"""
        mock_read_excel.return_value = self.test_data
        
        cm = CaseManager("test.xlsx")
        self.assertFalse(cm.df.empty)
        self.assertEqual(len(cm.df), 2)
    
    @patch('case_manager.pd.read_excel')
    def test_load_cases_file_not_found(self, mock_read_excel):
        """Test handling of missing case file"""
        mock_read_excel.side_effect = FileNotFoundError("File not found")
        
        cm = CaseManager("missing.xlsx")
        self.assertTrue(cm.df.empty)
    
    @patch('case_manager.pd.read_excel')
    def test_get_case_by_pv_found(self, mock_read_excel):
        """Test finding case by PV number"""
        mock_read_excel.return_value = self.test_data
        
        cm = CaseManager("test.xlsx")
        case = cm.get_case_by_pv("PV001")
        
        self.assertIsNotNone(case)
        self.assertEqual(case["Name"], "John Doe")
        self.assertEqual(case["PV"], "PV001")
        self.assertEqual(case["Attorney Email"], "john@law.com")
    
    @patch('case_manager.pd.read_excel')
    def test_get_case_by_pv_not_found(self, mock_read_excel):
        """Test case not found by PV number"""
        mock_read_excel.return_value = self.test_data
        
        cm = CaseManager("test.xlsx")
        case = cm.get_case_by_pv("PV999")
        
        self.assertIsNone(case)
    
    @patch('case_manager.pd.read_excel')
    def test_get_case_by_name_found(self, mock_read_excel):
        """Test finding case by name"""
        mock_read_excel.return_value = self.test_data
        
        cm = CaseManager("test.xlsx")
        case = cm.get_case_by_name("Jane Smith")
        
        self.assertIsNotNone(case)
        self.assertEqual(case["Name"], "Jane Smith")
        self.assertEqual(case["PV"], "PV002")
    
    @patch('case_manager.pd.read_excel')
    def test_get_case_by_name_case_insensitive(self, mock_read_excel):
        """Test case-insensitive name search"""
        mock_read_excel.return_value = self.test_data
        
        cm = CaseManager("test.xlsx")
        case = cm.get_case_by_name("john doe")  # lowercase
        
        self.assertIsNotNone(case)
        self.assertEqual(case["Name"], "John Doe")
    
    @patch('case_manager.pd.read_excel')
    def test_format_case_safe_access(self, mock_read_excel):
        """Test safe formatting of case data with incomplete rows"""
        # Create test data with incomplete row
        incomplete_data = pd.DataFrame([
            ["CMS001", "PV001", "Active"],  # Missing many columns
        ])
        mock_read_excel.return_value = incomplete_data
        
        cm = CaseManager("test.xlsx")
        case = cm.get_case_by_pv("PV001")
        
        self.assertIsNotNone(case)
        self.assertEqual(case["PV"], "PV001")
        self.assertEqual(case["Name"], "")  # Should default to empty string
        self.assertEqual(case["Attorney Email"], "")  # Should default to empty string

def run_tests():
    """Run all tests"""
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return success status
    return result.wasSuccessful()

def main():
    """Main test function"""
    print("Running AI Assistant Basic Tests")
    print("=" * 50)
    
    success = run_tests()
    
    if success:
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)