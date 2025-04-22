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

@router.get("/register", response_class=HTMLResponse)
async def register_form(request: Request):
    return templates.TemplateResponse("passenger/register.html", {"request": request})

@router.post("/register")
async def create_passenger(
    request: Request,
    passenger_full_name: str = Form(...),
    email: str = Form(...)
):
    errors = []
    
    if not passenger_full_name or len(passenger_full_name) < 3 or len(passenger_full_name) > 100:
        errors.append("Name must be between 3 and 100 characters")
    
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        errors.append("Please provide a valid email address")
        
    existing_email = execute_query("SELECT passenger_id FROM passenger WHERE email = %s", (email,))
    if existing_email:
        errors.append("This email address is already registered")
    
    if errors:
        return templates.TemplateResponse(
            "passenger/register.html", 
            {"request": request, "error": errors[0], "passenger_full_name": passenger_full_name, "email": email}
        )
    
    try:
        query = """
            INSERT INTO passenger (passenger_full_name, email) 
            VALUES (%s, %s)
        """
        params = (passenger_full_name, email)
        result = execute_query(query, params, fetch=False)
        
        if result and result.get("affected_rows", 0) > 0:
            passenger_id = result.get("last_insert_id")
            return RedirectResponse(url=f"/passenger/dashboard?passenger_id={passenger_id}", status_code=303)
        else:
            return templates.TemplateResponse(
                "passenger/register.html", 
                {"request": request, "error": "Failed to register passenger", 
                 "passenger_full_name": passenger_full_name, "email": email}
            )
    except IntegrityError as e:
        return templates.TemplateResponse(
            "passenger/register.html", 
            {"request": request, "error": f"Database integrity error: {str(e)}", 
             "passenger_full_name": passenger_full_name, "email": email}
        )

@router.get("/dashboard", response_class=HTMLResponse)
async def passenger_dashboard(request: Request, passenger_id: Optional[int] = None):
    if not passenger_id:
        passengers = execute_query("SELECT * FROM passenger")
        return templates.TemplateResponse(
            "passenger/select_passenger.html", 
            {"request": request, "passengers": passengers}
        )
    
    passenger = execute_query("SELECT * FROM passenger WHERE passenger_id = %s", (passenger_id,))
    if not passenger:
        raise HTTPException(status_code=404, detail="Passenger not found")
    
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

@router.get("/exemption/apply", response_class=HTMLResponse)
async def exemption_application_form(request: Request, passenger_id: int):
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
    errors = []
    
    passenger = execute_query("SELECT * FROM passenger WHERE passenger_id = %s", (passenger_id,))
    if not passenger:
        errors.append("Invalid passenger ID")
    
    fare_type = execute_query("SELECT * FROM fare_type WHERE fare_type_id = %s", (fare_type_id,))
    if not fare_type:
        errors.append("Invalid fare type selected")
    
    valid_categories = ["Student", "Senior", "Disability", "LowIncome"]
    if exemption_category not in valid_categories:
        errors.append("Invalid exemption category")
    
    valid_mime_types = ["application/pdf", "image/jpeg", "image/jpg", "image/png"]
    if document.content_type not in valid_mime_types:
        errors.append("Invalid document format. Please upload PDF, JPG, or PNG files only")
    
    file_content = await document.read()
    if len(file_content) > 5 * 1024 * 1024:
        errors.append("Document size exceeds the 5MB limit")
    
    existing_app = execute_query("""
        SELECT * FROM exemption_application 
        WHERE passenger_id = %s AND status IN ('Submitted', 'Pending')
    """, (passenger_id,))
    
    if existing_app:
        errors.append("You already have a pending exemption application")
    
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
    
    await document.seek(0)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        today = date.today()
        app_query = """
            INSERT INTO exemption_application (submitted_date, passenger_id, status) 
            VALUES (%s, %s, %s)
        """
        app_params = (today, passenger_id, "Submitted")
        
        print(f"\n[EXEMPTION APPLICATION CREATION - {datetime.now()}]")
        print("-" * 80)
        print(f"SQL QUERY: {app_query}")
        print(f"PARAMETERS: {app_params}")
        print("-" * 80)
        
        cursor.execute(app_query, app_params)
        
        application_id = cursor.lastrowid
        print(f"GENERATED APPLICATION ID: {application_id}")
        
        import uuid
        file_extension = os.path.splitext(document.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_location = f"uploads/{unique_filename}"
        
        os.makedirs("uploads", exist_ok=True)
        
        with open(file_location, "wb") as file_object:
            file_object.write(file_content)
        
        doc_query = """
            INSERT INTO document_record (application_id, document_type, document_value) 
            VALUES (%s, %s, %s)
        """
        doc_params = (application_id, document_description, file_location)
        cursor.execute(doc_query, doc_params)
        
        log_query = """
            INSERT INTO activity_log (activity_type, description, entity_id, entity_type, created_at)
            VALUES (%s, %s, %s, %s, NOW())
        """
        passenger_name = passenger[0]["passenger_full_name"] if passenger else f"Passenger ID: {passenger_id}"
        fare_type_name = fare_type[0]["type_name"] if fare_type else f"Fare Type ID: {fare_type_id}"
        log_description = f"New exemption application ({exemption_category}) submitted by {passenger_name} for {fare_type_name}"
        log_params = ("application_creation", log_description, application_id, "exemption_application")
        cursor.execute(log_query, log_params)
        
        conn.commit()
        print(f"[INFO] New exemption application created: ID {application_id}, Passenger ID {passenger_id}, Category {exemption_category}")
        cursor.close()
        close_connection(conn)
        
        return RedirectResponse(
            url=f"/passenger/dashboard?passenger_id={passenger_id}",
            status_code=303
        )
        
    except Exception as e:
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

@router.get("/exemptions", response_class=HTMLResponse)
async def view_exemptions(request: Request, passenger_id: int):
    passenger = execute_query("SELECT * FROM passenger WHERE passenger_id = %s", (passenger_id,))
    if not passenger:
        raise HTTPException(status_code=404, detail="Passenger not found")
    
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

@router.get("/exemption/status-report", response_class=HTMLResponse)
async def exemption_status_report(request: Request, passenger_id: int):
    try:
        passenger = execute_query("SELECT * FROM passenger WHERE passenger_id = %s", (passenger_id,))
        if not passenger:
            raise HTTPException(status_code=404, detail="Passenger not found")
        
        applications = execute_query("""
            SELECT ea.*, dr.document_type
            FROM exemption_application ea
            LEFT JOIN document_record dr ON ea.application_id = dr.application_id
            WHERE ea.passenger_id = %s
            ORDER BY ea.submitted_date DESC
        """, (passenger_id,))
        
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
        
        fare_type_lookup = {}
        for app in approved_applications:
            if app['exemption_id'] is not None:
                fare_type_lookup[app['application_id']] = {
                    'type_name': app['type_name'],
                    'description': app['description']
                }
        
        for app in applications:
            if app['application_id'] in fare_type_lookup:
                app['type_name'] = fare_type_lookup[app['application_id']]['type_name']
                app['description'] = fare_type_lookup[app['application_id']]['description']
            else:
                app['type_name'] = None
                app['description'] = None
        
        today = date.today()
        exemptions = execute_query("""
            SELECT e.*, ft.type_name, 
                DATEDIFF(e.valid_to, CURDATE()) as days_remaining
            FROM exemption e
            JOIN fare_type ft ON e.fare_type_id = ft.fare_type_id
            WHERE e.passenger_id = %s
            ORDER BY e.valid_to DESC
        """, (passenger_id,))
        
        return templates.TemplateResponse(
            "passenger/application_status.html",
            {
                "request": request, 
                "passenger": passenger[0], 
                "applications": applications,
                "exemptions": exemptions,
                "today": today
            }
        )
    except Exception as e:
        print(f"[ERROR] Error generating exemption status report: {str(e)}")
        return templates.TemplateResponse(
            "passenger/error.html",
            {
                "request": request,
                "error": "An error occurred while generating your exemption status report.",
                "details": str(e),
                "passenger_id": passenger_id
            }
        )