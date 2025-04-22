from fastapi import APIRouter, Request, Form, File, UploadFile, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from datetime import date, datetime
from typing import List, Optional
import os
import re
from mysql.connector import IntegrityError

from app.models.models import Passenger, ExemptionApplication, DocumentRecord, PassengerExemptionSummary
from app.database.config import execute_query, get_db_connection, close_connection

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Route for passenger registration
@router.get("/register", response_class=HTMLResponse)
async def register_form(request: Request):
    """Form for passenger registration"""
    return templates.TemplateResponse("passenger/register.html", {"request": request})

@router.post("/register")
async def create_passenger(
    request: Request,
    passenger_full_name: str = Form(...),
    email: str = Form(...)
):
    """Process passenger registration form with validation"""
    # Domain integrity validation
    errors = []
    
    # Validate name length and format
    if not passenger_full_name or len(passenger_full_name) < 3 or len(passenger_full_name) > 100:
        errors.append("Name must be between 3 and 100 characters")
    
    # Validate email format
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        errors.append("Please provide a valid email address")
        
    # Check if email already exists (uniqueness constraint)
    existing_email = execute_query("SELECT passenger_id FROM passenger WHERE email = %s", (email,))
    if existing_email:
        errors.append("This email address is already registered")
    
    if errors:
        return templates.TemplateResponse(
            "passenger/register.html", 
            {"request": request, "error": errors[0], "passenger_full_name": passenger_full_name, "email": email}
        )
    
    # If validation passes, insert passenger into database
    try:
        query = """
            INSERT INTO passenger (passenger_full_name, email) 
            VALUES (%s, %s)
        """
        params = (passenger_full_name, email)
        result = execute_query(query, params, fetch=False)
        
        if result and result.get("affected_rows", 0) > 0:
            # Get the new passenger ID
            passenger_id = result.get("last_insert_id")
            return RedirectResponse(url=f"/passenger/dashboard?passenger_id={passenger_id}", status_code=303)
        else:
            return templates.TemplateResponse(
                "passenger/register.html", 
                {"request": request, "error": "Failed to register passenger", 
                 "passenger_full_name": passenger_full_name, "email": email}
            )
    except IntegrityError as e:
        # Catch any integrity constraint violations
        return templates.TemplateResponse(
            "passenger/register.html", 
            {"request": request, "error": f"Database integrity error: {str(e)}", 
             "passenger_full_name": passenger_full_name, "email": email}
        )

@router.get("/dashboard", response_class=HTMLResponse)
async def passenger_dashboard(request: Request, passenger_id: Optional[int] = None):
    """Passenger dashboard showing their profile and exemptions"""
    if not passenger_id:
        # In a real app, this would come from authentication
        # For demo purposes, we'll list all passengers to select from
        passengers = execute_query("SELECT * FROM passenger")
        return templates.TemplateResponse(
            "passenger/select_passenger.html", 
            {"request": request, "passengers": passengers}
        )
    
    passenger = execute_query("SELECT * FROM passenger WHERE passenger_id = %s", (passenger_id,))
    if not passenger:
        raise HTTPException(status_code=404, detail="Passenger not found")
    
    # Get passenger's exemptions
    exemptions = execute_query("""
        SELECT e.*, ft.type_name
        FROM exemption e
        JOIN fare_type ft ON e.fare_type_id = ft.fare_type_id
        WHERE e.passenger_id = %s
    """, (passenger_id,))
    
    return templates.TemplateResponse(
        "passenger/dashboard.html",
        {"request": request, "passenger": passenger[0], "exemptions": exemptions}
    )

# 2.1: Submit Exemption Request
@router.get("/exemption/apply", response_class=HTMLResponse)
async def exemption_application_form(request: Request, passenger_id: int):
    """Form for submitting an exemption application"""
    passenger = execute_query("SELECT * FROM passenger WHERE passenger_id = %s", (passenger_id,))
    if not passenger:
        raise HTTPException(status_code=404, detail="Passenger not found")
    
    fare_types = execute_query("SELECT * FROM fare_type")
    
    return templates.TemplateResponse(
        "passenger/exemption_application.html", 
        {"request": request, "passenger": passenger[0], "fare_types": fare_types}
    )

@router.post("/exemption/apply")
async def submit_exemption_application(
    request: Request,
    passenger_id: int = Form(...),
    exemption_category: str = Form(...),
    fare_type_id: int = Form(...),
    document_description: str = Form(...),
    document: UploadFile = File(...),
    confirm: bool = Form(...)
):
    """Process exemption application submission with document upload and validation"""
    # Domain and referential integrity validation
    errors = []
    
    # Validate passenger exists (referential integrity)
    passenger = execute_query("SELECT * FROM passenger WHERE passenger_id = %s", (passenger_id,))
    if not passenger:
        errors.append("Invalid passenger ID")
    
    # Validate fare type exists (referential integrity)
    fare_type = execute_query("SELECT * FROM fare_type WHERE fare_type_id = %s", (fare_type_id,))
    if not fare_type:
        errors.append("Invalid fare type selected")
    
    # Validate exemption category (domain integrity)
    valid_categories = ["Student", "Senior", "Disability", "LowIncome"]
    if exemption_category not in valid_categories:
        errors.append("Invalid exemption category")
    
    # Validate file type (domain integrity)
    valid_mime_types = ["application/pdf", "image/jpeg", "image/jpg", "image/png"]
    if document.content_type not in valid_mime_types:
        errors.append("Invalid document format. Please upload PDF, JPG, or PNG files only")
    
    # Validate file size - max 5MB (domain integrity)
    file_content = await document.read()
    if len(file_content) > 5 * 1024 * 1024:  # 5MB
        errors.append("Document size exceeds the 5MB limit")
    
    # Check for existing applications
    existing_app = execute_query("""
        SELECT * FROM exemption_application 
        WHERE passenger_id = %s AND status IN ('Submitted', 'Pending')
    """, (passenger_id,))
    
    if existing_app:
        errors.append("You already have a pending exemption application")
    
    # If validation fails, display error and form again
    if errors:
        fare_types = execute_query("SELECT * FROM fare_type")
        return templates.TemplateResponse(
            "passenger/exemption_application.html", 
            {
                "request": request, 
                "error": errors[0], 
                "passenger": passenger[0] if passenger else None,
                "fare_types": fare_types
            }
        )
    
    # Reset file position after reading for validation
    await document.seek(0)
    
    try:
        # Start transaction
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # First insert the application
        today = date.today()
        app_query = """
            INSERT INTO exemption_application (submitted_date, passenger_id, status) 
            VALUES (%s, %s, %s)
        """
        app_params = (today, passenger_id, "Submitted")
        
        # Log the exemption application creation query with its parameters
        print(f"\n[EXEMPTION APPLICATION CREATION - {datetime.now()}]")
        print("-" * 80)
        print(f"SQL QUERY: {app_query}")
        print(f"PARAMETERS: {app_params}")
        print("-" * 80)
        
        cursor.execute(app_query, app_params)
        
        # Get the new application ID
        application_id = cursor.lastrowid
        print(f"GENERATED APPLICATION ID: {application_id}")
        
        # Create a unique filename to prevent overwriting
        import uuid
        file_extension = os.path.splitext(document.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_location = f"uploads/{unique_filename}"
        
        # Ensure uploads directory exists
        os.makedirs("uploads", exist_ok=True)
        
        # Save the document to file
        with open(file_location, "wb") as file_object:
            file_object.write(file_content)
        
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
        passenger_name = passenger[0]["passenger_full_name"] if passenger else f"Passenger ID: {passenger_id}"
        fare_type_name = fare_type[0]["type_name"] if fare_type else f"Fare Type ID: {fare_type_id}"
        log_description = f"New exemption application ({exemption_category}) submitted by {passenger_name} for {fare_type_name}"
        log_params = ("application_creation", log_description, application_id, "exemption_application")
        cursor.execute(log_query, log_params)
        
        # Commit transaction
        conn.commit()
        print(f"[INFO] New exemption application created: ID {application_id}, Passenger ID {passenger_id}, Category {exemption_category}")
        cursor.close()
        close_connection(conn)
        
        # Redirect on success
        return RedirectResponse(
            url=f"/passenger/dashboard?passenger_id={passenger_id}",
            status_code=303
        )
        
    except Exception as e:
        # Rollback on error to maintain data consistency
        if 'conn' in locals() and conn.is_connected():
            conn.rollback()
            cursor.close()
            close_connection(conn)
        
        print(f"[ERROR] Failed to create exemption application: {str(e)}")
        fare_types = execute_query("SELECT * FROM fare_type")
        return templates.TemplateResponse(
            "passenger/exemption_application.html", 
            {
                "request": request, 
                "error": f"Database error: {str(e)}", 
                "passenger": passenger[0] if passenger else None,
                "fare_types": fare_types
            }
        )

# 2.4: View Passenger Exemptions
@router.get("/exemptions", response_class=HTMLResponse)
async def view_exemptions(request: Request, passenger_id: int):
    """View exemptions for a specific passenger"""
    passenger = execute_query("SELECT * FROM passenger WHERE passenger_id = %s", (passenger_id,))
    if not passenger:
        raise HTTPException(status_code=404, detail="Passenger not found")
    
    # Get all exemptions for the passenger with detailed information
    exemptions = execute_query("""
        SELECT e.*, ft.type_name, ea.status
        FROM exemption e
        JOIN fare_type ft ON e.fare_type_id = ft.fare_type_id
        JOIN exemption_application ea ON e.passenger_id = ea.passenger_id
        WHERE e.passenger_id = %s
    """, (passenger_id,))
    
    return templates.TemplateResponse(
        "passenger/exemptions.html",
        {"request": request, "passenger": passenger[0], "exemptions": exemptions}
    )