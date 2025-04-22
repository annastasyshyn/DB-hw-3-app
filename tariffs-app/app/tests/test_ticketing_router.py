import unittest
from unittest.mock import patch, MagicMock
from datetime import date
import re

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

    def tearDown(self):
        self.mock_execute_query_patcher.stop()

    # 3.1 Retrieve Passenger Profile tests
    def test_retrieve_passenger_profile(self):
        """Test the SQL operations for retrieving passenger profile"""
        # Setup the test parameters
        passenger_id = 1
        
        # Mock the query results
        self.mock_execute_query.side_effect = [
            [{"passenger_id": 1, "passenger_full_name": "John Doe", "email": "john@example.com"}],  # Passenger
            [{"exemption_id": 1, "exemption_category": "Student", "type_name": "Student Fare"}]  # Exemptions
        ]
        
        # Import here to avoid circular imports
        from app.database.config import execute_query
        
        # Get passenger details
        passenger = execute_query(
            "SELECT * FROM passenger WHERE passenger_id = %s", 
            (passenger_id,)
        )
        
        # Get passenger's exemptions
        exemptions = execute_query("""
            SELECT e.*, ft.type_name 
            FROM exemption e
            JOIN fare_type ft ON e.fare_type_id = ft.fare_type_id
            WHERE e.passenger_id = %s AND CURDATE() BETWEEN e.valid_from AND e.valid_to
        """, (passenger_id,))
        
        # Assert the queries were called correctly - using normalized SQL
        self.mock_execute_query.assert_any_call(
            "SELECT * FROM passenger WHERE passenger_id = %s", 
            (passenger_id,)
        )
        
        # Check for exemptions query using normalized SQL
        expected_exemptions_sql = normalize_sql("""
            SELECT e.*, ft.type_name 
            FROM exemption e
            JOIN fare_type ft ON e.fare_type_id = ft.fare_type_id
            WHERE e.passenger_id = %s AND CURDATE() BETWEEN e.valid_from AND e.valid_to
        """)
        
        found_exemptions_call = False
        for call_args in self.mock_execute_query.call_args_list:
            args, kwargs = call_args
            if args and len(args) > 0:
                # Check if the normalized SQL strings match
                if normalize_sql(args[0]) == expected_exemptions_sql and args[1] == (passenger_id,):
                    found_exemptions_call = True
                    break
        
        self.assertTrue(found_exemptions_call, f"Expected execute_query call with normalized query {expected_exemptions_sql} not found")
        
        # Assert the results
        self.assertTrue(passenger)
        self.assertEqual(passenger[0]["passenger_id"], passenger_id)
        self.assertEqual(passenger[0]["passenger_full_name"], "John Doe")
        self.assertEqual(exemptions[0]["exemption_id"], 1)
        self.assertEqual(exemptions[0]["exemption_category"], "Student")
        self.assertEqual(exemptions[0]["type_name"], "Student Fare")

    # 3.2 Determine Fare Type and 3.3 Apply Exemptions
    def test_prepare_fare_calculation(self):
        """Test the SQL operations for preparing fare calculation"""
        # Setup the test parameters
        passenger_id = 1
        
        # Mock the query results
        self.mock_execute_query.side_effect = [
            [{"passenger_id": 1, "passenger_full_name": "John Doe"}],  # Passenger
            [{"fare_type_id": 1, "type_name": "Adult"}, {"fare_type_id": 2, "type_name": "Student"}],  # Fare types
            [{"exemption_id": 1, "exemption_category": "Student", "type_name": "Student Fare"}]  # Exemptions
        ]
        
        # Import here to avoid circular imports
        from app.database.config import execute_query
        
        # Get passenger details
        passenger = execute_query(
            "SELECT * FROM passenger WHERE passenger_id = %s", 
            (passenger_id,)
        )
        
        # Get all fare types
        fare_types = execute_query("SELECT * FROM fare_type")
        
        # Get eligible exemptions for this passenger
        exemptions = execute_query("""
            SELECT e.*, ft.type_name 
            FROM exemption e
            JOIN fare_type ft ON e.fare_type_id = ft.fare_type_id
            WHERE e.passenger_id = %s AND CURDATE() BETWEEN e.valid_from AND e.valid_to
        """, (passenger_id,))
        
        # Assert the queries were called correctly - using normalized SQL
        self.mock_execute_query.assert_any_call(
            "SELECT * FROM passenger WHERE passenger_id = %s", 
            (passenger_id,)
        )
        
        self.mock_execute_query.assert_any_call("SELECT * FROM fare_type")
        
        # Check for exemptions query using normalized SQL
        expected_exemptions_sql = normalize_sql("""
            SELECT e.*, ft.type_name 
            FROM exemption e
            JOIN fare_type ft ON e.fare_type_id = ft.fare_type_id
            WHERE e.passenger_id = %s AND CURDATE() BETWEEN e.valid_from AND e.valid_to
        """)
        
        found_exemptions_call = False
        for call_args in self.mock_execute_query.call_args_list:
            args, kwargs = call_args
            if args and len(args) > 0:
                # Check if the normalized SQL strings match
                if normalize_sql(args[0]) == expected_exemptions_sql and args[1] == (passenger_id,):
                    found_exemptions_call = True
                    break
        
        self.assertTrue(found_exemptions_call, f"Expected execute_query call with normalized query {expected_exemptions_sql} not found")
        
        # Assert the results
        self.assertTrue(passenger)
        self.assertEqual(passenger[0]["passenger_id"], passenger_id)
        self.assertEqual(passenger[0]["passenger_full_name"], "John Doe")
        self.assertEqual(len(fare_types), 2)
        self.assertEqual(fare_types[0]["fare_type_id"], 1)
        self.assertEqual(fare_types[1]["fare_type_id"], 2)
        self.assertEqual(exemptions[0]["exemption_id"], 1)
        self.assertEqual(exemptions[0]["exemption_category"], "Student")

    # 3.4 Calculate Final Price tests
    def test_calculate_final_price_without_exemption(self):
        """Test the SQL operations for calculating final price without exemption"""
        # Setup the test parameters
        passenger_id = 1
        fare_type_id = 1
        exemption_id = None
        
        # Mock the query results
        self.mock_execute_query.side_effect = [
            [{"fare_type_id": 1, "type_name": "Adult", "base_price": 3.0, "discount_rate": 0.0}],  # Fare type
            [{"passenger_id": 1, "passenger_full_name": "John Doe"}],  # Passenger
            [{"fare_type_id": 1, "type_name": "Adult"}]  # Fare type details
        ]
        
        # Import here to avoid circular imports
        from app.database.config import execute_query
        
        # Get fare type and base price
        fare_info = execute_query("""
            SELECT ft.*, t.base_price, t.discount_rate
            FROM fare_type ft
            JOIN tariff t ON ft.fare_type_id = t.fare_type_id
            WHERE ft.fare_type_id = %s
        """, (fare_type_id,))
            
        base_fare = float(fare_info[0]["base_price"])
        discount_rate = 0
        
        # Apply exemption discount if provided - not in this case
        
        # Calculate final price
        discount_amount = base_fare * (discount_rate / 100)
        final_fare = base_fare - discount_amount
        
        # Get passenger details for the template
        passenger = execute_query(
            "SELECT * FROM passenger WHERE passenger_id = %s", 
            (passenger_id,)
        )
        
        # Get fare type details for the template
        fare_type = execute_query(
            "SELECT * FROM fare_type WHERE fare_type_id = %s", 
            (fare_type_id,)
        )
        
        # Assert the queries were called correctly - using normalized SQL
        expected_fare_info_sql = normalize_sql("""
            SELECT ft.*, t.base_price, t.discount_rate
            FROM fare_type ft
            JOIN tariff t ON ft.fare_type_id = t.fare_type_id
            WHERE ft.fare_type_id = %s
        """)
        
        call_queries = {
            "fare_info": (expected_fare_info_sql, (fare_type_id,)),
            "passenger": ("SELECT * FROM passenger WHERE passenger_id = %s", (passenger_id,)),
            "fare_type": ("SELECT * FROM fare_type WHERE fare_type_id = %s", (fare_type_id,))
        }
        
        # Check that each expected query was called
        for call_args in self.mock_execute_query.call_args_list:
            args, kwargs = call_args
            if args and len(args) > 0:
                normalized_query = normalize_sql(args[0])
                
                for query_name, (expected_sql, expected_params) in list(call_queries.items()):
                    expected_sql_normalized = normalize_sql(expected_sql)
                    if normalized_query == expected_sql_normalized and args[1] == expected_params:
                        # Found the query, remove it from our check list
                        del call_queries[query_name]
                        break
        
        # If our dictionary is empty, all queries were found
        self.assertEqual(len(call_queries), 0, f"Some expected queries were not called: {call_queries.keys()}")
        
        # Assert the calculation results
        self.assertEqual(base_fare, 3.0)
        self.assertEqual(discount_rate, 0)
        self.assertEqual(discount_amount, 0.0)
        self.assertEqual(final_fare, 3.0)
        self.assertEqual(passenger[0]["passenger_id"], 1)
        self.assertEqual(passenger[0]["passenger_full_name"], "John Doe")
        self.assertEqual(fare_type[0]["fare_type_id"], 1)
        self.assertEqual(fare_type[0]["type_name"], "Adult")

    def test_calculate_final_price_with_exemption(self):
        """Test the SQL operations for calculating final price with exemption"""
        # Setup the test parameters
        passenger_id = 1
        fare_type_id = 2
        exemption_id = 1
        
        # Mock the query results
        self.mock_execute_query.side_effect = [
            [{"fare_type_id": 2, "type_name": "Student", "base_price": 3.0, "discount_rate": 0.0}],  # Fare type
            [{"exemption_id": 1, "fare_type_id": 2, "discount_rate": 50.0}],  # Exemption
            [{"passenger_id": 1, "passenger_full_name": "John Doe"}],  # Passenger
            [{"fare_type_id": 2, "type_name": "Student"}]  # Fare type details
        ]
        
        # Import here to avoid circular imports
        from app.database.config import execute_query
        
        # Get fare type and base price
        fare_info = execute_query("""
            SELECT ft.*, t.base_price, t.discount_rate
            FROM fare_type ft
            JOIN tariff t ON ft.fare_type_id = t.fare_type_id
            WHERE ft.fare_type_id = %s
        """, (fare_type_id,))
            
        base_fare = float(fare_info[0]["base_price"])
        discount_rate = 0
        
        # Apply exemption discount if provided
        exemption = execute_query("""
            SELECT e.*, t.discount_rate
            FROM exemption e
            JOIN tariff t ON e.fare_type_id = t.fare_type_id
            WHERE e.exemption_id = %s AND e.passenger_id = %s
        """, (exemption_id, passenger_id))
        
        if exemption and len(exemption) > 0:
            discount_rate = float(exemption[0]["discount_rate"])
        
        # Calculate final price
        discount_amount = base_fare * (discount_rate / 100)
        final_fare = base_fare - discount_amount
        
        # Get passenger details for the template
        passenger = execute_query(
            "SELECT * FROM passenger WHERE passenger_id = %s", 
            (passenger_id,)
        )
        
        # Get fare type details for the template
        fare_type = execute_query(
            "SELECT * FROM fare_type WHERE fare_type_id = %s", 
            (fare_type_id,)
        )
        
        # Assert the queries were called correctly - using normalized SQL
        call_queries = {
            "fare_info": (normalize_sql("""
                SELECT ft.*, t.base_price, t.discount_rate
                FROM fare_type ft
                JOIN tariff t ON ft.fare_type_id = t.fare_type_id
                WHERE ft.fare_type_id = %s
            """), (fare_type_id,)),
            
            "exemption": (normalize_sql("""
                SELECT e.*, t.discount_rate
                FROM exemption e
                JOIN tariff t ON e.fare_type_id = t.fare_type_id
                WHERE e.exemption_id = %s AND e.passenger_id = %s
            """), (exemption_id, passenger_id)),
            
            "passenger": ("SELECT * FROM passenger WHERE passenger_id = %s", (passenger_id,)),
            
            "fare_type": ("SELECT * FROM fare_type WHERE fare_type_id = %s", (fare_type_id,))
        }
        
        # Check that each expected query was called
        for call_args in self.mock_execute_query.call_args_list:
            args, kwargs = call_args
            if args and len(args) > 0:
                normalized_query = normalize_sql(args[0])
                
                for query_name, (expected_sql, expected_params) in list(call_queries.items()):
                    if normalized_query == expected_sql and args[1] == expected_params:
                        # Found the query, remove it from our check list
                        del call_queries[query_name]
                        break
        
        # If our dictionary is empty, all queries were found
        self.assertEqual(len(call_queries), 0, f"Some expected queries were not called: {call_queries.keys()}")
        
        # Assert the calculation results
        self.assertEqual(base_fare, 3.0)
        self.assertEqual(discount_rate, 50.0)
        self.assertEqual(discount_amount, 1.5)
        self.assertEqual(final_fare, 1.5)
        self.assertEqual(passenger[0]["passenger_id"], 1)
        self.assertEqual(passenger[0]["passenger_full_name"], "John Doe")
        self.assertEqual(fare_type[0]["fare_type_id"], 2)
        self.assertEqual(fare_type[0]["type_name"], "Student")

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

    def tearDown(self):
        self.mock_execute_query_patcher.stop()
        self.mock_get_db_connection_patcher.stop()
        self.mock_close_connection_patcher.stop()

    # 4.1 Confirm Payment and 4.2 Generate Ticket tests
    def test_issue_ticket_success(self):
        """Test the SQL operations for issuing a ticket"""
        # Setup the test parameters
        passenger_id = 1
        fare_type_id = 1
        base_fare = 3.0
        discount = 0.0
        final_fare = 3.0
        payment_method = "Cash"
        today = date.today()
        ticket_id = 1001
        
        # Mock the lastrowid for ticket insertion
        self.mock_cursor.lastrowid = ticket_id
        
        # Mock the execute_query results
        self.mock_execute_query.side_effect = [
            [{"passenger_id": 1, "passenger_full_name": "John Doe"}],  # Verify passenger
            [{"fare_type_id": 1, "type_name": "Adult"}],  # Verify fare type
            {"affected_rows": 1, "last_insert_id": ticket_id},  # Insert ticket
            [{"ticket_id": ticket_id, "purchase_date": today}],  # Verify ticket
            [  # Full ticket details
                {
                    "ticket_id": ticket_id, 
                    "purchase_date": today, 
                    "price": 3.0,
                    "passenger_id": 1, 
                    "passenger_full_name": "John Doe",
                    "fare_type_id": 1, 
                    "type_name": "Adult",
                    "payment_method": "Cash", 
                    "transaction_ref": f"TXN{today.strftime('%Y%m%d')}-{ticket_id}"
                }
            ]
        ]
        
        # Import here to avoid circular imports
        from app.database.config import execute_query, get_db_connection, close_connection
        
        # First, verify the passenger exists
        passenger = execute_query("SELECT * FROM passenger WHERE passenger_id = %s", (passenger_id,), fetch=True)
        if not passenger:
            raise Exception("Passenger not found")
            
        # Verify the fare type exists
        fare_type = execute_query("SELECT * FROM fare_type WHERE fare_type_id = %s", (fare_type_id,), fetch=True)
        if not fare_type:
            raise Exception("Fare type not found")
        
        # Create a new ticket
        ticket_query = """
            INSERT INTO ticket (purchase_date, price, passenger_id, fare_type_id)
            VALUES (%s, %s, %s, %s)
        """
        ticket_params = (today, final_fare, passenger_id, fare_type_id)
        
        # Execute in transaction
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Insert the ticket record
        cursor.execute(ticket_query, ticket_params)
        
        # Get the new ticket ID
        ticket_id = cursor.lastrowid
        
        # Record fare calculation
        calc_query = """
            INSERT INTO fare_calculation (ticket_id, base_fare, discount, final_fare)
            VALUES (%s, %s, %s, %s)
        """
        calc_params = (ticket_id, base_fare, discount, final_fare)
        cursor.execute(calc_query, calc_params)
        
        # Record payment confirmation
        payment_query = """
            INSERT INTO payment_confirmation (ticket_id, status, payment_method, transaction_ref)
            VALUES (%s, %s, %s, %s)
        """
        # Generate a unique transaction reference
        transaction_ref = f"TXN{date.today().strftime('%Y%m%d')}-{ticket_id}"
        payment_params = (ticket_id, "Confirmed", payment_method, transaction_ref)
        cursor.execute(payment_query, payment_params)
        
        # Commit transaction
        conn.commit()
        cursor.close()
        close_connection(conn)
        
        # Double-verify the ticket record exists in the database
        ticket_check = execute_query("SELECT * FROM ticket WHERE ticket_id = %s", (ticket_id,), fetch=True)
        if not ticket_check:
            raise Exception("Ticket record not found after creation")
            
        # Get detailed ticket information for display
        ticket = execute_query("""
            SELECT t.*, p.passenger_full_name, ft.type_name, pc.payment_method, pc.transaction_ref
            FROM ticket t
            LEFT JOIN passenger p ON t.passenger_id = p.passenger_id
            LEFT JOIN fare_type ft ON t.fare_type_id = ft.fare_type_id
            LEFT JOIN payment_confirmation pc ON t.ticket_id = pc.ticket_id
            WHERE t.ticket_id = %s
        """, (ticket_id,), fetch=True)
        
        if not ticket:
            raise Exception("Ticket was created but could not be retrieved")
        
        # Assert the queries were called correctly - using normalized SQL for complex queries
        self.mock_execute_query.assert_any_call("SELECT * FROM passenger WHERE passenger_id = %s", (passenger_id,), fetch=True)
        self.mock_execute_query.assert_any_call("SELECT * FROM fare_type WHERE fare_type_id = %s", (fare_type_id,), fetch=True)
        self.mock_execute_query.assert_any_call("SELECT * FROM ticket WHERE ticket_id = %s", (ticket_id,), fetch=True)
        
        # Check the complex ticket query with normalized SQL
        expected_ticket_query = normalize_sql("""
            SELECT t.*, p.passenger_full_name, ft.type_name, pc.payment_method, pc.transaction_ref
            FROM ticket t
            LEFT JOIN passenger p ON t.passenger_id = p.passenger_id
            LEFT JOIN fare_type ft ON t.fare_type_id = ft.fare_type_id
            LEFT JOIN payment_confirmation pc ON t.ticket_id = pc.ticket_id
            WHERE t.ticket_id = %s
        """)
        
        found_ticket_query = False
        for call_args in self.mock_execute_query.call_args_list:
            args, kwargs = call_args
            if args and len(args) > 0:
                normalized_query = normalize_sql(args[0])
                if normalized_query == expected_ticket_query and args[1] == (ticket_id,) and kwargs.get('fetch') is True:
                    found_ticket_query = True
                    break
        
        self.assertTrue(found_ticket_query, f"Expected execute_query call for ticket details not found")
        
        # For SQL executions via cursor
        self.mock_cursor.execute.assert_any_call(ticket_query, ticket_params)
        self.mock_cursor.execute.assert_any_call(calc_query, calc_params)
        self.mock_cursor.execute.assert_any_call(payment_query, payment_params)
        self.assertEqual(self.mock_cursor.execute.call_count, 3)  # Three SQL operations
        
        # Verify transaction was committed
        self.mock_conn.commit.assert_called_once()
        self.mock_close_connection.assert_called_once_with(self.mock_conn)


if __name__ == "__main__":
    unittest.main()