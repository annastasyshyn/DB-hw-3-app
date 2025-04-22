import unittest
import sys
import os

# Add the parent directory to the path so imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import test modules
from app.tests.test_passenger_router import TestPassengerRegistrationOperations, TestExemptionApplicationOperations
from app.tests.test_admin_router import TestFareTypeOperations, TestExemptionOperations
from app.tests.test_ticketing_router import TestFareCalculationOperations, TestTicketOperations
from app.tests.test_document_operations import TestDocumentStorageOperations

def run_tests():
    """Run all tests for the tariffs and exemptions system."""
    # Create a test suite combining all test cases
    test_suite = unittest.TestSuite()
    
    # Add tests from the test classes
    loader = unittest.TestLoader()
    
    # Add passenger router tests
    test_suite.addTest(loader.loadTestsFromTestCase(TestPassengerRegistrationOperations))
    test_suite.addTest(loader.loadTestsFromTestCase(TestExemptionApplicationOperations))
    
    # Add admin router tests
    test_suite.addTest(loader.loadTestsFromTestCase(TestFareTypeOperations))
    test_suite.addTest(loader.loadTestsFromTestCase(TestExemptionOperations))
    
    # Add ticketing router tests
    test_suite.addTest(loader.loadTestsFromTestCase(TestFareCalculationOperations))
    test_suite.addTest(loader.loadTestsFromTestCase(TestTicketOperations))
    
    # Add document operation tests
    test_suite.addTest(loader.loadTestsFromTestCase(TestDocumentStorageOperations))
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Return exit code based on test results
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    sys.exit(run_tests())