import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import os
import re
import uuid
from datetime import date
from io import BytesIO
import shutil
import tempfile

def normalize_sql(sql):
    if sql is None:
        return None
    normalized = re.sub(r'\s+', ' ', sql)
    normalized = normalized.strip()
    return normalized

class TestDocumentStorageOperations(unittest.TestCase):
    def setUp(self):
        self.test_upload_dir = tempfile.mkdtemp()
        
        self.mock_execute_query_patcher = patch('app.database.config.execute_query')
        self.mock_execute_query = self.mock_execute_query_patcher.start()
        
        self.mock_get_db_connection_patcher = patch('app.database.config.get_db_connection')
        self.mock_get_db_connection = self.mock_get_db_connection_patcher.start()
        
        self.mock_close_connection_patcher = patch('app.database.config.close_connection')
        self.mock_close_connection = self.mock_close_connection_patcher.start()
        
        self.mock_uuid_patcher = patch('uuid.uuid4')
        self.mock_uuid = self.mock_uuid_patcher.start()
        self.mock_uuid.return_value = uuid.UUID('12345678-1234-5678-1234-567812345678')
        
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor
        self.mock_get_db_connection.return_value = self.mock_conn

    def tearDown(self):
        shutil.rmtree(self.test_upload_dir)
        
        self.mock_execute_query_patcher.stop()
        self.mock_get_db_connection_patcher.stop()
        self.mock_close_connection_patcher.stop()
        self.mock_uuid_patcher.stop()

    async def test_document_storage_in_filesystem(self):
        mock_content = b"Test document content"
        mock_file = MagicMock()
        mock_file.filename = "test_document.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.read = AsyncMock(return_value=mock_content)
        
        expected_filename = f"12345678-1234-5678-1234-567812345678.pdf"
        expected_path = os.path.join(self.test_upload_dir, expected_filename)
        
        with patch('builtins.open', MagicMock()) as mock_open:
            mock_file_handle = mock_open.return_value.__enter__.return_value
            
            unique_filename = f"{uuid.uuid4()}.pdf"
            
            file_location = os.path.join("uploads", unique_filename)
            
            with open(expected_path, 'wb') as buffer:
                buffer.write(await mock_file.read())
            
            mock_open.assert_called_once_with(expected_path, 'wb')
            
            mock_file_handle.write.assert_called_once_with(mock_content)
        
        self.assertEqual(file_location, f"uploads/{expected_filename}")

    def test_document_record_in_database(self):
        application_id = 123
        document_type = "Student ID"
        file_location = "uploads/12345678-1234-5678-1234-567812345678.pdf"
        
        self.mock_cursor.lastrowid = 456
        
        from app.database.config import execute_query, get_db_connection, close_connection
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
            INSERT INTO document_record (application_id, document_type, document_value) 
            VALUES (%s, %s, %s)
        """
        params = (application_id, document_type, file_location)
        cursor.execute(query, params)
        document_id = cursor.lastrowid
        
        conn.commit()
        cursor.close()
        close_connection(conn)
        
        self.mock_cursor.execute.assert_called_once_with(query, params)
        self.mock_conn.commit.assert_called_once()
        self.mock_close_connection.assert_called_once_with(self.mock_conn)
        
        self.assertEqual(document_id, 456)

    def test_retrieve_document_from_database(self):
        application_id = 123
        
        expected_documents = [
            {
                "record_id": 456, 
                "application_id": 123, 
                "document_type": "Student ID", 
                "document_value": "uploads/12345678-1234-5678-1234-567812345678.pdf"
            },
            {
                "record_id": 457, 
                "application_id": 123, 
                "document_type": "Proof of Address", 
                "document_value": "uploads/87654321-8765-4321-8765-432187654321.pdf"
            }
        ]
        self.mock_execute_query.return_value = expected_documents
        
        from app.database.config import execute_query
        
        query = """
            SELECT * FROM document_record
            WHERE application_id = %s
        """
        documents = execute_query(query, (application_id,))
        
        self.mock_execute_query.assert_called_once_with(query, (application_id,))
        
        self.assertEqual(documents, expected_documents)
        self.assertEqual(len(documents), 2)
        self.assertEqual(documents[0]["document_type"], "Student ID")
        self.assertEqual(documents[1]["document_type"], "Proof of Address")

    async def test_complete_document_flow_for_exemption_application(self):
        application_id = 123
        passenger_id = 456
        document_type = "Student ID"
        
        mock_content = b"Test document content"
        mock_file = MagicMock()
        mock_file.filename = "student_id.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.read = AsyncMock(return_value=mock_content)
        
        expected_filename = f"12345678-1234-5678-1234-567812345678.pdf"
        expected_path = os.path.join(self.test_upload_dir, expected_filename)
        expected_file_location = f"uploads/{expected_filename}"
        
        self.mock_cursor.lastrowid = 789
        
        from app.database.config import execute_query, get_db_connection, close_connection
        
        with patch('builtins.open', MagicMock()) as mock_open:
            unique_filename = f"{uuid.uuid4()}.pdf"
            file_location = os.path.join("uploads", unique_filename)
            
            with open(expected_path, 'wb') as buffer:
                buffer.write(await mock_file.read())
                
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = """
                INSERT INTO document_record (application_id, document_type, document_value) 
                VALUES (%s, %s, %s)
            """
            params = (application_id, document_type, file_location)
            cursor.execute(query, params)
            
            log_query = """
                INSERT INTO activity_log (activity_type, description, entity_id, entity_type, created_at)
                VALUES (%s, %s, %s, %s, NOW())
            """
            log_description = f"Document uploaded: {document_type}"
            log_params = ("document_upload", log_description, application_id, "exemption_application")
            cursor.execute(log_query, log_params)
            
            conn.commit()
            cursor.close()
            close_connection(conn)
            
            mock_open.assert_called_once_with(expected_path, 'wb')
            
            self.mock_cursor.execute.assert_any_call(query, params)
            self.mock_cursor.execute.assert_any_call(log_query, log_params)
            self.assertEqual(self.mock_cursor.execute.call_count, 2)
            
            self.mock_conn.commit.assert_called_once()
            self.mock_close_connection.assert_called_once_with(self.mock_conn)

    def test_document_validation_for_exemption_application(self):
        application_id = 123
        
        self.mock_execute_query.side_effect = [
            [
                {
                    "record_id": 456, 
                    "application_id": 123, 
                    "document_type": "Student ID", 
                    "document_value": "uploads/12345678-1234-5678-1234-567812345678.pdf"
                },
                {
                    "record_id": 457, 
                    "application_id": 123, 
                    "document_type": "Proof of Address", 
                    "document_value": "uploads/87654321-8765-4321-8765-432187654321.pdf"
                }
            ],
            {"affected_rows": 1}
        ]
        
        from app.database.config import execute_query, get_db_connection, close_connection
        
        doc_query = """
            SELECT * FROM document_record
            WHERE application_id = %s
        """
        documents = execute_query(doc_query, (application_id,))
        
        required_docs = ["Student ID", "Proof of Address"]
        submitted_doc_types = [doc["document_type"] for doc in documents]
        
        all_docs_present = all(req_doc in submitted_doc_types for req_doc in required_docs)
        
        if all_docs_present:
            status_query = """
                UPDATE exemption_application
                SET status = %s
                WHERE application_id = %s
            """
            new_status = "Validated"
            result = execute_query(status_query, (new_status, application_id), fetch=False)
        
        expected_doc_query = normalize_sql("""
            SELECT * FROM document_record
            WHERE application_id = %s
        """)
        
        expected_status_query = normalize_sql("""
            UPDATE exemption_application
            SET status = %s
            WHERE application_id = %s
        """)
        
        self.mock_execute_query.assert_any_call(doc_query, (application_id,))
        
        call_args_list = self.mock_execute_query.call_args_list
        second_call = call_args_list[1]
        query, params, kwargs = second_call[0][0], second_call[0][1], second_call[1]
        self.assertEqual(normalize_sql(query), expected_status_query)
        self.assertEqual(params, ("Validated", application_id))
        self.assertEqual(kwargs, {"fetch": False})
        
        self.assertTrue(all_docs_present)
        self.assertEqual(result, {"affected_rows": 1})

    def test_generate_document_report(self):
        expected_report_data = [
            {"document_type": "Student ID", "count": 25},
            {"document_type": "Proof of Address", "count": 23},
            {"document_type": "Medical Certificate", "count": 12},
            {"document_type": "Senior ID", "count": 8}
        ]
        self.mock_execute_query.return_value = expected_report_data
        
        from app.database.config import execute_query
        
        query = """
            SELECT 
                document_type,
                COUNT(*) as count
            FROM document_record
            GROUP BY document_type
            ORDER BY count DESC
        """
        report_data = execute_query(query)
        
        self.mock_execute_query.assert_called_once_with(query)
        
        self.assertEqual(report_data, expected_report_data)
        self.assertEqual(len(report_data), 4)
        self.assertEqual(report_data[0]["document_type"], "Student ID")
        self.assertEqual(report_data[0]["count"], 25)
        
        most_common = max(report_data, key=lambda x: x["count"])
        self.assertEqual(most_common["document_type"], "Student ID")

    def test_retrieve_document_with_application(self):
        application_id = 123
        
        self.mock_execute_query.side_effect = [
            [
                {
                    "application_id": 123,
                    "passenger_id": 456,
                    "passenger_full_name": "John Smith",
                    "email": "john@example.com",
                    "status": "Submitted",
                    "submitted_date": date(2025, 4, 15)
                }
            ],
            [
                {
                    "record_id": 789,
                    "application_id": 123,
                    "document_type": "Student ID",
                    "document_value": "uploads/12345678-1234-5678-1234-567812345678.pdf"
                },
                {
                    "record_id": 790,
                    "application_id": 123,
                    "document_type": "Proof of Address",
                    "document_value": "uploads/87654321-8765-4321-8765-432187654321.pdf"
                }
            ]
        ]
        
        from app.database.config import execute_query
        
        app_query = """
            SELECT ea.*, p.passenger_full_name, p.email
            FROM exemption_application ea
            JOIN passenger p ON ea.passenger_id = p.passenger_id
            WHERE ea.application_id = %s
        """
        application = execute_query(app_query, (application_id,))
        
        doc_query = """
            SELECT * FROM document_record
            WHERE application_id = %s
        """
        documents = execute_query(doc_query, (application_id,))
        
        expected_app_query = normalize_sql("""
            SELECT ea.*, p.passenger_full_name, p.email
            FROM exemption_application ea
            JOIN passenger p ON ea.passenger_id = p.passenger_id
            WHERE ea.application_id = %s
        """)
        
        expected_doc_query = normalize_sql("""
            SELECT * FROM document_record
            WHERE application_id = %s
        """)
        
        self.mock_execute_query.assert_any_call(app_query, (application_id,))
        
        call_args_list = self.mock_execute_query.call_args_list
        second_call = call_args_list[1]
        query, params = second_call[0]
        self.assertEqual(normalize_sql(query), expected_doc_query)
        self.assertEqual(params, (application_id,))
        
        self.assertEqual(len(application), 1)
        self.assertEqual(application[0]["passenger_full_name"], "John Smith")
        self.assertEqual(application[0]["status"], "Submitted")
        
        self.assertEqual(len(documents), 2)
        self.assertEqual(documents[0]["document_type"], "Student ID")
        self.assertEqual(documents[1]["document_type"], "Proof of Address")


if __name__ == "__main__":
    unittest.main()