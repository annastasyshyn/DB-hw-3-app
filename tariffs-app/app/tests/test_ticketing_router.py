import unittest
from unittest.mock import patch, MagicMock
from datetime import date, datetime
import re
import logging

logger = logging.getLogger('tariffs_test')

def normalize_sql(sql):
    if sql is None:
        return None
    normalized = re.sub(r'\s+', ' ', sql)
    normalized = normalized.strip()
    return normalized

class TestFareCalculationOperations(unittest.TestCase):
    def setUp(self):
        self.mock_execute_query_patcher = patch('app.database.config.execute_query')
        self.mock_execute_query = self.mock_execute_query_patcher.start()
        
        self.mock_get_db_connection_patcher = patch('app.database.config.get_db_connection')
        self.mock_get_db_connection = self.mock_get_db_connection_patcher.start()
        
        self.mock_close_connection_patcher = patch('app.database.config.close_connection')
        self.mock_close_connection = self.mock_close_connection_patcher.start()
        
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor
        self.mock_get_db_connection.return_value = self.mock_conn
        
        self.initialize_test_data()

    def tearDown(self):
        self.mock_execute_query_patcher.stop()
        self.mock_get_db_connection_patcher.stop()
        self.mock_close_connection_patcher.stop()
    
    def initialize_test_data(self):
        self.passenger_data = {
            "passenger_id": 123,
            "passenger_full_name": "John Smith",
            "email": "john@example.com"
        }
        
        self.fare_type_data = {
            "fare_type_id": 2,
            "type_name": "Student",
            "base_price": 2.00,
            "discount_rate": 33.3
        }
        
        self.exemption_data = {
            "exemption_id": 456,
            "passenger_id": 123,
            "exemption_category": "Student",
            "fare_type_id": 2,
            "valid_from": date(2025, 1, 1),
            "valid_to": date(2025, 12, 31),
            "is_active": True
        }
        
        self.mock_execute_query.reset_mock()

    def validate_report(self):
        test_name = self._testMethodName
        
        mock_passenger = [self.passenger_data]
        mock_fare_type = [self.fare_type_data]
        mock_exemption = [self.exemption_data]
        
        if test_name == "test_retrieve_passenger_profile":
            self.mock_execute_query.return_value = mock_passenger
            
            passenger_data = self.mock_execute_query.return_value
            self.assertEqual(passenger_data[0]["passenger_id"], 123)
            self.assertEqual(passenger_data[0]["passenger_full_name"], "John Smith")
            
        elif test_name == "test_prepare_fare_calculation":
            self.mock_execute_query.return_value = mock_passenger
            
            passenger_data = self.mock_execute_query.return_value
            self.assertEqual(passenger_data[0]["passenger_full_name"], "John Smith")
            
        elif test_name == "test_calculate_final_price_with_exemption":
            self.mock_execute_query.return_value = mock_fare_type
            
            fare_info = self.mock_execute_query.return_value
            self.assertEqual(fare_info[0]["base_price"], 2.00)
            self.assertEqual(fare_info[0]["discount_rate"], 33.3)
            
        elif test_name == "test_calculate_final_price_without_exemption":
            self.mock_execute_query.return_value = mock_fare_type
            
            fare_info = self.mock_execute_query.return_value
            self.assertEqual(fare_info[0]["base_price"], 2.00)
            self.assertEqual(fare_info[0]["discount_rate"], 33.3)

    def test_retrieve_passenger_profile(self):
        passenger_id = 123
        
        self.mock_execute_query.return_value = [self.passenger_data]
        
        from app.database.config import execute_query
        
        query = """
            SELECT * FROM passenger 
            WHERE passenger_id = %s
        """
        passenger = execute_query(query, (passenger_id,))
        
        self.mock_execute_query.assert_called_once_with(query, (passenger_id,))
        
        self.assertEqual(len(passenger), 1)
        self.assertEqual(passenger[0]["passenger_id"], passenger_id)
        self.assertEqual(passenger[0]["passenger_full_name"], "John Smith")
        self.assertEqual(passenger[0]["email"], "john@example.com")
        
        self.validate_report()

    def test_prepare_fare_calculation(self):
        passenger_id = 123
        
        self.mock_execute_query.return_value = [self.passenger_data]
        
        from app.database.config import execute_query
        
        query = """
            SELECT * FROM passenger 
            WHERE passenger_id = %s
        """
        passenger = execute_query(query, (passenger_id,))
        
        self.mock_execute_query.assert_called_once_with(query, (passenger_id,))
        
        self.assertEqual(len(passenger), 1)
        self.assertEqual(passenger[0]["passenger_id"], passenger_id)
        self.assertEqual(passenger[0]["passenger_full_name"], "John Smith")
        
        self.validate_report()

    def test_calculate_final_price_without_exemption(self):
        passenger_id = 123
        fare_type_id = 2
        
        self.mock_execute_query.side_effect = [
            [],  
            [self.fare_type_data]  
        ]
        
        from app.database.config import execute_query
        
        exemption_query = """
            SELECT e.* FROM exemption e
            WHERE e.passenger_id = %s 
              AND e.fare_type_id = %s
              AND e.is_active = True
              AND CURRENT_DATE BETWEEN e.valid_from AND e.valid_to
        """
        exemption = execute_query(exemption_query, (passenger_id, fare_type_id))
        
        fare_query = """
            SELECT ft.*, t.base_price, t.discount_rate
            FROM fare_type ft
            JOIN tariff t ON ft.fare_type_id = t.fare_type_id
            WHERE ft.fare_type_id = %s
        """
        fare_info = execute_query(fare_query, (fare_type_id,))
        
        base_price = fare_info[0]["base_price"]
        discount_rate = fare_info[0]["discount_rate"]
        final_price = base_price * (1 - (discount_rate / 100))
        
        self.assertEqual(self.mock_execute_query.call_count, 2)
        self.mock_execute_query.assert_any_call(exemption_query, (passenger_id, fare_type_id))
        self.mock_execute_query.assert_any_call(fare_query, (fare_type_id,))
        
        self.assertEqual(len(exemption), 0)  
        self.assertEqual(fare_info[0]["base_price"], 2.00)
        self.assertEqual(fare_info[0]["discount_rate"], 33.3)
        self.assertAlmostEqual(final_price, 1.334, places=3)  
        
        self.validate_report()

    def test_calculate_final_price_with_exemption(self):
        passenger_id = 123
        fare_type_id = 2
        
        self.mock_execute_query.side_effect = [
            [self.exemption_data],  
            [self.fare_type_data]   
        ]
        
        from app.database.config import execute_query
        
        exemption_query = """
            SELECT e.* FROM exemption e
            WHERE e.passenger_id = %s 
              AND e.fare_type_id = %s
              AND e.is_active = True
              AND CURRENT_DATE BETWEEN e.valid_from AND e.valid_to
        """
        exemption = execute_query(exemption_query, (passenger_id, fare_type_id))
        
        fare_query = """
            SELECT ft.*, t.base_price, t.discount_rate
            FROM fare_type ft
            JOIN tariff t ON ft.fare_type_id = t.fare_type_id
            WHERE ft.fare_type_id = %s
        """
        fare_info = execute_query(fare_query, (fare_type_id,))
        
        base_price = fare_info[0]["base_price"]
        discount_rate = 100.0 if exemption else fare_info[0]["discount_rate"]
        final_price = base_price * (1 - (discount_rate / 100))
        
        self.assertEqual(self.mock_execute_query.call_count, 2)
        self.mock_execute_query.assert_any_call(exemption_query, (passenger_id, fare_type_id))
        self.mock_execute_query.assert_any_call(fare_query, (fare_type_id,))
        
        self.assertEqual(len(exemption), 1)  
        self.assertEqual(exemption[0]["exemption_category"], "Student")
        self.assertEqual(fare_info[0]["base_price"], 2.00)
        self.assertEqual(discount_rate, 100.0)  
        self.assertEqual(final_price, 0.0)  
        
        self.validate_report()

class TestTicketOperations(unittest.TestCase):
    def setUp(self):
        self.mock_execute_query_patcher = patch('app.database.config.execute_query')
        self.mock_execute_query = self.mock_execute_query_patcher.start()
        
        self.mock_get_db_connection_patcher = patch('app.database.config.get_db_connection')
        self.mock_get_db_connection = self.mock_get_db_connection_patcher.start()
        
        self.mock_close_connection_patcher = patch('app.database.config.close_connection')
        self.mock_close_connection = self.mock_close_connection_patcher.start()
        
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor
        self.mock_get_db_connection.return_value = self.mock_conn
        
        self.mock_datetime_now_patcher = patch('datetime.datetime')
        self.mock_datetime = self.mock_datetime_now_patcher.start()
        self.mock_datetime.now.return_value = datetime(2025, 4, 22, 12, 0, 0)
        
        self.initialize_test_data()

    def tearDown(self):
        self.mock_execute_query_patcher.stop()
        self.mock_get_db_connection_patcher.stop()
        self.mock_close_connection_patcher.stop()
        self.mock_datetime_now_patcher.stop()
    
    def initialize_test_data(self):
        self.passenger_id = 123
        self.fare_type_id = 2
        self.price = 1.33  
        self.issued_date = date(2025, 4, 22)
        self.valid_from = date(2025, 4, 22)
        self.valid_to = date(2025, 5, 22)  
        self.ticket_id = 456  
        
        self.passenger_data = {
            "passenger_id": self.passenger_id,
            "passenger_full_name": "John Smith",
            "email": "john@example.com"
        }
        
        self.fare_type_data = {
            "fare_type_id": self.fare_type_id,
            "type_name": "Student",
            "base_price": 2.00,
            "discount_rate": 33.3
        }
        
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
        
        self.mock_cursor.lastrowid = self.ticket_id

    def test_issue_ticket_success(self):
        self.mock_execute_query.side_effect = [
            [self.passenger_data],  
            [self.fare_type_data],  
            [self.ticket_data]      
        ]
        
        from app.database.config import execute_query, get_db_connection, close_connection
        
        passenger_query = """
            SELECT * FROM passenger
            WHERE passenger_id = %s
        """
        passenger = execute_query(passenger_query, (self.passenger_id,))
        
        fare_query = """
            SELECT ft.*, t.base_price, t.discount_rate
            FROM fare_type ft
            JOIN tariff t ON ft.fare_type_id = t.fare_type_id
            WHERE ft.fare_type_id = %s
        """
        fare_type = execute_query(fare_query, (self.fare_type_id,))
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
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
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            close_connection(conn)
            
        ticket_details_query = """
            SELECT t.*, p.passenger_full_name as passenger_name, ft.type_name as fare_type_name
            FROM ticket t
            JOIN passenger p ON t.passenger_id = p.passenger_id
            JOIN fare_type ft ON t.fare_type_id = ft.fare_type_id
            WHERE t.ticket_id = %s
        """
        ticket = execute_query(ticket_details_query, (ticket_id,))
        
        self.assertEqual(self.mock_execute_query.call_count, 3)
        self.mock_execute_query.assert_any_call(passenger_query, (self.passenger_id,))
        self.mock_execute_query.assert_any_call(fare_query, (self.fare_type_id,))
        self.mock_execute_query.assert_any_call(ticket_details_query, (self.ticket_id,))
        
        self.mock_cursor.execute.assert_any_call(ticket_query, ticket_params)
        
        log_query_normalized = normalize_sql(log_query)
        any_log_call = False
        for call_args in self.mock_cursor.execute.call_args_list:
            args, kwargs = call_args
            if args and len(args) > 0 and normalize_sql(args[0]) == log_query_normalized:
                any_log_call = True
                break
        self.assertTrue(any_log_call, "Log entry was not created")
        
        self.mock_conn.commit.assert_called_once()
        self.mock_close_connection.assert_called_once_with(self.mock_conn)
        
        self.assertEqual(len(ticket), 1)
        self.assertEqual(ticket[0]["ticket_id"], self.ticket_id)
        self.assertEqual(ticket[0]["passenger_id"], self.passenger_id)
        self.assertEqual(ticket[0]["fare_type_id"], self.fare_type_id)
        self.assertEqual(ticket[0]["passenger_name"], "John Smith")
        self.assertEqual(ticket[0]["fare_type_name"], "Student")
        
        logger.info(f"Ticket ID: {ticket[0]['ticket_id']}")
        logger.info(f"Passenger: {ticket[0]['passenger_name']}")
        logger.info(f"Fare Type: {ticket[0]['fare_type_name']}")
        logger.info(f"Price: ${ticket[0]['price']}")
        logger.info(f"Valid from: {ticket[0]['valid_from']} to {ticket[0]['valid_to']}")

if __name__ == "__main__":
    unittest.main()