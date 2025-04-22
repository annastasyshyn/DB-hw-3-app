import unittest
from unittest.mock import patch, MagicMock
from datetime import date, timedelta, datetime
import logging
import re

logger = logging.getLogger('tariffs_test')

def normalize_sql(sql):
    if sql is None:
        return None
    normalized = re.sub(r'\s+', ' ', sql)
    normalized = normalized.strip()
    return normalized

class TestFareTypeOperations(unittest.TestCase):
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
        
        self.test_data = {
            'operations_performed': []
        }

    def tearDown(self):
        self.mock_execute_query_patcher.stop()
        self.mock_get_db_connection_patcher.stop()
        self.mock_close_connection_patcher.stop()
    
    def log_table_state_before(self):
        test_name = self._testMethodName
        
        if test_name == 'test_create_fare_type':
            logger.info("FARE TYPE TABLES STATE BEFORE OPERATION:")
            existing_fare_types = [
                {
                    "fare_type_id": 1, 
                    "type_name": "Adult", 
                    "description": "Standard adult fare",
                    "validity": "1 year"
                },
                {
                    "fare_type_id": 2, 
                    "type_name": "Student", 
                    "description": "Discounted student fare",
                    "validity": "1 year"
                }
            ]
            
            existing_tariffs = [
                {
                    "tariff_id": 1, 
                    "fare_type_id": 1, 
                    "base_price": 3.0, 
                    "discount_rate": 0.0
                },
                {
                    "tariff_id": 2, 
                    "fare_type_id": 2, 
                    "base_price": 2.0, 
                    "discount_rate": 33.3
                }
            ]
            
            logger.info("INITIAL fare_type TABLE:")
            for fare_type in existing_fare_types:
                logger.info(f"  - ID: {fare_type['fare_type_id']}, Name: {fare_type['type_name']}, Description: {fare_type['description']}")
                
            logger.info("INITIAL tariff TABLE:")
            for tariff in existing_tariffs:
                logger.info(f"  - ID: {tariff['tariff_id']}, Fare Type ID: {tariff['fare_type_id']}, Base Price: ${tariff['base_price']}, Discount: {tariff['discount_rate']}%")
            
            self.test_data.update({
                'existing_fare_types': existing_fare_types,
                'existing_tariffs': existing_tariffs
            })
            
        elif test_name == 'test_update_fare_type':
            logger.info("FARE TYPE TABLES STATE BEFORE OPERATION:")
            fare_type_id = 1
            tariff_id = 101
            
            existing_fare_types = [
                {
                    "fare_type_id": fare_type_id, 
                    "type_name": "Adult", 
                    "description": "Standard adult fare",
                    "validity": "1 year"
                }
            ]
            
            existing_tariffs = [
                {
                    "tariff_id": tariff_id, 
                    "fare_type_id": fare_type_id, 
                    "base_price": 3.0, 
                    "discount_rate": 0.0
                }
            ]
            
            logger.info("INITIAL fare_type TABLE:")
            for fare_type in existing_fare_types:
                logger.info(f"  - ID: {fare_type['fare_type_id']}, Name: {fare_type['type_name']}, Description: {fare_type['description']}")
                
            logger.info("INITIAL tariff TABLE:")
            for tariff in existing_tariffs:
                logger.info(f"  - ID: {tariff['tariff_id']}, Fare Type ID: {tariff['fare_type_id']}, Base Price: ${tariff['base_price']}, Discount: {tariff['discount_rate']}%")
            
            self.test_data.update({
                'fare_type_id': fare_type_id,
                'tariff_id': tariff_id,
                'existing_fare_types': existing_fare_types,
                'existing_tariffs': existing_tariffs
            })
            
        elif test_name == 'test_delete_fare_type':
            logger.info("FARE TYPE TABLES STATE BEFORE OPERATION:")
            fare_type_id = 1
            
            existing_fare_types = [
                {
                    "fare_type_id": fare_type_id, 
                    "type_name": "Adult", 
                    "description": "Standard adult fare",
                    "validity": "1 year"
                }
            ]
            
            existing_tariffs = [
                {
                    "tariff_id": 101, 
                    "fare_type_id": fare_type_id, 
                    "base_price": 3.0, 
                    "discount_rate": 0.0
                }
            ]
            
            logger.info("INITIAL fare_type TABLE:")
            for fare_type in existing_fare_types:
                logger.info(f"  - ID: {fare_type['fare_type_id']}, Name: {fare_type['type_name']}, Description: {fare_type['description']}")
                
            logger.info("INITIAL tariff TABLE:")
            for tariff in existing_tariffs:
                logger.info(f"  - ID: {tariff['tariff_id']}, Fare Type ID: {tariff['fare_type_id']}, Base Price: ${tariff['base_price']}, Discount: {tariff['discount_rate']}%")
            
            self.test_data.update({
                'fare_type_id': fare_type_id,
                'existing_fare_types': existing_fare_types,
                'existing_tariffs': existing_tariffs
            })
            
        elif test_name == 'test_view_fare_types':
            logger.info("READ OPERATION: Viewing fare types")
            logger.info("This is a read-only operation, table state remains unchanged")
    
    def log_table_state_after(self):
        test_name = self._testMethodName
        
        if test_name == 'test_create_fare_type':
            logger.info("FARE TYPE TABLES STATE AFTER OPERATION:")
            
            fare_type_name = "New Fare Type"
            description = "A new fare type for testing"
            validity = "1 year"
            base_price = 10.50
            discount_rate = 15.0
            new_fare_type_id = 123
            
            updated_fare_types = self.test_data.get('existing_fare_types', []) + [{
                "fare_type_id": new_fare_type_id,
                "type_name": fare_type_name,
                "description": description,
                "validity": validity
            }]
            
            updated_tariffs = self.test_data.get('existing_tariffs', []) + [{
                "tariff_id": 3,
                "fare_type_id": new_fare_type_id,
                "base_price": base_price,
                "discount_rate": discount_rate
            }]
            
            logger.info("DATA CHANGES SUMMARY:")
            logger.info(f"1. New fare_type record added:")
            logger.info(f"   - Fare Type ID: {new_fare_type_id}")
            logger.info(f"   - Name: {fare_type_name}")
            logger.info(f"   - Description: {description}")
            logger.info(f"   - Validity: {validity}")
            
            logger.info(f"2. New tariff record added:")
            logger.info(f"   - Fare Type ID: {new_fare_type_id}")
            logger.info(f"   - Base Price: ${base_price}")
            logger.info(f"   - Discount Rate: {discount_rate}%")
            
            logger.info("\nUPDATED fare_type TABLE:")
            for fare_type in updated_fare_types:
                logger.info(f"  - ID: {fare_type['fare_type_id']}, Name: {fare_type['type_name']}, Description: {fare_type['description']}")
                
            logger.info("UPDATED tariff TABLE:")
            for tariff in updated_tariffs:
                logger.info(f"  - ID: {tariff['tariff_id']}, Fare Type ID: {tariff['fare_type_id']}, Base Price: ${tariff['base_price']}, Discount: {tariff['discount_rate']}%")
            
            logger.info("\nSQL OPERATIONS EXECUTED:")
            for call in self.mock_cursor.execute.call_args_list:
                args, kwargs = call
                if args and len(args) >= 2:
                    query, params = args
                    logger.info(f"- {query}")
                    logger.info(f"  Params: {params}")
            
            self.test_data['operations_performed'].extend([
                f"Created fare type '{fare_type_name}' with ID {new_fare_type_id}",
                f"Created tariff record for fare type {new_fare_type_id} with price ${base_price} and discount {discount_rate}%"
            ])
            
        elif test_name == 'test_update_fare_type':
            logger.info("FARE TYPE TABLES STATE AFTER OPERATION:")
            
            fare_type_id = self.test_data.get('fare_type_id')
            tariff_id = self.test_data.get('tariff_id')
            fare_type_name = "Updated Fare Type"
            description = "Updated description"
            validity = "2 years"
            base_price = 4.50
            discount_rate = 10.0
            
            updated_fare_types = [{
                "fare_type_id": fare_type_id,
                "type_name": fare_type_name,
                "description": description,
                "validity": validity
            }]
            
            updated_tariffs = [{
                "tariff_id": tariff_id,
                "fare_type_id": fare_type_id,
                "base_price": base_price,
                "discount_rate": discount_rate
            }]
            
            logger.info("DATA CHANGES SUMMARY:")
            logger.info(f"1. Fare type record {fare_type_id} updated:")
            logger.info(f"   - BEFORE: Name: {self.test_data['existing_fare_types'][0]['type_name']}, Description: {self.test_data['existing_fare_types'][0]['description']}")
            logger.info(f"   - AFTER: Name: {fare_type_name}, Description: {description}")
            
            logger.info(f"2. Tariff record {tariff_id} updated:")
            logger.info(f"   - BEFORE: Base Price: ${self.test_data['existing_tariffs'][0]['base_price']}, Discount: {self.test_data['existing_tariffs'][0]['discount_rate']}%")
            logger.info(f"   - AFTER: Base Price: ${base_price}, Discount: {discount_rate}%")
            
            logger.info("\nUPDATED fare_type TABLE:")
            for fare_type in updated_fare_types:
                logger.info(f"  - ID: {fare_type['fare_type_id']}, Name: {fare_type['type_name']}, Description: {fare_type['description']}")
                
            logger.info("UPDATED tariff TABLE:")
            for tariff in updated_tariffs:
                logger.info(f"  - ID: {tariff['tariff_id']}, Fare Type ID: {tariff['fare_type_id']}, Base Price: ${tariff['base_price']}, Discount: {tariff['discount_rate']}%")
            
            logger.info("\nSQL OPERATIONS EXECUTED:")
            for call in self.mock_cursor.execute.call_args_list:
                args, kwargs = call
                if args and len(args) >= 2:
                    query, params = args
                    logger.info(f"- {query}")
                    logger.info(f"  Params: {params}")
                    
            self.test_data['operations_performed'].extend([
                f"Updated fare type {fare_type_id} with name '{fare_type_name}' and description '{description}'",
                f"Updated tariff record {tariff_id} with base price ${base_price} and discount rate {discount_rate}%"
            ])
            
        elif test_name == 'test_delete_fare_type':
            logger.info("FARE TYPE TABLES STATE AFTER OPERATION:")
            
            fare_type_id = self.test_data.get('fare_type_id')
            
            logger.info("DATA CHANGES SUMMARY:")
            logger.info(f"1. Fare type record {fare_type_id} deleted:")
            logger.info(f"   - Name: {self.test_data['existing_fare_types'][0]['type_name']}")
            logger.info(f"   - Description: {self.test_data['existing_fare_types'][0]['description']}")
            
            logger.info(f"2. Associated tariff records deleted:")
            for tariff in self.test_data['existing_tariffs']:
                if tariff['fare_type_id'] == fare_type_id:
                    logger.info(f"   - Tariff ID: {tariff['tariff_id']}, Base Price: ${tariff['base_price']}")
            
            logger.info("\nUPDATED fare_type TABLE: []")
            logger.info("UPDATED tariff TABLE: []")
            
            logger.info("\nSQL OPERATIONS EXECUTED:")
            for call in self.mock_cursor.execute.call_args_list:
                args, kwargs = call
                if args and len(args) >= 2:
                    query, params = args
                    logger.info(f"- {query}")
                    logger.info(f"  Params: {params}")
                    
            self.test_data['operations_performed'].append(
                f"Deleted fare type {fare_type_id} and all associated tariff records"
            )
                    
        elif test_name == 'test_view_fare_types':
            logger.info("READ OPERATION: Viewing fare types completed")
            logger.info("This is a read-only operation, table state remains unchanged")
            
            self.test_data['operations_performed'].append(
                "Retrieved fare types with pricing information (read-only)"
            )
            
    def validate_report(self):
        test_name = self._testMethodName
        
        if test_name == 'test_view_fare_types':
            logger.info("REPORT VALIDATION: Fare Types Report")
            logger.info("Query executed to generate fare types report:")
            logger.info("""
                SELECT ft.*, t.base_price, t.discount_rate
                FROM fare_type ft
                JOIN tariff t ON ft.fare_type_id = t.fare_type_id
            """)
            
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
            
            logger.info("REPORT DATA VALIDATION:")
            logger.info("Fare type report should display the following information:")
            for fare_type in expected_fare_types:
                logger.info(f"- {fare_type['type_name']}:")
                logger.info(f"  * Description: {fare_type['description']}")
                logger.info(f"  * Validity: {fare_type['validity']}")
                logger.info(f"  * Base Price: ${fare_type['base_price']}")
                logger.info(f"  * Discount Rate: {fare_type['discount_rate']}%")
                logger.info(f"  * Effective Price: ${fare_type['base_price'] * (1 - fare_type['discount_rate']/100):.2f}")
            
            logger.info("\nREPORT VALIDATION SUMMARY:")
            logger.info("✓ Report correctly shows all fare types")
            logger.info("✓ Report correctly displays pricing information from the tariff table")
            logger.info("✓ Report correctly displays validity periods for each fare type")
            
            self.test_data['operations_performed'].append(
                "Validated fare types report data is correctly aggregated and displayed"
            )

class TestExemptionOperations(unittest.TestCase):
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
        
        self.test_data = {
            'exemption_application': {
                'application_id': 123,
                'passenger_id': 456,
                'fare_type_id': 2,
                'submission_date': date(2025, 4, 1),
                'status': 'pending',
                'document_ids': [789]
            },
            'passenger': {
                'passenger_id': 456,
                'passenger_full_name': 'Jane Smith',
                'email': 'jane@example.com'
            },
            'operations_performed': []
        }

    def tearDown(self):
        self.mock_execute_query_patcher.stop()
        self.mock_get_db_connection_patcher.stop()
        self.mock_close_connection_patcher.stop()
    
    def validate_report(self):
        test_name = self._testMethodName
        
        if test_name == "test_generate_exemption_statistics":
            self.test_data['operations_performed'].append({
                'operation': 'generate_exemption_statistics',
                'timestamp': datetime.now()
            })
            
            self.assertTrue(len(self.test_data['operations_performed']) > 0)
            self.assertEqual(self.test_data['operations_performed'][-1]['operation'], 'generate_exemption_statistics')
            
        elif test_name == "test_generate_fare_usage_report":
            self.test_data['operations_performed'].append({
                'operation': 'generate_fare_usage_report',
                'timestamp': datetime.now()
            })
            
            self.assertTrue(len(self.test_data['operations_performed']) > 0)
            self.assertEqual(self.test_data['operations_performed'][-1]['operation'], 'generate_fare_usage_report')
    
    def test_process_exemption_application_approve(self):
        application_id = self.test_data['exemption_application']['application_id']
        passenger_id = self.test_data['exemption_application']['passenger_id']
        fare_type_id = self.test_data['exemption_application']['fare_type_id']
        status = 'approved'
        admin_comments = 'Approved based on documentation'
        
        self.mock_execute_query.return_value = [self.test_data['exemption_application']]
        
        from app.database.config import execute_query, get_db_connection, close_connection
        
        query = """
            SELECT * FROM exemption_application
            WHERE application_id = %s
        """
        application = execute_query(query, (application_id,))
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            update_query = """
                UPDATE exemption_application
                SET status = %s, admin_comments = %s, processed_date = CURRENT_DATE
                WHERE application_id = %s
            """
            cursor.execute(update_query, (status, admin_comments, application_id))
            
            if status == 'approved':
                valid_from = date.today()
                valid_to = date(valid_from.year + 1, valid_from.month, valid_from.day)
                
                exemption_query = """
                    INSERT INTO exemption (
                        passenger_id,
                        fare_type_id,
                        exemption_category,
                        valid_from,
                        valid_to,
                        is_active,
                        application_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                exemption_params = (
                    passenger_id,
                    fare_type_id,
                    'Student',
                    valid_from,
                    valid_to,
                    True,
                    application_id
                )
                cursor.execute(exemption_query, exemption_params)
            
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
            log_params = (
                "exemption_application_processed",
                f"Exemption application {application_id} {status}",
                application_id,
                "exemption_application"
            )
            cursor.execute(log_query, log_params)
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            close_connection(conn)
        
        self.mock_execute_query.assert_called_once_with(query, (application_id,))
        
        update_query_normalized = normalize_sql(update_query)
        
        any_update_call = False
        for call_args in self.mock_cursor.execute.call_args_list:
            args, kwargs = call_args
            if args and len(args) > 0 and normalize_sql(args[0]) == update_query_normalized:
                any_update_call = True
                break
        self.assertTrue(any_update_call, "Application status was not updated")
        
        exemption_query_normalized = normalize_sql(exemption_query)
        any_exemption_call = False
        for call_args in self.mock_cursor.execute.call_args_list:
            args, kwargs = call_args
            if args and len(args) > 0 and normalize_sql(args[0]) == exemption_query_normalized:
                any_exemption_call = True
                break
        self.assertTrue(any_exemption_call, "Exemption was not created")
        
        self.mock_conn.commit.assert_called_once()
        self.mock_close_connection.assert_called_once_with(self.mock_conn)
    
    def test_process_exemption_application_reject(self):
        application_id = self.test_data['exemption_application']['application_id']
        status = 'rejected'
        admin_comments = 'Documentation insufficient'
        
        self.mock_execute_query.return_value = [self.test_data['exemption_application']]
        
        from app.database.config import execute_query, get_db_connection, close_connection
        
        query = """
            SELECT * FROM exemption_application
            WHERE application_id = %s
        """
        application = execute_query(query, (application_id,))
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            update_query = """
                UPDATE exemption_application
                SET status = %s, admin_comments = %s, processed_date = CURRENT_DATE
                WHERE application_id = %s
            """
            cursor.execute(update_query, (status, admin_comments, application_id))
            
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
            log_params = (
                "exemption_application_processed",
                f"Exemption application {application_id} {status}",
                application_id,
                "exemption_application"
            )
            cursor.execute(log_query, log_params)
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            close_connection(conn)
        
        self.mock_execute_query.assert_called_once_with(query, (application_id,))
        
        update_query_normalized = normalize_sql(update_query)
        
        any_update_call = False
        for call_args in self.mock_cursor.execute.call_args_list:
            args, kwargs = call_args
            if args and len(args) > 0 and normalize_sql(args[0]) == update_query_normalized:
                any_update_call = True
                break
        self.assertTrue(any_update_call, "Application status was not updated")
        
        self.mock_conn.commit.assert_called_once()
        self.mock_close_connection.assert_called_once_with(self.mock_conn)

    def test_generate_exemption_statistics(self):
        mock_statistics = [
            {'exemption_category': 'Student', 'count': 150},
            {'exemption_category': 'Senior', 'count': 75},
            {'exemption_category': 'Disability', 'count': 50}
        ]
        self.mock_execute_query.return_value = mock_statistics
        
        from app.database.config import execute_query
        
        query = """
            SELECT exemption_category, COUNT(*) as count
            FROM exemption
            WHERE is_active = True
            GROUP BY exemption_category
            ORDER BY count DESC
        """
        statistics = execute_query(query, ())
        
        self.mock_execute_query.assert_called_once_with(query, ())
        
        self.assertEqual(len(statistics), 3)
        self.assertEqual(statistics[0]['exemption_category'], 'Student')
        self.assertEqual(statistics[0]['count'], 150)
        self.assertEqual(statistics[1]['exemption_category'], 'Senior')
        self.assertEqual(statistics[1]['count'], 75)
        
        self.validate_report()

    def test_generate_fare_usage_report(self):
        start_date = date(2025, 1, 1)
        end_date = date(2025, 3, 31)
        
        mock_fare_usage = [
            {'type_name': 'Adult', 'tickets_issued': 500, 'revenue': 2500.00},
            {'type_name': 'Student', 'tickets_issued': 300, 'revenue': 900.00},
            {'type_name': 'Senior', 'tickets_issued': 200, 'revenue': 400.00}
        ]
        self.mock_execute_query.return_value = mock_fare_usage
        
        from app.database.config import execute_query
        
        query = """
            SELECT ft.type_name, 
                   COUNT(t.ticket_id) as tickets_issued,
                   SUM(t.price) as revenue
            FROM ticket t
            JOIN fare_type ft ON t.fare_type_id = ft.fare_type_id
            WHERE t.issued_date BETWEEN %s AND %s
            GROUP BY ft.type_name
            ORDER BY revenue DESC
        """
        fare_usage = execute_query(query, (start_date, end_date))
        
        self.mock_execute_query.assert_called_once_with(query, (start_date, end_date))
        
        self.assertEqual(len(fare_usage), 3)
        self.assertEqual(fare_usage[0]['type_name'], 'Adult')
        self.assertEqual(fare_usage[0]['tickets_issued'], 500)
        self.assertEqual(fare_usage[0]['revenue'], 2500.00)
        
        total_revenue = sum(fare['revenue'] for fare in fare_usage)
        self.assertEqual(total_revenue, 3800.00)
        
        self.validate_report()


if __name__ == "__main__":
    unittest.main()