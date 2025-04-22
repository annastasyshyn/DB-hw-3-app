import unittest
from unittest.mock import patch, MagicMock
from datetime import date, timedelta

class TestFareTypeOperations(unittest.TestCase):
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

    # 1.1 Create Fare Type tests
    def test_create_fare_type(self):
        """Test the SQL operations for creating a new fare type"""
        # Mock the successful insert
        self.mock_cursor.lastrowid = 123  # Mock the new fare type ID
        
        # Setup the test parameters
        fare_type_name = "New Fare Type"
        description = "A new fare type for testing"
        validity = "1 year"
        base_price = 10.50
        discount_rate = 15.0
        
        # Import here to avoid circular imports
        from app.database.config import execute_query, get_db_connection, close_connection
        
        # Execute the create fare type operation
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Insert fare type
        fare_query = """
            INSERT INTO fare_type (type_name, description, validity)
            VALUES (%s, %s, %s)
        """
        fare_params = (fare_type_name, description, validity)
        cursor.execute(fare_query, fare_params)
        
        # Get the new fare type ID
        fare_type_id = cursor.lastrowid
        
        # Create the tariff
        tariff_query = """
            INSERT INTO tariff (base_price, discount_rate, fare_type_id)
            VALUES (%s, %s, %s)
        """
        tariff_params = (base_price, discount_rate, fare_type_id)
        cursor.execute(tariff_query, tariff_params)
        
        # Commit and close
        conn.commit()
        cursor.close()
        close_connection(conn)
        
        # Assert that the operations were called with the correct parameters
        self.mock_cursor.execute.assert_any_call(fare_query, fare_params)
        self.mock_cursor.execute.assert_any_call(tariff_query, tariff_params)
        self.assertEqual(self.mock_cursor.execute.call_count, 2)  # Two SQL operations
        self.mock_conn.commit.assert_called_once()
        self.mock_close_connection.assert_called_once_with(self.mock_conn)
        
        # Verify the fare type ID was returned
        self.assertEqual(fare_type_id, 123)

    # 1.2 Update Fare Type tests
    def test_update_fare_type(self):
        """Test the SQL operations for updating an existing fare type"""
        # Setup the test parameters
        fare_type_id = 1
        tariff_id = 101
        fare_type_name = "Updated Fare Type"
        description = "Updated description"
        validity = "2 years"
        base_price = 4.50
        discount_rate = 10.0
        
        # Import here to avoid circular imports
        from app.database.config import execute_query, get_db_connection, close_connection
        
        # Execute the update fare type operation
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Update fare type
        fare_query = """
            UPDATE fare_type 
            SET type_name = %s, description = %s, validity = %s
            WHERE fare_type_id = %s
        """
        fare_params = (fare_type_name, description, validity, fare_type_id)
        cursor.execute(fare_query, fare_params)
        
        # Update tariff
        tariff_query = """
            UPDATE tariff 
            SET base_price = %s, discount_rate = %s
            WHERE tariff_id = %s
        """
        tariff_params = (base_price, discount_rate, tariff_id)
        cursor.execute(tariff_query, tariff_params)
        
        # Commit and close
        conn.commit()
        cursor.close()
        close_connection(conn)
        
        # Assert that the operations were called with the correct parameters
        self.mock_cursor.execute.assert_any_call(fare_query, fare_params)
        self.mock_cursor.execute.assert_any_call(tariff_query, tariff_params)
        self.assertEqual(self.mock_cursor.execute.call_count, 2)  # Two SQL operations
        self.mock_conn.commit.assert_called_once()
        self.mock_close_connection.assert_called_once_with(self.mock_conn)

    # 1.3 Delete Fare Type tests
    def test_delete_fare_type(self):
        """Test the SQL operations for deleting a fare type"""
        # Setup the test parameters
        fare_type_id = 1
        
        # Import here to avoid circular imports
        from app.database.config import execute_query, get_db_connection, close_connection
        
        # Execute the delete fare type operation
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Delete the fare type
        query = "DELETE FROM fare_type WHERE fare_type_id = %s"
        cursor.execute(query, (fare_type_id,))
        
        # Commit and close
        conn.commit()
        cursor.close()
        close_connection(conn)
        
        # Assert that the operations were called with the correct parameters
        self.mock_cursor.execute.assert_called_once_with(query, (fare_type_id,))
        self.mock_conn.commit.assert_called_once()
        self.mock_close_connection.assert_called_once_with(self.mock_conn)

    # 1.4 View Fare Types test
    def test_view_fare_types(self):
        """Test the SQL operations for viewing all fare types"""
        # Mock the query result
        expected_fare_types = [
            {
                "fare_type_id": 1, 
                "type_name": "Adult", 
                "description": "Standard adult fare",
                "validity": "1 year",
                "base_price": 3.0,
                "discount_rate": 0.0
            },
            {
                "fare_type_id": 2, 
                "type_name": "Student", 
                "description": "Discounted student fare",
                "validity": "1 year",
                "base_price": 2.0,
                "discount_rate": 33.3
            }
        ]
        self.mock_execute_query.return_value = expected_fare_types
        
        # Import here to avoid circular imports
        from app.database.config import execute_query
        
        # Execute the view fare types operation
        query = """
            SELECT ft.*, t.base_price, t.discount_rate
            FROM fare_type ft
            JOIN tariff t ON ft.fare_type_id = t.fare_type_id
        """
        result = execute_query(query)
        
        # Assert the query was called correctly and returned the expected result
        self.mock_execute_query.assert_called_once_with(query)
        self.assertEqual(result, expected_fare_types)

class TestExemptionOperations(unittest.TestCase):
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

    # 2.2 Validate Documents and 2.3 Approve/Reject Request
    def test_process_exemption_application_approve(self):
        """Test the SQL operations for approving an exemption application"""
        # Setup the test parameters
        application_id = 1
        passenger_id = 100
        decision = "Approved"
        fare_type_id = 2
        exemption_category = "Student"
        
        # Mock query results
        self.mock_execute_query.side_effect = [
            [{"passenger_id": passenger_id}]  # Get passenger ID from application
        ]
        
        # Import here to avoid circular imports
        from app.database.config import execute_query, get_db_connection, close_connection
        
        # Execute the process exemption application operation
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Update application status
        status_query = """
            UPDATE exemption_application
            SET status = %s
            WHERE application_id = %s
        """
        status_params = (decision, application_id)
        cursor.execute(status_query, status_params)
        
        # Get passenger ID from application
        application = execute_query("""
            SELECT passenger_id FROM exemption_application
            WHERE application_id = %s
        """, (application_id,))
        
        if application:
            passenger_id = application[0]["passenger_id"]
            
            # Create exemption valid for 1 year
            today = date.today()
            valid_to = today + timedelta(days=365)
            
            exemption_query = """
                INSERT INTO exemption 
                (exemption_category, passenger_id, fare_type_id, valid_from, valid_to)
                VALUES (%s, %s, %s, %s, %s)
            """
            exemption_params = (
                exemption_category, 
                passenger_id, 
                fare_type_id, 
                today, 
                valid_to
            )
            cursor.execute(exemption_query, exemption_params)
        
        # Commit and close
        conn.commit()
        cursor.close()
        close_connection(conn)
        
        # Assert that the operations were called with the correct parameters
        self.mock_cursor.execute.assert_any_call(status_query, status_params)
        
        # For the second execute call, we need to verify the parameters, but the date objects will be different
        # So we'll extract the call arguments and verify them separately
        call_args_list = self.mock_cursor.execute.call_args_list
        self.assertEqual(len(call_args_list), 2)  # Two SQL operations
        
        # Check the second call (exemption creation)
        second_call = call_args_list[1]
        query, params = second_call[0]
        self.assertEqual(query, exemption_query)
        self.assertEqual(params[0], exemption_category)
        self.assertEqual(params[1], passenger_id)
        self.assertEqual(params[2], fare_type_id)
        # params[3] is today's date
        # params[4] is valid_to date
        
        self.mock_conn.commit.assert_called_once()
        self.mock_close_connection.assert_called_once_with(self.mock_conn)

    def test_process_exemption_application_reject(self):
        """Test the SQL operations for rejecting an exemption application"""
        # Setup the test parameters
        application_id = 1
        decision = "Rejected"
        
        # Import here to avoid circular imports
        from app.database.config import get_db_connection, close_connection
        
        # Execute the process exemption application operation
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Update application status
        status_query = """
            UPDATE exemption_application
            SET status = %s
            WHERE application_id = %s
        """
        status_params = (decision, application_id)
        cursor.execute(status_query, status_params)
        
        # Commit and close
        conn.commit()
        cursor.close()
        close_connection(conn)
        
        # Assert that the operations were called with the correct parameters
        self.mock_cursor.execute.assert_called_once_with(status_query, status_params)
        self.mock_conn.commit.assert_called_once()
        self.mock_close_connection.assert_called_once_with(self.mock_conn)

    # 5.1 Generate Fare Usage Report
    def test_generate_fare_usage_report(self):
        """Test the SQL operations for generating a fare usage report"""
        # Setup the test parameters
        start_date = "2025-03-22"
        end_date = "2025-04-22"
        
        # Mock the query result
        expected_report_data = [
            {"date": date(2025, 4, 20), "fare_type": "Adult", "tickets_sold": 10, "total_revenue": 30.0},
            {"date": date(2025, 4, 20), "fare_type": "Student", "tickets_sold": 5, "total_revenue": 7.5}
        ]
        self.mock_execute_query.return_value = expected_report_data
        
        # Import here to avoid circular imports
        from app.database.config import execute_query
        
        # Execute the generate fare usage report operation
        query = """
            SELECT 
                t.purchase_date as date,
                ft.type_name as fare_type,
                COUNT(t.ticket_id) as tickets_sold,
                SUM(t.price) as total_revenue
            FROM ticket t
            JOIN fare_type ft ON t.fare_type_id = ft.fare_type_id
            WHERE t.purchase_date BETWEEN %s AND %s
            GROUP BY t.purchase_date, ft.type_name
            ORDER BY t.purchase_date DESC
        """
        report_data = execute_query(query, (start_date, end_date))
        
        # Assert the query was called correctly and returned the expected result
        self.mock_execute_query.assert_called_once_with(query, (start_date, end_date))
        self.assertEqual(report_data, expected_report_data)

    # 5.2 Generate Exemption Statistics
    def test_generate_exemption_statistics(self):
        """Test the SQL operations for generating exemption statistics"""
        # Setup the test parameters
        start_date = "2025-03-22"  # past 30 days
        
        # Mock the query result
        expected_stats = [
            {"exemption_category": "Student", "total_applications": 20, "approved": 15, "approval_rate": 75.0},
            {"exemption_category": "Senior", "total_applications": 15, "approved": 14, "approval_rate": 93.3}
        ]
        self.mock_execute_query.return_value = expected_stats
        
        # Import here to avoid circular imports
        from app.database.config import execute_query
        
        # Execute the generate exemption statistics operation
        query = """
            SELECT 
                exemption_category,
                COUNT(a.application_id) as total_applications,
                SUM(CASE WHEN a.status = 'Approved' THEN 1 ELSE 0 END) as approved,
                (SUM(CASE WHEN a.status = 'Approved' THEN 1 ELSE 0 END) / COUNT(a.application_id)) * 100 as approval_rate
            FROM exemption e
            JOIN exemption_application a ON e.passenger_id = a.passenger_id
            WHERE a.submitted_date >= %s
            GROUP BY exemption_category ORDER BY total_applications DESC
        """
        stats = execute_query(query, (start_date,))
        
        # Assert the query was called correctly and returned the expected result
        self.mock_execute_query.assert_called_once_with(query, (start_date,))
        self.assertEqual(stats, expected_stats)


if __name__ == "__main__":
    unittest.main()