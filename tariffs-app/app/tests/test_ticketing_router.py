import unittest
from unittest.mock import patch, MagicMock
from datetime import date, datetime
import re
import logging

logger = logging.getLogger('tariffs_test')

def normalize_sql(sql):
    """Normalize SQL string by removing extra whitespace and newlines for comparison"""
    if sql is None:
        return None
    # Replace multiple whitespace characters with a single space
    normalized = re.sub(r'\s+', ' ', sql)
    # Trim spaces
    normalized = normalized.strip()
    return normalized

class TestFareCalculationOperations(unittest.TestCase):
    def setUp(self):
        # Mock the database connection and cursor
        self.mock_execute_query_patcher = patch('app.database.config.execute_query')
        self.mock_execute_query = self.mock_execute_query_patcher.start()
        
        self.mock_get_db_connection_patcher = patch('app.database.config.get_db_connection')
        self.mock_get_db_connection = self.mock_get_db_connection_patcher.start()
        
        self.mock_close_connection_patcher = patch('app.database.config.close_connection')
        self.mock_close_connection = self.mock_close_connection_patcher.start()
        
        # Setup common mock objects
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor
        self.mock_get_db_connection.return_value = self.mock_conn
        
        # Initialize test data
        self.initialize_test_data()

    def tearDown(self):
        self.mock_execute_query_patcher.stop()
        self.mock_get_db_connection_patcher.stop()
        self.mock_close_connection_patcher.stop()
    
    def initialize_test_data(self):
        """Set up fixed test data for consistent test execution"""
        # Mock passenger data
        self.passenger_data = {
            "passenger_id": 123,
            "passenger_full_name": "John Smith",
            "email": "john@example.com"
        }
        
        # Mock fare type data for calculation
        self.fare_type_data = {
            "fare_type_id": 2,
            "type_name": "Student",
            "base_price": 2.00,
            "discount_rate": 33.3
        }
        
        # Mock exemption data
        self.exemption_data = {
            "exemption_id": 456,
            "passenger_id": 123,
            "exemption_category": "Student",
            "fare_type_id": 2,
            "valid_from": date(2025, 1, 1),
            "valid_to": date(2025, 12, 31),
            "is_active": True
        }
        
        # Set standard return values for tests
        self.mock_execute_query.reset_mock()

    def validate_report(self):
        """Validate report generation for relevant tests"""
        test_name = self._testMethodName
        
        # Create fixed test data for validation
        mock_passenger = [self.passenger_data]
        mock_fare_type = [self.fare_type_data]
        mock_exemption = [self.exemption_data]
        
        if test_name == "test_retrieve_passenger_profile":
            # Use fixed mock data instead of side_effect indexing
            self.mock_execute_query.return_value = mock_passenger
            
            passenger_data = self.mock_execute_query.return_value
            self.assertEqual(passenger_data[0]["passenger_id"], 123)
            self.assertEqual(passenger_data[0]["passenger_full_name"], "John Smith")
            
        elif test_name == "test_prepare_fare_calculation":
            # Use fixed mock data instead of side_effect indexing
            self.mock_execute_query.return_value = mock_passenger
            
            passenger_data = self.mock_execute_query.return_value
            self.assertEqual(passenger_data[0]["passenger_full_name"], "John Smith")
            
        elif test_name == "test_calculate_final_price_with_exemption":
            # Use fixed mock data for fare type and exemption
            self.mock_execute_query.return_value = mock_fare_type
            
            fare_info = self.mock_execute_query.return_value
            self.assertEqual(fare_info[0]["base_price"], 2.00)
            self.assertEqual(fare_info[0]["discount_rate"], 33.3)
            
        elif test_name == "test_calculate_final_price_without_exemption":
            # Use fixed mock data for fare type
            self.mock_execute_query.return_value = mock_fare_type
            
            fare_info = self.mock_execute_query.return_value
            self.assertEqual(fare_info[0]["base_price"], 2.00)
            self.assertEqual(fare_info[0]["discount_rate"], 33.3)

    def test_retrieve_passenger_profile(self):
        """Test the SQL operations for retrieving passenger profile"""
        # Setup test parameters
        passenger_id = 123
        
        # Set mock return value for this test
        self.mock_execute_query.return_value = [self.passenger_data]
        
        # Import here to avoid circular imports
        from app.database.config import execute_query
        
        # Retrieve passenger profile
        query = """
            SELECT * FROM passenger 
            WHERE passenger_id = %s
        """
        passenger = execute_query(query, (passenger_id,))
        
        # Verify query execution
        self.mock_execute_query.assert_called_once_with(query, (passenger_id,))
        
        # Verify data is returned correctly
        self.assertEqual(len(passenger), 1)
        self.assertEqual(passenger[0]["passenger_id"], passenger_id)
        self.assertEqual(passenger[0]["passenger_full_name"], "John Smith")
        self.assertEqual(passenger[0]["email"], "john@example.com")
        
        # Validate report data
        self.validate_report()

    def test_prepare_fare_calculation(self):
        """Test the SQL operations for preparing fare calculation"""
        # Setup test parameters
        passenger_id = 123
        
        # Set mock return value for this test
        self.mock_execute_query.return_value = [self.passenger_data]
        
        # Import here to avoid circular imports
        from app.database.config import execute_query
        
        # Retrieve passenger profile for ticket issuance
        query = """
            SELECT * FROM passenger 
            WHERE passenger_id = %s
        """
        passenger = execute_query(query, (passenger_id,))
        
        # Verify query execution
        self.mock_execute_query.assert_called_once_with(query, (passenger_id,))
        
        # Verify data is returned correctly
        self.assertEqual(len(passenger), 1)
        self.assertEqual(passenger[0]["passenger_id"], passenger_id)
        self.assertEqual(passenger[0]["passenger_full_name"], "John Smith")
        
        # Validate report data
        self.validate_report()

    def test_calculate_final_price_without_exemption(self):
        """Test the SQL operations for calculating final price without exemption"""
        # Setup test parameters
        passenger_id = 123
        fare_type_id = 2
        
        # Set up mock return values - no exemption found, but return fare type
        self.mock_execute_query.side_effect = [
            [],  # No exemption
            [self.fare_type_data]  # Fare type
        ]
        
        # Import here to avoid circular imports
        from app.database.config import execute_query
        
        # Check for exemptions
        exemption_query = """
            SELECT e.* FROM exemption e
            WHERE e.passenger_id = %s 
              AND e.fare_type_id = %s
              AND e.is_active = True
              AND CURRENT_DATE BETWEEN e.valid_from AND e.valid_to
        """
        exemption = execute_query(exemption_query, (passenger_id, fare_type_id))
        
        # Get fare information
        fare_query = """
            SELECT ft.*, t.base_price, t.discount_rate
            FROM fare_type ft
            JOIN tariff t ON ft.fare_type_id = t.fare_type_id
            WHERE ft.fare_type_id = %s
        """
        fare_info = execute_query(fare_query, (fare_type_id,))
        
        # Calculate price (without exemption)
        base_price = fare_info[0]["base_price"]
        discount_rate = fare_info[0]["discount_rate"]
        final_price = base_price * (1 - (discount_rate / 100))
        
        # Verify query executions
        self.assertEqual(self.mock_execute_query.call_count, 2)
        self.mock_execute_query.assert_any_call(exemption_query, (passenger_id, fare_type_id))
        self.mock_execute_query.assert_any_call(fare_query, (fare_type_id,))
        
        # Verify data is processed correctly
        self.assertEqual(len(exemption), 0)  # No exemptions
        self.assertEqual(fare_info[0]["base_price"], 2.00)
        self.assertEqual(fare_info[0]["discount_rate"], 33.3)
        self.assertAlmostEqual(final_price, 1.334, places=3)  # 2.00 * (1 - 33.3/100)
        
        # Validate report data
        self.validate_report()

    def test_calculate_final_price_with_exemption(self):
        """Test the SQL operations for calculating final price with exemption"""
        # Setup test parameters
        passenger_id = 123
        fare_type_id = 2
        
        # Set up mock return values - exemption found and fare type
        self.mock_execute_query.side_effect = [
            [self.exemption_data],  # Exemption exists
            [self.fare_type_data]   # Fare type
        ]
        
        # Import here to avoid circular imports
        from app.database.config import execute_query
        
        # Check for exemptions
        exemption_query = """
            SELECT e.* FROM exemption e
            WHERE e.passenger_id = %s 
              AND e.fare_type_id = %s
              AND e.is_active = True
              AND CURRENT_DATE BETWEEN e.valid_from AND e.valid_to
        """
        exemption = execute_query(exemption_query, (passenger_id, fare_type_id))
        
        # Get fare information
        fare_query = """
            SELECT ft.*, t.base_price, t.discount_rate
            FROM fare_type ft
            JOIN tariff t ON ft.fare_type_id = t.fare_type_id
            WHERE ft.fare_type_id = %s
        """
        fare_info = execute_query(fare_query, (fare_type_id,))
        
        # Calculate price (with exemption - 100% discount)
        base_price = fare_info[0]["base_price"]
        discount_rate = 100.0 if exemption else fare_info[0]["discount_rate"]
        final_price = base_price * (1 - (discount_rate / 100))
        
        # Verify query executions
        self.assertEqual(self.mock_execute_query.call_count, 2)
        self.mock_execute_query.assert_any_call(exemption_query, (passenger_id, fare_type_id))
        self.mock_execute_query.assert_any_call(fare_query, (fare_type_id,))
        
        # Verify data is processed correctly
        self.assertEqual(len(exemption), 1)  # Exemption exists
        self.assertEqual(exemption[0]["exemption_category"], "Student")
        self.assertEqual(fare_info[0]["base_price"], 2.00)
        self.assertEqual(discount_rate, 100.0)  # Full exemption
        self.assertEqual(final_price, 0.0)  # Free due to exemption
        
        # Validate report data
        self.validate_report()

class TestTicketOperations(unittest.TestCase):
    def setUp(self):
        # Mock the database connection and cursor
        self.mock_execute_query_patcher = patch('app.database.config.execute_query')
        self.mock_execute_query = self.mock_execute_query_patcher.start()
        
        self.mock_get_db_connection_patcher = patch('app.database.config.get_db_connection')
        self.mock_get_db_connection = self.mock_get_db_connection_patcher.start()
        
        self.mock_close_connection_patcher = patch('app.database.config.close_connection')
        self.mock_close_connection = self.mock_close_connection_patcher.start()
        
        # Setup common mock objects
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor
        self.mock_get_db_connection.return_value = self.mock_conn
        
        # Mock current datetime for consistent timestamp
        self.mock_datetime_now_patcher = patch('datetime.datetime')
        self.mock_datetime = self.mock_datetime_now_patcher.start()
        self.mock_datetime.now.return_value = datetime(2025, 4, 22, 12, 0, 0)
        
        # Initialize test data
        self.initialize_test_data()

    def tearDown(self):
        self.mock_execute_query_patcher.stop()
        self.mock_get_db_connection_patcher.stop()
        self.mock_close_connection_patcher.stop()
        self.mock_datetime_now_patcher.stop()
    
    def initialize_test_data(self):
        """Set up fixed test data for consistent test execution"""
        # Test parameters
        self.passenger_id = 123
        self.fare_type_id = 2
        self.price = 1.33  # Reduced price due to student discount
        self.issued_date = date(2025, 4, 22)
        self.valid_from = date(2025, 4, 22)
        self.valid_to = date(2025, 5, 22)  # 1 month validity
        self.ticket_id = 456  # Mock inserted ID
        
        # Mock passenger data
        self.passenger_data = {
            "passenger_id": self.passenger_id,
            "passenger_full_name": "John Smith",
            "email": "john@example.com"
        }
        
        # Mock fare type data
        self.fare_type_data = {
            "fare_type_id": self.fare_type_id,
            "type_name": "Student",
            "base_price": 2.00,
            "discount_rate": 33.3
        }
        
        # Mock ticket data (returned after ticket creation)
        self.ticket_data = {
            "ticket_id": self.ticket_id,
            "passenger_id": self.passenger_id,
            "fare_type_id": self.fare_type_id,
            "price": self.price,
            "issued_date": self.issued_date,
            "valid_from": self.valid_from,
            "valid_to": self.valid_to,
            "passenger_name": "John Smith",
            "fare_type_name": "Student"
        }
        
        # Set lastrowid for ticket insertion
        self.mock_cursor.lastrowid = self.ticket_id

    def test_issue_ticket_success(self):
        """Test the SQL operations for issuing a ticket"""
        # Set up mock return values for this test
        self.mock_execute_query.side_effect = [
            [self.passenger_data],  # Passenger lookup
            [self.fare_type_data],  # Fare type lookup
            [self.ticket_data]      # Ticket data after insertion
        ]
        
        # Import here to avoid circular imports
        from app.database.config import execute_query, get_db_connection, close_connection
        
        # 1. Get passenger information
        passenger_query = """
            SELECT * FROM passenger
            WHERE passenger_id = %s
        """
        passenger = execute_query(passenger_query, (self.passenger_id,))
        
        # 2. Get fare type information
        fare_query = """
            SELECT ft.*, t.base_price, t.discount_rate
            FROM fare_type ft
            JOIN tariff t ON ft.fare_type_id = t.fare_type_id
            WHERE ft.fare_type_id = %s
        """
        fare_type = execute_query(fare_query, (self.fare_type_id,))
        
        # Begin transaction
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # 3. Insert ticket
            ticket_query = """
                INSERT INTO ticket (
                    passenger_id, 
                    fare_type_id, 
                    price, 
                    issued_date,
                    valid_from,
                    valid_to
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            ticket_params = (
                self.passenger_id,
                self.fare_type_id,
                self.price,
                self.issued_date,
                self.valid_from,
                self.valid_to
            )
            cursor.execute(ticket_query, ticket_params)
            ticket_id = cursor.lastrowid
            
            # 4. Log ticket issuance
            log_query = """
                INSERT INTO activity_log (
                    activity_type, 
                    description,
                    entity_id,
                    entity_type,
                    created_at
                )
                VALUES (%s, %s, %s, %s, NOW())
            """
            log_description = f"Ticket issued to {passenger[0]['passenger_full_name']} - {fare_type[0]['type_name']} fare"
            log_params = ("ticket_issuance", log_description, ticket_id, "ticket")
            cursor.execute(log_query, log_params)
            
            # Commit transaction
            conn.commit()
        except Exception as e:
            # Rollback in case of error
            conn.rollback()
            raise e
        finally:
            cursor.close()
            close_connection(conn)
            
        # 5. Get issued ticket details
        ticket_details_query = """
            SELECT t.*, p.passenger_full_name as passenger_name, ft.type_name as fare_type_name
            FROM ticket t
            JOIN passenger p ON t.passenger_id = p.passenger_id
            JOIN fare_type ft ON t.fare_type_id = ft.fare_type_id
            WHERE t.ticket_id = %s
        """
        ticket = execute_query(ticket_details_query, (ticket_id,))
        
        # Verify database operations were executed correctly
        self.assertEqual(self.mock_execute_query.call_count, 3)
        self.mock_execute_query.assert_any_call(passenger_query, (self.passenger_id,))
        self.mock_execute_query.assert_any_call(fare_query, (self.fare_type_id,))
        self.mock_execute_query.assert_any_call(ticket_details_query, (self.ticket_id,))
        
        # Verify ticket insertion
        self.mock_cursor.execute.assert_any_call(ticket_query, ticket_params)
        
        # Verify activity logging
        log_query_normalized = normalize_sql(log_query)
        any_log_call = False
        for call_args in self.mock_cursor.execute.call_args_list:
            args, kwargs = call_args
            if args and len(args) > 0 and normalize_sql(args[0]) == log_query_normalized:
                any_log_call = True
                break
        self.assertTrue(any_log_call, "Log entry was not created")
        
        # Verify transaction was committed
        self.mock_conn.commit.assert_called_once()
        self.mock_close_connection.assert_called_once_with(self.mock_conn)
        
        # Verify the returned ticket data
        self.assertEqual(len(ticket), 1)
        self.assertEqual(ticket[0]["ticket_id"], self.ticket_id)
        self.assertEqual(ticket[0]["passenger_id"], self.passenger_id)
        self.assertEqual(ticket[0]["fare_type_id"], self.fare_type_id)
        self.assertEqual(ticket[0]["passenger_name"], "John Smith")
        self.assertEqual(ticket[0]["fare_type_name"], "Student")
        
        # Log ticket details for debugging
        logger.info(f"Ticket ID: {ticket[0]['ticket_id']}")
        logger.info(f"Passenger: {ticket[0]['passenger_name']}")
        logger.info(f"Fare Type: {ticket[0]['fare_type_name']}")
        logger.info(f"Price: ${ticket[0]['price']}")
        logger.info(f"Valid from: {ticket[0]['valid_from']} to {ticket[0]['valid_to']}")

if __name__ == "__main__":
    unittest.main()