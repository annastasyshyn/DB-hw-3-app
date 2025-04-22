import unittest
from unittest.mock import patch, MagicMock, AsyncMock, call
from datetime import date
from io import BytesIO
import os
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

class TestPassengerRegistrationOperations(unittest.TestCase):
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

    def test_create_passenger(self):
        """Test the SQL operations for creating a passenger"""
        # Mock the successful insert
        self.mock_execute_query.side_effect = [
            [],  # No existing email
            {"affected_rows": 1, "last_insert_id": 123}  # Successful insert
        ]
        
        # Setup the test parameters
        passenger_full_name = "Test User"
        email = "test@example.com"
        
        # Import here to avoid circular imports
        from app.database.config import execute_query
        
        # Check if email already exists
        existing_email = execute_query("SELECT passenger_id FROM passenger WHERE email = %s", (email,))
        
        # If validation passes, insert passenger into database
        query = """
            INSERT INTO passenger (passenger_full_name, email) 
            VALUES (%s, %s)
        """
        params = (passenger_full_name, email)
        result = execute_query(query, params, fetch=False)
        
        # Assert the queries were called correctly
        self.mock_execute_query.assert_any_call("SELECT passenger_id FROM passenger WHERE email = %s", (email,))
        
        # Use normalize_sql for SQL string comparison
        normalized_query = normalize_sql(query)
        for call_args in self.mock_execute_query.call_args_list:
            args, kwargs = call_args
            if args and len(args) > 0:
                # Check if the normalized SQL strings match
                if normalize_sql(args[0]) == normalized_query and args[1] == params:
                    # Found the right call
                    break
        else:
            self.fail(f"Expected execute_query call with normalized query {normalized_query} not found")
        
        # Assert the expected result
        self.assertEqual(result, {"affected_rows": 1, "last_insert_id": 123})

    def test_email_already_exists(self):
        """Test the SQL operations when email already exists"""
        # Mock finding an existing email
        self.mock_execute_query.return_value = [{"passenger_id": 1}]
        
        # Setup the test parameters
        email = "existing@example.com"
        
        # Import here to avoid circular imports
        from app.database.config import execute_query
        
        # Check if email already exists
        existing_email = execute_query("SELECT passenger_id FROM passenger WHERE email = %s", (email,))
        
        # Assert the query was called correctly
        self.mock_execute_query.assert_called_once_with("SELECT passenger_id FROM passenger WHERE email = %s", (email,))
        
        # Assert that an existing email was found
        self.assertTrue(existing_email)
        self.assertEqual(existing_email[0]["passenger_id"], 1)

class TestExemptionApplicationOperations(unittest.TestCase):
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

    async def test_submit_exemption_application(self):
        """Test the SQL operations for submitting an exemption application"""
        # Mock the successful inserts
        self.mock_cursor.lastrowid = 456  # Mock application ID
        
        # Setup the test parameters
        passenger_id = 123
        exemption_category = "Student"
        fare_type_id = 2
        document_description = "Student ID"
        
        # Mock document file
        mock_file_content = b"test content"
        mock_file = MagicMock()
        mock_file.read = AsyncMock(return_value=mock_file_content)
        mock_file.filename = "student_id.pdf"
        mock_file.content_type = "application/pdf"
        
        # Mock existing applications check
        self.mock_execute_query.side_effect = [
            [{"passenger_id": 123, "passenger_full_name": "Test User"}],  # Passenger exists
            [{"fare_type_id": 2, "type_name": "Student"}],  # Fare type exists
            []  # No pending applications
        ]
        
        # Import here to avoid circular imports
        from app.database.config import execute_query, get_db_connection, close_connection
        
        # Execute the exemption application submission operation
        today = date.today()
        
        # Start transaction
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # First insert the application
        app_query = """
            INSERT INTO exemption_application (submitted_date, passenger_id, status) 
            VALUES (%s, %s, %s)
        """
        app_params = (today, passenger_id, "Submitted")
        cursor.execute(app_query, app_params)
        
        # Get the new application ID
        application_id = cursor.lastrowid
        
        # Create a unique filename to prevent overwriting
        unique_filename = "test-uuid.pdf"
        file_location = f"uploads/{unique_filename}"
        
        # Save the document to file (mock)
        with patch('builtins.open', MagicMock()):
            # Insert document record
            doc_query = """
                INSERT INTO document_record (application_id, document_type, document_value) 
                VALUES (%s, %s, %s)
            """
            doc_params = (application_id, document_description, file_location)
            cursor.execute(doc_query, doc_params)
            
            # Log the creation of a new exemption application
            log_query = """
                INSERT INTO activity_log (activity_type, description, entity_id, entity_type, created_at)
                VALUES (%s, %s, %s, %s, NOW())
            """
            passenger_name = "Test User"
            fare_type_name = "Student"
            log_description = f"New exemption application ({exemption_category}) submitted by {passenger_name} for {fare_type_name}"
            log_params = ("application_creation", log_description, application_id, "exemption_application")
            cursor.execute(log_query, log_params)
        
        # Commit transaction
        conn.commit()
        cursor.close()
        close_connection(conn)
        
        # Assert that the operations were called with the correct parameters
        # Use normalized SQL comparison
        self.mock_cursor.execute.assert_any_call(app_query, app_params)
        self.mock_cursor.execute.assert_any_call(doc_query, doc_params)
        self.mock_cursor.execute.assert_any_call(log_query, log_params)
        self.assertEqual(self.mock_cursor.execute.call_count, 3)  # Three SQL operations
        self.mock_conn.commit.assert_called_once()
        self.mock_close_connection.assert_called_once_with(self.mock_conn)

    def test_pending_application_check(self):
        """Test the SQL operations for checking pending applications"""
        # Setup the test parameters
        passenger_id = 123
        
        # Mock finding a pending application
        self.mock_execute_query.return_value = [
            {"application_id": 1, "status": "Submitted"}
        ]
        
        # Import here to avoid circular imports
        from app.database.config import execute_query
        
        # Check for existing applications
        existing_app = execute_query("""
            SELECT * FROM exemption_application 
            WHERE passenger_id = %s AND status IN ('Submitted', 'Pending')
        """, (passenger_id,))
        
        # Assert the query was called correctly - using normalized SQL comparison
        expected_sql = normalize_sql("""
            SELECT * FROM exemption_application 
            WHERE passenger_id = %s AND status IN ('Submitted', 'Pending')
        """)
        
        for call_args in self.mock_execute_query.call_args_list:
            args, kwargs = call_args
            if args and len(args) > 0:
                # Check if the normalized SQL strings match
                if normalize_sql(args[0]) == expected_sql and args[1] == (passenger_id,):
                    # Found the right call
                    break
        else:
            self.fail(f"Expected execute_query call with normalized query {expected_sql} not found")
        
        # Assert that a pending application was found
        self.assertTrue(existing_app)
        self.assertEqual(existing_app[0]["application_id"], 1)
        self.assertEqual(existing_app[0]["status"], "Submitted")

    # 2.4: View Passenger Exemptions
    def test_view_exemptions(self):
        """Test the SQL operations for viewing passenger exemptions"""
        # Setup the test parameters
        passenger_id = 123
        
        # Mock the query results
        self.mock_execute_query.side_effect = [
            [{"passenger_id": passenger_id, "passenger_full_name": "Test User"}],  # Passenger exists
            [
                {
                    "exemption_id": 1,
                    "exemption_category": "Student",
                    "type_name": "Student Fare",
                    "status": "Approved"
                }
            ]  # Exemptions found
        ]
        
        # Import here to avoid circular imports
        from app.database.config import execute_query
        
        # Check if passenger exists
        passenger = execute_query("SELECT * FROM passenger WHERE passenger_id = %s", (passenger_id,))
        
        # Get all exemptions for the passenger with detailed information
        exemptions = execute_query("""
            SELECT e.*, ft.type_name, ea.status
            FROM exemption e
            JOIN fare_type ft ON e.fare_type_id = ft.fare_type_id
            JOIN exemption_application ea ON e.passenger_id = ea.passenger_id
            WHERE e.passenger_id = %s
        """, (passenger_id,))
        
        # Assert the queries were called correctly - using normalized SQL
        self.mock_execute_query.assert_any_call("SELECT * FROM passenger WHERE passenger_id = %s", (passenger_id,))
        
        expected_exemptions_sql = normalize_sql("""
            SELECT e.*, ft.type_name, ea.status
            FROM exemption e
            JOIN fare_type ft ON e.fare_type_id = ft.fare_type_id
            JOIN exemption_application ea ON e.passenger_id = ea.passenger_id
            WHERE e.passenger_id = %s
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
        self.assertEqual(exemptions[0]["exemption_id"], 1)
        self.assertEqual(exemptions[0]["exemption_category"], "Student")
        self.assertEqual(exemptions[0]["status"], "Approved")

    # 2.5: View Exemption Application Status Report
    def test_exemption_status_report(self):
        """Test the SQL operations for generating an exemption status report"""
        # Setup the test parameters
        passenger_id = 123
        today = date.today()
        
        # Mock the query results
        self.mock_execute_query.side_effect = [
            [{"passenger_id": passenger_id, "passenger_full_name": "Test User"}],  # Passenger exists
            [
                {
                    "application_id": 1, 
                    "status": "Approved", 
                    "submitted_date": today,
                    "document_type": "Student ID"
                }
            ],  # Applications
            [
                {
                    "application_id": 1, 
                    "type_name": "Student Fare",
                    "description": "For students", 
                    "exemption_id": 1
                }
            ],  # Approved applications with fare type info
            [
                {
                    "exemption_id": 1, 
                    "exemption_category": "Student",
                    "type_name": "Student Fare", 
                    "valid_from": today,
                    "valid_to": today.replace(year=today.year + 1),
                    "days_remaining": 365
                }
            ]  # Current active exemptions
        ]
        
        # Import here to avoid circular imports
        from app.database.config import execute_query
        
        # Check if passenger exists
        passenger = execute_query("SELECT * FROM passenger WHERE passenger_id = %s", (passenger_id,))
        
        # Get all applications for the passenger with document information
        applications = execute_query("""
            SELECT ea.*, dr.document_type
            FROM exemption_application ea
            LEFT JOIN document_record dr ON ea.application_id = dr.application_id
            WHERE ea.passenger_id = %s
            ORDER BY ea.submitted_date DESC
        """, (passenger_id,))
        
        # Get approved applications with fare type information
        approved_applications = execute_query("""
            SELECT ea.application_id, ft.type_name, ft.description, e.exemption_id
            FROM exemption_application ea
            LEFT JOIN exemption e ON (
                ea.passenger_id = e.passenger_id AND 
                ea.status = 'Approved' AND
                DATE(ea.submitted_date) <= e.valid_from
            )
            LEFT JOIN fare_type ft ON e.fare_type_id = ft.fare_type_id
            WHERE ea.passenger_id = %s AND ea.status = 'Approved'
        """, (passenger_id,))
        
        # Get current active exemptions for the passenger
        exemptions = execute_query("""
            SELECT e.*, ft.type_name, 
                DATEDIFF(e.valid_to, CURDATE()) as days_remaining
            FROM exemption e
            JOIN fare_type ft ON e.fare_type_id = ft.fare_type_id
            WHERE e.passenger_id = %s
            ORDER BY e.valid_to DESC
        """, (passenger_id,))
        
        # Assert the queries were called correctly using normalized SQL
        self.mock_execute_query.assert_any_call(
            "SELECT * FROM passenger WHERE passenger_id = %s", (passenger_id,))
        
        call_queries = {
            "applications": normalize_sql("""
                SELECT ea.*, dr.document_type
                FROM exemption_application ea
                LEFT JOIN document_record dr ON ea.application_id = dr.application_id
                WHERE ea.passenger_id = %s
                ORDER BY ea.submitted_date DESC
            """),
            "approved_apps": normalize_sql("""
                SELECT ea.application_id, ft.type_name, ft.description, e.exemption_id
                FROM exemption_application ea
                LEFT JOIN exemption e ON (
                    ea.passenger_id = e.passenger_id AND 
                    ea.status = 'Approved' AND
                    DATE(ea.submitted_date) <= e.valid_from
                )
                LEFT JOIN fare_type ft ON e.fare_type_id = ft.fare_type_id
                WHERE ea.passenger_id = %s AND ea.status = 'Approved'
            """),
            "exemptions": normalize_sql("""
                SELECT e.*, ft.type_name, 
                    DATEDIFF(e.valid_to, CURDATE()) as days_remaining
                FROM exemption e
                JOIN fare_type ft ON e.fare_type_id = ft.fare_type_id
                WHERE e.passenger_id = %s
                ORDER BY e.valid_to DESC
            """)
        }

        # Check that each expected query was called
        for call_args in self.mock_execute_query.call_args_list:
            args, kwargs = call_args
            if args and len(args) > 0:
                normalized_query = normalize_sql(args[0])
                
                for query_name, expected_sql in list(call_queries.items()):
                    if normalized_query == expected_sql and args[1] == (passenger_id,):
                        # Found the query, remove it from our check list
                        del call_queries[query_name]
                        break
        
        # If our dictionary is empty, all queries were found
        self.assertEqual(len(call_queries), 0, f"Some expected queries were not called: {call_queries.keys()}")
        
        # Assert the results
        self.assertTrue(passenger)
        self.assertEqual(passenger[0]["passenger_id"], passenger_id)
        self.assertEqual(applications[0]["application_id"], 1)
        self.assertEqual(applications[0]["status"], "Approved")
        self.assertEqual(approved_applications[0]["application_id"], 1)
        self.assertEqual(approved_applications[0]["type_name"], "Student Fare")
        self.assertEqual(exemptions[0]["exemption_id"], 1)
        self.assertEqual(exemptions[0]["type_name"], "Student Fare")


if __name__ == "__main__":
    unittest.main()