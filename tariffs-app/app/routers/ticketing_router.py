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
    
    try:
        # First, verify the passenger exists
        passenger = execute_query("SELECT * FROM passenger WHERE passenger_id = %s", (passenger_id,), fetch=True)
        if not passenger:
            print(f"[ERROR] Passenger not found for ID: {passenger_id}")
            raise HTTPException(status_code=404, detail="Passenger not found")
            
        # Verify the fare type exists
        fare_type = execute_query("SELECT * FROM fare_type WHERE fare_type_id = %s", (fare_type_id,), fetch=True)
        if not fare_type:
            print(f"[ERROR] Fare type not found for ID: {fare_type_id}")
            raise HTTPException(status_code=404, detail="Fare type not found")
            
        # Insert the ticket record
        ticket_result = execute_query(ticket_query, ticket_params, fetch=False)
        
        if not ticket_result or ticket_result.get("affected_rows", 0) == 0:
            print(f"[ERROR] Failed to create ticket: {ticket_result}")
            raise HTTPException(status_code=500, detail="Failed to create ticket")
        
        # Get the new ticket ID using the lastrowid from the result
        ticket_id = ticket_result.get("last_insert_id")
        
        if not ticket_id:
            # Fall back to using LAST_INSERT_ID() if lastrowid isn't available
            ticket_id_result = execute_query("SELECT LAST_INSERT_ID() as ticket_id", fetch=True)
            if ticket_id_result and len(ticket_id_result) > 0:
                ticket_id = ticket_id_result[0]["ticket_id"]
            else:
                print("[ERROR] Could not retrieve ticket ID")
                raise HTTPException(status_code=500, detail="Could not retrieve ticket ID")
        
        print(f"[DEBUG] Created new ticket with ID: {ticket_id}")
        
        # Record fare calculation
        calc_query = """
            INSERT INTO fare_calculation (ticket_id, base_fare, discount, final_fare)
            VALUES (%s, %s, %s, %s)
        """
        calc_params = (ticket_id, base_fare, discount, final_fare)
        calc_result = execute_query(calc_query, calc_params, fetch=False)
        print(f"[DEBUG] Added fare calculation: {calc_result}")
        
        # Record payment confirmation
        payment_query = """
            INSERT INTO payment_confirmation (ticket_id, status, payment_method, transaction_ref)
            VALUES (%s, %s, %s, %s)
        """
        # Generate a unique transaction reference
        transaction_ref = f"TXN{date.today().strftime('%Y%m%d')}-{ticket_id}"
        payment_params = (ticket_id, "Confirmed", payment_method, transaction_ref)
        payment_result = execute_query(payment_query, payment_params, fetch=False)
        print(f"[DEBUG] Added payment confirmation: {payment_result}")
        
        # Double-verify the ticket record exists in the database
        ticket_check = execute_query("SELECT * FROM ticket WHERE ticket_id = %s", (ticket_id,), fetch=True)
        if not ticket_check or len(ticket_check) == 0:
            print(f"[ERROR] Ticket record not found for ID: {ticket_id}")
            # Attempt to show all recent tickets for debugging
            recent_tickets = execute_query("SELECT * FROM ticket ORDER BY ticket_id DESC LIMIT 5", fetch=True)
            print(f"[DEBUG] Recent tickets: {recent_tickets}")
            raise HTTPException(status_code=500, detail="Ticket record not found after creation")
            
        # Get detailed ticket information for display - Use LEFT JOIN to ensure we get the ticket even if related data is missing
        ticket = execute_query("""
            SELECT t.*, p.passenger_full_name, ft.type_name, pc.payment_method, pc.transaction_ref
            FROM ticket t
            LEFT JOIN passenger p ON t.passenger_id = p.passenger_id
            LEFT JOIN fare_type ft ON t.fare_type_id = ft.fare_type_id
            LEFT JOIN payment_confirmation pc ON t.ticket_id = pc.ticket_id
            WHERE t.ticket_id = %s
        """, (ticket_id,), fetch=True)
        
        print(f"[DEBUG] Retrieved ticket info: {ticket}")
        
        if ticket and len(ticket) > 0:
            return templates.TemplateResponse(
                "ticketing/ticket_issued.html",
                {"request": request, "ticket": ticket[0]}
            )
        else:
            print(f"[ERROR] No ticket found with ID: {ticket_id} after successful verification")
            raise HTTPException(status_code=500, detail="Ticket was created but could not be retrieved")
            
    except Exception as e:
        print(f"[ERROR] Exception in ticket issuance process: {str(e)}")
        import traceback
        traceback.print_exc()
        # Try to provide more specific error information
        error_detail = str(e)
        if "payment_confirmation" in error_detail.lower():
            error_detail = "Error with payment confirmation"
        elif "fare_calculation" in error_detail.lower():
            error_detail = "Error with fare calculation"
        elif "foreign key constraint" in error_detail.lower():
            if "passenger_id" in error_detail.lower():
                error_detail = "Invalid passenger ID"
            elif "fare_type_id" in error_detail.lower():
                error_detail = "Invalid fare type ID"
            else:
                error_detail = "Foreign key constraint violation"
        
        raise HTTPException(status_code=500, detail=f"Error retrieving ticket information: {error_detail}")