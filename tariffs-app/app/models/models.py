from pydantic import BaseModel
from typing import Optional, List
from datetime import date

class Passenger(BaseModel):
    passenger_id: Optional[int] = None
    passenger_full_name: str
    email: str

class FareType(BaseModel):
    fare_type_id: Optional[int] = None
    type_name: str
    description: str
    validity: str

class Tariff(BaseModel):
    tariff_id: Optional[int] = None
    base_price: float
    discount_rate: float
    fare_type_id: int

class ExemptionApplication(BaseModel):
    application_id: Optional[int] = None
    submitted_date: date
    passenger_id: int
    status: str = "Submitted"

class DocumentRecord(BaseModel):
    record_id: Optional[int] = None
    application_id: int
    document_type: str
    document_value: str  # File path or reference

class Exemption(BaseModel):
    exemption_id: Optional[int] = None
    exemption_category: str
    passenger_id: int
    fare_type_id: int
    valid_from: date
    valid_to: date

class Ticket(BaseModel):
    ticket_id: Optional[int] = None
    purchase_date: date
    price: float
    passenger_id: int
    fare_type_id: int

class FareCalculation(BaseModel):
    calculation_id: Optional[int] = None
    ticket_id: int
    base_fare: float
    discount: float
    final_fare: float

class PaymentConfirmation(BaseModel):
    payment_id: Optional[int] = None
    ticket_id: int
    status: str = "Confirmed"
    payment_method: str
    transaction_ref: Optional[str] = None

# Custom response models
class PassengerExemptionSummary(BaseModel):
    passenger_id: int
    passenger_full_name: str
    email: str
    exemptions: List[Exemption] = []

class FareUsageReport(BaseModel):
    date: date
    fare_type: str
    tickets_sold: int
    total_revenue: float

class ExemptionStatistics(BaseModel):
    exemption_category: str
    total_applications: int
    approved: int
    approval_rate: float