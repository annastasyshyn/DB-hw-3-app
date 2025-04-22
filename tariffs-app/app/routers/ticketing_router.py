from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from datetime import date
from typing import List, Optional
import uuid

from app.models.models import Ticket, FareCalculation, PaymentConfirmation
from app.database.config import execute_query

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# 3.1 Retrieve Passenger Profile
@router.get("/passengers", response_class=HTMLResponse)
async def list_passengers(request: Request):
    """List all passengers for ticketing staff to select from"""
    passengers = execute_query("SELECT * FROM passenger")
    return templates.TemplateResponse(
        "ticketing/passenger_list.html",
        {"request": request, "passengers": passengers}
    )

@router.get("/passenger/{passenger_id}", response_class=HTMLResponse)
async def passenger_profile(request: Request, passenger_id: int):
    """Retrieve and display passenger profile with exemptions"""
    # Get passenger details
    passenger = execute_query(
        "SELECT * FROM passenger WHERE passenger_id = %s", 
        (passenger_id,)
    )
    
    if not passenger:
        raise HTTPException(status_code=404, detail="Passenger not found")
    
    # Get passenger's exemptions
    exemptions = execute_query("""
        SELECT e.*, ft.type_name 
        FROM exemption e
        JOIN fare_type ft ON e.fare_type_id = ft.fare_type_id
        WHERE e.passenger_id = %s AND CURDATE() BETWEEN e.valid_from AND e.valid_to
    """, (passenger_id,))
    
    return templates.TemplateResponse(
        "ticketing/passenger_profile.html",
        {"request": request, "passenger": passenger[0], "exemptions": exemptions}
    )

# 3.2 Determine Fare Type and 3.3 Apply Exemptions
@router.get("/calculate-fare/{passenger_id}", response_class=HTMLResponse)
async def calculate_fare_form(request: Request, passenger_id: int):
    """Form for calculating fare based on passenger and journey details"""
    passenger = execute_query(
        "SELECT * FROM passenger WHERE passenger_id = %s", 
        (passenger_id,)
    )
    
    if not passenger:
        raise HTTPException(status_code=404, detail="Passenger not found")
    
    # Get all fare types
    fare_types = execute_query("SELECT * FROM fare_type")
    
    # Get eligible exemptions for this passenger
    exemptions = execute_query("""
        SELECT e.*, ft.type_name 
        FROM exemption e
        JOIN fare_type ft ON e.fare_type_id = ft.fare_type_id
        WHERE e.passenger_id = %s AND CURDATE() BETWEEN e.valid_from AND e.valid_to
    """, (passenger_id,))
    
    return templates.TemplateResponse(
        "ticketing/calculate_fare.html",
        {
            "request": request, 
            "passenger": passenger[0], 
            "fare_types": fare_types,
            "exemptions": exemptions
        }
    )

# 3.4 Calculate Final Price
@router.post("/calculate-fare")
async def calculate_final_price(
    request: Request,
    passenger_id: int = Form(...),
    fare_type_id: int = Form(...),
    exemption_id: Optional[int] = Form(None)
):
    """Calculate the final ticket price based on fare type and exemptions"""
    try:
        # Log the incoming request parameters for debugging
        print(f"[DEBUG] Fare calculation - passenger_id: {passenger_id}, fare_type_id: {fare_type_id}, exemption_id: {exemption_id}")
        
        # Get fare type and base price
        fare_info = execute_query("""
            SELECT ft.*, t.base_price, t.discount_rate
            FROM fare_type ft
            JOIN tariff t ON ft.fare_type_id = t.fare_type_id
            WHERE ft.fare_type_id = %s
        """, (fare_type_id,))
        
        if not fare_info or len(fare_info) == 0:
            print(f"[ERROR] Fare type not found for ID: {fare_type_id}")
            raise HTTPException(status_code=404, detail="Fare type not found")
            
        base_fare = float(fare_info[0]["base_price"])
        discount_rate = 0
        
        # Apply exemption discount if provided
        if exemption_id:
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
        
        print(f"[DEBUG] Fare calculation results - base_fare: {base_fare}, discount_rate: {discount_rate}%, discount_amount: {discount_amount}, final_fare: {final_fare}")
        
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
        
        # Store calculation result in session for ticket creation
        calculation = {
            "passenger_id": passenger_id,
            "passenger_name": passenger[0]["passenger_full_name"] if passenger else "Unknown",
            "fare_type_id": fare_type_id,
            "fare_type_name": fare_type[0]["type_name"] if fare_type else "Unknown",
            "base_fare": base_fare,
            "discount_rate": discount_rate,
            "discount": discount_amount,
            "final_fare": final_fare
        }
        
        return templates.TemplateResponse(
            "ticketing/fare_result.html",
            {"request": request, "calculation": calculation}
        )
    except Exception as e:
        print(f"[ERROR] Error calculating fare: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error calculating fare: {str(e)}")

# 4.1 Confirm Payment and 4.2 Generate Ticket
@router.post("/issue-ticket")
async def issue_ticket(
    request: Request,
    passenger_id: int = Form(...),
    fare_type_id: int = Form(...),
    base_fare: float = Form(...),
    discount: float = Form(...),
    final_fare: float = Form(...),
    payment_method: str = Form(...)
):
    """Issue a new ticket after payment confirmation"""
    # Create a new ticket
    ticket_query = """
        INSERT INTO ticket (purchase_date, price, passenger_id, fare_type_id)
        VALUES (%s, %s, %s, %s)
    """
    today = date.today()
    ticket_params = (today, final_fare, passenger_id, fare_type_id)
    
    ticket_result = execute_query(ticket_query, ticket_params, fetch=False)
    
    if not ticket_result or ticket_result.get("affected_rows", 0) == 0:
        raise HTTPException(status_code=500, detail="Failed to create ticket")
    
    # Get the new ticket ID
    ticket_id = execute_query(
        "SELECT LAST_INSERT_ID() as ticket_id", 
        fetch=True
    )[0]["ticket_id"]
    
    # Record fare calculation
    calc_query = """
        INSERT INTO fare_calculation (ticket_id, base_fare, discount, final_fare)
        VALUES (%s, %s, %s, %s)
    """
    calc_params = (ticket_id, base_fare, discount, final_fare)
    execute_query(calc_query, calc_params, fetch=False)
    
    # Record payment confirmation
    payment_query = """
        INSERT INTO payment_confirmation (ticket_id, status, payment_method, transaction_ref)
        VALUES (%s, %s, %s, %s)
    """
    # Generate a unique transaction reference
    transaction_ref = f"TXN{date.today().strftime('%Y%m%d')}-{ticket_id}"
    payment_params = (ticket_id, "Confirmed", payment_method, transaction_ref)
    execute_query(payment_query, payment_params, fetch=False)
    
    # Get detailed ticket information for display
    ticket = execute_query("""
        SELECT t.*, p.passenger_full_name, ft.type_name, pc.payment_method, pc.transaction_ref
        FROM ticket t
        JOIN passenger p ON t.passenger_id = p.passenger_id
        JOIN fare_type ft ON t.fare_type_id = ft.fare_type_id
        JOIN payment_confirmation pc ON t.ticket_id = pc.ticket_id
        WHERE t.ticket_id = %s
    """, (ticket_id,))
    
    if ticket:
        return templates.TemplateResponse(
            "ticketing/ticket_issued.html",
            {"request": request, "ticket": ticket[0]}
        )
    else:
        raise HTTPException(status_code=500, detail="Error retrieving ticket information")