-- clean out old database and create new one
DROP DATABASE IF EXISTS tariffs_exemptions;
CREATE DATABASE IF NOT EXISTS tariffs_exemptions;
USE tariffs_exemptions;

-- 1. passengers
CREATE TABLE IF NOT EXISTS passenger (
    passenger_id        INT           PRIMARY KEY AUTO_INCREMENT COMMENT 'PK: passenger',
    passenger_full_name VARCHAR(100)  NOT NULL COMMENT 'Complete passenger name',
    email               VARCHAR(100)  NOT NULL COMMENT 'Email address',
    UNIQUE (email)
) COMMENT='Individuals using the transport service.';

-- 2. fare categories
CREATE TABLE IF NOT EXISTS fare_type (
    fare_type_id INT           PRIMARY KEY AUTO_INCREMENT COMMENT 'PK: fare category',
    type_name    VARCHAR(50)  NOT NULL COMMENT 'Name of fare (e.g., student)',
    description  TEXT  NOT NULL COMMENT 'Description of fare type',
    validity     VARCHAR(50)  NOT NULL COMMENT 'Validity period'
) COMMENT='Categories of fares.';

-- 3. pricing rules
CREATE TABLE IF NOT EXISTS tariff (
    tariff_id     INT             PRIMARY KEY AUTO_INCREMENT COMMENT 'PK: pricing rule',
    base_price    DECIMAL(10,2)   NOT NULL COMMENT 'Standard fare',
    discount_rate DECIMAL(5,2)    DEFAULT 0 COMMENT 'Percentage discount',
    fare_type_id  INT             NOT NULL COMMENT 'FK → fare_type',
    CONSTRAINT fk_tariff_fare_type
        FOREIGN KEY(fare_type_id) REFERENCES fare_type(fare_type_id)
        ON DELETE CASCADE
) COMMENT='Pricing rules for each fare category.';

-- 4. tickets
CREATE TABLE IF NOT EXISTS ticket (
    ticket_id     INT             PRIMARY KEY AUTO_INCREMENT COMMENT 'PK: ticket',
    purchase_date DATE            NOT NULL COMMENT 'When purchased',
    price         DECIMAL(10,2)   NOT NULL COMMENT 'Final paid amount',
    passenger_id  INT             NOT NULL COMMENT 'FK → passenger',
    fare_type_id  INT             NOT NULL COMMENT 'FK → fare_type',
    CONSTRAINT fk_ticket_passenger
        FOREIGN KEY(passenger_id) REFERENCES passenger(passenger_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_ticket_fare_type
        FOREIGN KEY(fare_type_id) REFERENCES fare_type(fare_type_id)
        ON DELETE CASCADE
) COMMENT='Validated travel passes.';

-- 5. exemption applications
CREATE TABLE IF NOT EXISTS exemption_application (
    application_id INT       PRIMARY KEY AUTO_INCREMENT COMMENT 'PK: application',
    submitted_date DATE      NOT NULL COMMENT 'When applied',
    passenger_id   INT       NOT NULL COMMENT 'FK → passenger',
    status         VARCHAR(20) NOT NULL DEFAULT 'Submitted' COMMENT 'Status of application',
    CONSTRAINT fk_exapp_passenger
        FOREIGN KEY(passenger_id) REFERENCES passenger(passenger_id)
        ON DELETE CASCADE
) COMMENT='Users apply here to request an exemption.';

-- 6. uploaded docs per application
CREATE TABLE IF NOT EXISTS document_record (
    record_id      INT           PRIMARY KEY AUTO_INCREMENT COMMENT 'PK: document record',
    application_id INT           NOT NULL COMMENT 'FK → exemption_application',
    document_type  VARCHAR(50)  NOT NULL COMMENT 'e.g., student ID',
    document_value VARCHAR(255)  NOT NULL COMMENT 'File path or ref',
    CONSTRAINT fk_docrec_exapp
        FOREIGN KEY(application_id) REFERENCES exemption_application(application_id)
        ON DELETE CASCADE
) COMMENT='Documents submitted to support an exemption application.';

-- 7. granted exemptions
CREATE TABLE IF NOT EXISTS exemption (
    exemption_id       INT           PRIMARY KEY AUTO_INCREMENT COMMENT 'PK: exemption',
    exemption_category VARCHAR(50)  NOT NULL COMMENT 'e.g., disability',
    passenger_id       INT           NOT NULL COMMENT 'Qualifying passenger',
    fare_type_id       INT           NOT NULL COMMENT 'FK → fare_type',
    valid_from         DATE          NOT NULL COMMENT 'Start date',
    valid_to           DATE          NOT NULL COMMENT 'End date',
    CONSTRAINT fk_exemption_passenger
        FOREIGN KEY(passenger_id) REFERENCES passenger(passenger_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_exemption_fare
        FOREIGN KEY(fare_type_id) REFERENCES fare_type(fare_type_id)
        ON DELETE CASCADE
) COMMENT='Approved exemptions for special fares.';

-- 8. which docs each exemption category requires
CREATE TABLE IF NOT EXISTS exemption_required_document (
    requirement_id INT           PRIMARY KEY AUTO_INCREMENT COMMENT 'PK',
    exemption_id   INT           NOT NULL COMMENT 'FK → exemption',
    document_type  VARCHAR(50)  NOT NULL COMMENT 'e.g., medical cert',
    CONSTRAINT fk_reqdoc_exemption
        FOREIGN KEY(exemption_id) REFERENCES exemption(exemption_id)
        ON DELETE CASCADE
) COMMENT='Docs needed to qualify for an exemption.';

-- 9. fare calculation records
CREATE TABLE IF NOT EXISTS fare_calculation (
    calculation_id INT PRIMARY KEY AUTO_INCREMENT COMMENT 'PK: calc record',
    ticket_id      INT NOT NULL COMMENT 'FK → ticket',
    base_fare      DECIMAL(10,2) NOT NULL COMMENT 'Original fare',
    discount       DECIMAL(10,2) NOT NULL COMMENT 'Discount amount',
    final_fare     DECIMAL(10,2) NOT NULL COMMENT 'Final fare after discount',
    CONSTRAINT fk_farecalc_ticket
        FOREIGN KEY(ticket_id) REFERENCES ticket(ticket_id)
        ON DELETE CASCADE
) COMMENT='Stores how each tickets fare was computed.';

-- 10. payment confirmations
CREATE TABLE IF NOT EXISTS payment_confirmation (
    payment_id INT PRIMARY KEY AUTO_INCREMENT COMMENT 'PK: payment conf',
    ticket_id  INT NOT NULL COMMENT 'FK → ticket',
    status     VARCHAR(20) NOT NULL COMMENT 'Payment status',
    payment_method VARCHAR(50) NOT NULL COMMENT 'Method of payment',
    transaction_ref VARCHAR(100) NULL COMMENT 'Transaction reference',
    CONSTRAINT fk_payconf_ticket
        FOREIGN KEY(ticket_id) REFERENCES ticket(ticket_id)
        ON DELETE CASCADE
) COMMENT='Confirms successful payment for a ticket.';

-- Insert sample data
-- 1. passengers
INSERT INTO passenger (passenger_id, passenger_full_name, email) VALUES
  (1, 'Alice Johnson', 'alice@example.com'),
  (2, 'Bob Smith', 'bob@example.com'),
  (3, 'Charlie Brown', 'charlie@example.com'),
  (4, 'Diana Prince', 'diana@example.com'),
  (5, 'Ethan Hunt', 'ethan@example.com');

-- 2. fare types
INSERT INTO fare_type (fare_type_id, type_name, description, validity) VALUES
  (1, 'Adult', 'Standard adult fare', '2025-01-01 to 2025-12-31'),
  (2, 'Student', 'Discounted rate for students', '2025-01-01 to 2025-12-31'),
  (3, 'Senior', 'Discounted rate for seniors', '2025-01-01 to 2025-12-31'),
  (4, 'Child', 'Discounted rate for children under 12', '2025-01-01 to 2025-12-31');

-- 3. tariffs
INSERT INTO tariff (tariff_id, base_price, discount_rate, fare_type_id) VALUES
  (1, 3.00,  0.00, 1),   -- Adult pays full fare
  (2, 3.00, 50.00, 2),   -- Student gets 50% off
  (3, 3.00, 60.00, 3),   -- Senior gets 60% off
  (4, 3.00, 75.00, 4);   -- Child gets 75% off

-- 4. tickets
INSERT INTO ticket (ticket_id, purchase_date, price, passenger_id, fare_type_id) VALUES
  (1, '2025-04-20', 3.00, 1, 1),   -- Alice buys Adult ticket
  (2, '2025-04-21', 1.50, 2, 2),   -- Bob buys Student ticket (after discount)
  (3, '2025-04-21', 1.20, 3, 3),   -- Charlie buys Senior ticket
  (4, '2025-04-22', 0.75, 4, 4),   -- Diana buys Child ticket
  (5, '2025-04-22', 3.00, 5, 1);   -- Ethan buys Adult ticket

-- 5. exemption application (Bob applies for student discount)
INSERT INTO exemption_application (application_id, submitted_date, passenger_id, status) VALUES
  (1, '2025-04-18', 2, 'Approved'),
  (2, '2025-04-19', 3, 'Approved'),
  (3, '2025-04-19', 4, 'Approved'),
  (4, '2025-04-20', 5, 'Pending');

-- 6. documents uploaded
INSERT INTO document_record (record_id, application_id, document_type, document_value) VALUES
  (1, 1, 'StudentID', '/path/to/bob_student_id.pdf'),
  (2, 2, 'SeniorID', '/path/to/charlie_senior_id.pdf'),
  (3, 3, 'BirthCertificate', '/path/to/diana_birth_cert.pdf'),
  (4, 4, 'EmployeeID', '/path/to/ethan_employee_id.pdf');

-- 7. granted exemptions
INSERT INTO exemption (exemption_id, exemption_category, passenger_id, fare_type_id, valid_from, valid_to) VALUES
  (1, 'Student Discount', 2, 2, '2025-04-18', '2026-04-18'),
  (2, 'Senior Discount', 3, 3, '2025-04-19', '2026-04-19'),
  (3, 'Child Discount', 4, 4, '2025-04-19', '2026-04-19');

-- 8. required docs for exemptions
INSERT INTO exemption_required_document (requirement_id, exemption_id, document_type) VALUES
  (1, 1, 'StudentID'),
  (2, 2, 'SeniorID'),
  (3, 3, 'BirthCertificate');

-- 9. fare calculation entries
INSERT INTO fare_calculation (calculation_id, ticket_id, base_fare, discount, final_fare) VALUES
  (1, 1, 3.00, 0.00, 3.00),
  (2, 2, 3.00, 1.50, 1.50),
  (3, 3, 3.00, 1.80, 1.20),
  (4, 4, 3.00, 2.25, 0.75),
  (5, 5, 3.00, 0.00, 3.00);

-- 10. payment confirmations
INSERT INTO payment_confirmation (payment_id, ticket_id, status, payment_method, transaction_ref) VALUES
  (1, 1, 'Confirmed', 'Card', 'TXN123456'),
  (2, 2, 'Confirmed', 'Cash', NULL),
  (3, 3, 'Confirmed', 'Card', 'TXN123457'),
  (4, 4, 'Confirmed', 'Mobile', 'TXN123458'),
  (5, 5, 'Confirmed', 'Card', 'TXN123459');
