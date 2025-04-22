from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from datetime import date, datetime, timedelta
from typing import List, Optional

from app.models.models import FareType, Tariff, ExemptionApplication, Exemption
from app.database.config import execute_query, get_db_connection, close_connection

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Admin dashboard
@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Admin dashboard with overview of system metrics"""
    # Count of fare types
    fare_types_count = execute_query("SELECT COUNT(*) as count FROM fare_type")[0]['count']
    
    # Count of exemption applications by status
    exemption_stats = execute_query("""
        SELECT status, COUNT(*) as count 
        FROM exemption_application 
        GROUP BY status
    """)
    
    # Recent tickets
    recent_tickets = execute_query("""
        SELECT t.*, p.passenger_full_name, ft.type_name
        FROM ticket t
        JOIN passenger p ON t.passenger_id = p.passenger_id
        JOIN fare_type ft ON t.fare_type_id = ft.fare_type_id
        ORDER BY t.purchase_date DESC
        LIMIT 5
    """)
    
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "fare_types_count": fare_types_count,
            "exemption_stats": exemption_stats,
            "recent_tickets": recent_tickets
        }
    )

# 1.1 Create Fare Type
@router.get("/fare-types/create", response_class=HTMLResponse)
async def create_fare_type_form(request: Request):
    """Form for creating a new fare type"""
    return templates.TemplateResponse("admin/create_fare_type.html", {"request": request})

@router.post("/fare-types/create")
async def create_fare_type(
    request: Request,
    type_name: str = Form(...),
    description: str = Form(...),
    validity: str = Form(...),
    base_price: float = Form(...),
    discount_rate: float = Form(...)
):
    """Process fare type creation form with validation"""
    # Domain integrity validation
    errors = []
    
    # Validate type name (length and uniqueness)
    if not type_name or len(type_name) < 2 or len(type_name) > 50:
        errors.append("Type name must be between 2 and 50 characters")
    
    # Check if fare type name already exists
    existing_fare_type = execute_query("SELECT fare_type_id FROM fare_type WHERE type_name = %s", (type_name,))
    if existing_fare_type:
        errors.append(f"A fare type with name '{type_name}' already exists")
    
    # Validate description
    if not description or len(description) < 5:
        errors.append("Please provide a more detailed description (at least 5 characters)")
    
    # Validate numeric fields
    if base_price < 0:
        errors.append("Base price must be a positive number")
    
    if discount_rate < 0 or discount_rate > 100:
        errors.append("Discount rate must be between 0 and 100")
    
    # If validation fails, return to form with error
    if errors:
        return templates.TemplateResponse(
            "admin/create_fare_type.html", 
            {
                "request": request, 
                "error": errors[0],
                "type_name": type_name,
                "description": description,
                "validity": validity,
                "base_price": base_price,
                "discount_rate": discount_rate
            }
        )
    
    try:
        # Start transaction
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # First, create the fare type
        fare_query = """
            INSERT INTO fare_type (type_name, description, validity)
            VALUES (%s, %s, %s)
        """
        fare_params = (type_name, description, validity)
        
        # Log the fare type creation query with its parameters
        print(f"\n[FARE TYPE CREATION - {datetime.now()}]")
        print("-" * 80)
        print(f"SQL QUERY: {fare_query}")
        print(f"PARAMETERS: {fare_params}")
        print("-" * 80)
        
        cursor.execute(fare_query, fare_params)
        
        # Get the new fare type ID
        fare_type_id = cursor.lastrowid
        print(f"GENERATED FARE TYPE ID: {fare_type_id}")
        
        # Create the tariff
        tariff_query = """
            INSERT INTO tariff (base_price, discount_rate, fare_type_id)
            VALUES (%s, %s, %s)
        """
        tariff_params = (base_price, discount_rate, fare_type_id)
        
        # Log the tariff creation query with its parameters
        print(f"\n[TARIFF CREATION - {datetime.now()}]")
        print("-" * 80)
        print(f"SQL QUERY: {tariff_query}")
        print(f"PARAMETERS: {tariff_params}")
        print("-" * 80)
        
        cursor.execute(tariff_query, tariff_params)
        
        # Log the creation in activity_log table
        log_query = """
            INSERT INTO activity_log (activity_type, description, entity_id, entity_type, created_at)
            VALUES (%s, %s, %s, %s, NOW())
        """
        log_description = f"New fare type '{type_name}' created with base price {base_price} and discount rate {discount_rate}%"
        log_params = ("fare_type_creation", log_description, fare_type_id, "fare_type")
        
        # Log the activity log insertion
        print(f"\n[ACTIVITY LOG ENTRY - {datetime.now()}]")
        print("-" * 80)
        print(f"SQL QUERY: {log_query}")
        print(f"PARAMETERS: {log_params}")
        print("-" * 80)
        
        cursor.execute(log_query, log_params)
        
        # Commit the transaction
        conn.commit()
        print(f"[INFO] New fare type created: ID {fare_type_id}, Name '{type_name}', Base Price {base_price}")
        cursor.close()
        close_connection(conn)
        
        return RedirectResponse(url="/admin/fare-types", status_code=303)
    
    except Exception as e:
        # Rollback in case of error to maintain data consistency
        if 'conn' in locals() and conn.is_connected():
            conn.rollback()
            cursor.close()
            close_connection(conn)
        
        print(f"[ERROR] Failed to create fare type: {str(e)}")
        return templates.TemplateResponse(
            "admin/create_fare_type.html", 
            {
                "request": request, 
                "error": f"Database error: {str(e)}",
                "type_name": type_name,
                "description": description,
                "validity": validity,
                "base_price": base_price,
                "discount_rate": discount_rate
            }
        )

# 1.2 Update Fare Type
@router.get("/fare-types", response_class=HTMLResponse)
async def list_fare_types(request: Request):
    """List all fare types for management"""
    fare_types = execute_query("""
        SELECT ft.*, t.base_price, t.discount_rate
        FROM fare_type ft
        JOIN tariff t ON ft.fare_type_id = t.fare_type_id
    """)
    
    return templates.TemplateResponse(
        "admin/fare_types.html",
        {"request": request, "fare_types": fare_types}
    )

@router.get("/fare-types/{fare_type_id}/edit", response_class=HTMLResponse)
async def edit_fare_type_form(request: Request, fare_type_id: int):
    """Form for editing an existing fare type"""
    fare_type = execute_query("""
        SELECT ft.*, t.base_price, t.discount_rate, t.tariff_id
        FROM fare_type ft
        JOIN tariff t ON ft.fare_type_id = t.fare_type_id
        WHERE ft.fare_type_id = %s
    """, (fare_type_id,))
    
    if not fare_type:
        raise HTTPException(status_code=404, detail="Fare type not found")
    
    return templates.TemplateResponse(
        "admin/edit_fare_type.html",
        {"request": request, "fare_type": fare_type[0]}
    )

@router.post("/fare-types/{fare_type_id}/edit")
async def update_fare_type(
    request: Request,
    fare_type_id: int,
    type_name: str = Form(...),
    description: str = Form(...),
    validity: str = Form(...),
    base_price: float = Form(...),
    discount_rate: float = Form(...),
    tariff_id: int = Form(...)
):
    """Process fare type update form"""
    try:
        # Start transaction
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Update fare type
        fare_query = """
            UPDATE fare_type 
            SET type_name = %s, description = %s, validity = %s
            WHERE fare_type_id = %s
        """
        fare_params = (type_name, description, validity, fare_type_id)
        
        # Log the fare type update query with its parameters
        print(f"\n[FARE TYPE UPDATE - {datetime.now()}]")
        print("-" * 80)
        print(f"SQL QUERY: {fare_query}")
        print(f"PARAMETERS: {fare_params}")
        print("-" * 80)
        
        cursor.execute(fare_query, fare_params)
        
        # Update tariff
        tariff_query = """
            UPDATE tariff 
            SET base_price = %s, discount_rate = %s
            WHERE tariff_id = %s
        """
        tariff_params = (base_price, discount_rate, tariff_id)
        
        # Log the tariff update query with its parameters
        print(f"\n[TARIFF UPDATE - {datetime.now()}]")
        print("-" * 80)
        print(f"SQL QUERY: {tariff_query}")
        print(f"PARAMETERS: {tariff_params}")
        print("-" * 80)
        
        cursor.execute(tariff_query, tariff_params)
        
        # Log the update in activity_log table
        log_query = """
            INSERT INTO activity_log (activity_type, description, entity_id, entity_type, created_at)
            VALUES (%s, %s, %s, %s, NOW())
        """
        log_description = f"Fare type '{type_name}' (ID: {fare_type_id}) updated with base price {base_price} and discount rate {discount_rate}%"
        log_params = ("fare_type_update", log_description, fare_type_id, "fare_type")
        
        # Log the activity log insertion
        print(f"\n[ACTIVITY LOG ENTRY - {datetime.now()}]")
        print("-" * 80)
        print(f"SQL QUERY: {log_query}")
        print(f"PARAMETERS: {log_params}")
        print("-" * 80)
        
        cursor.execute(log_query, log_params)
        
        # Commit the transaction
        conn.commit()
        print(f"[INFO] Fare type updated: ID {fare_type_id}, Name '{type_name}'")
        cursor.close()
        close_connection(conn)
        
        return RedirectResponse(url="/admin/fare-types", status_code=303)
    
    except Exception as e:
        # Rollback in case of error to maintain data consistency
        if 'conn' in locals() and conn.is_connected():
            conn.rollback()
            cursor.close()
            close_connection(conn)
        
        print(f"[ERROR] Failed to update fare type: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update fare type: {str(e)}")

# 1.3 Delete Fare Type
@router.get("/fare-types/{fare_type_id}/delete", response_class=HTMLResponse)
async def delete_fare_type_form(request: Request, fare_type_id: int):
    """Confirmation page for deleting a fare type"""
    fare_type = execute_query("""
        SELECT ft.*, t.base_price, t.discount_rate
        FROM fare_type ft
        JOIN tariff t ON ft.fare_type_id = t.fare_type_id
        WHERE ft.fare_type_id = %s
    """, (fare_type_id,))
    
    if not fare_type:
        raise HTTPException(status_code=404, detail="Fare type not found")
    
    # Check for dependencies (tickets using this fare type)
    tickets = execute_query("""
        SELECT COUNT(*) as count FROM ticket
        WHERE fare_type_id = %s
    """, (fare_type_id,))
    
    dependency_count = tickets[0]['count'] if tickets else 0
    
    return templates.TemplateResponse(
        "admin/delete_fare_type.html",
        {
            "request": request, 
            "fare_type": fare_type[0],
            "dependency_count": dependency_count
        }
    )

@router.post("/fare-types/{fare_type_id}/delete")
async def delete_fare_type(
    request: Request,
    fare_type_id: int,
    confirm: bool = Form(...)
):
    """Process fare type deletion"""
    if not confirm:
        return RedirectResponse(url="/admin/fare-types", status_code=303)
    
    try:
        # Start transaction
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get fare type details before deletion for logging
        fare_type_info = execute_query("""
            SELECT ft.*, t.base_price, t.discount_rate
            FROM fare_type ft
            JOIN tariff t ON ft.fare_type_id = t.fare_type_id
            WHERE ft.fare_type_id = %s
        """, (fare_type_id,))
        
        fare_type_name = fare_type_info[0]['type_name'] if fare_type_info else "Unknown"
        
        # Delete the fare type (and related tariff due to CASCADE)
        query = "DELETE FROM fare_type WHERE fare_type_id = %s"
        
        # Log the deletion query with its parameters
        print(f"\n[FARE TYPE DELETION - {datetime.now()}]")
        print("-" * 80)
        print(f"SQL QUERY: {query}")
        print(f"PARAMETERS: ({fare_type_id},)")
        print("-" * 80)
        
        cursor.execute(query, (fare_type_id,))
        
        # Log the deletion in activity_log table
        log_query = """
            INSERT INTO activity_log (activity_type, description, entity_id, entity_type, created_at)
            VALUES (%s, %s, %s, %s, NOW())
        """
        log_description = f"Fare type '{fare_type_name}' (ID: {fare_type_id}) was deleted"
        log_params = ("fare_type_deletion", log_description, fare_type_id, "fare_type")
        
        # Log the activity log insertion
        print(f"\n[ACTIVITY LOG ENTRY - {datetime.now()}]")
        print("-" * 80)
        print(f"SQL QUERY: {log_query}")
        print(f"PARAMETERS: {log_params}")
        print("-" * 80)
        
        cursor.execute(log_query, log_params)
        
        # Commit the transaction
        conn.commit()
        print(f"[INFO] Fare type deleted: ID {fare_type_id}, Name '{fare_type_name}'")
        cursor.close()
        close_connection(conn)
        
        return RedirectResponse(url="/admin/fare-types", status_code=303)
    
    except Exception as e:
        # Rollback in case of error to maintain data consistency
        if 'conn' in locals() and conn.is_connected():
            conn.rollback()
            cursor.close()
            close_connection(conn)
        
        print(f"[ERROR] Failed to delete fare type: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete fare type: {str(e)}")

# 2.2 Validate Documents and 2.3 Approve/Reject Request
@router.get("/exemption-applications", response_class=HTMLResponse)
async def list_exemption_applications(request: Request, status: Optional[str] = None):
    """List all exemption applications with optional filtering by status"""
    query = """
        SELECT ea.*, p.passenger_full_name
        FROM exemption_application ea
        JOIN passenger p ON ea.passenger_id = p.passenger_id
    """
    
    params = ()
    if status:
        query += " WHERE ea.status = %s"
        params = (status,)
        
    query += " ORDER BY ea.submitted_date DESC"
    
    applications = execute_query(query, params)
    
    return templates.TemplateResponse(
        "admin/exemption_applications.html",
        {"request": request, "applications": applications, "current_status": status}
    )

@router.get("/exemption-applications/{application_id}", response_class=HTMLResponse)
async def view_exemption_application(request: Request, application_id: int):
    """View details of a specific exemption application with documents"""
    application = execute_query("""
        SELECT ea.*, p.passenger_full_name, p.email
        FROM exemption_application ea
        JOIN passenger p ON ea.passenger_id = p.passenger_id
        WHERE ea.application_id = %s
    """, (application_id,))
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Get uploaded documents
    documents = execute_query("""
        SELECT * FROM document_record
        WHERE application_id = %s
    """, (application_id,))
    
    # Get available fare types for exemptions
    fare_types = execute_query("SELECT * FROM fare_type")
    
    return templates.TemplateResponse(
        "admin/view_application.html",
        {
            "request": request, 
            "application": application[0],
            "documents": documents,
            "fare_types": fare_types
        }
    )

@router.post("/exemption-applications/{application_id}/process")
async def process_exemption_application(
    request: Request,
    application_id: int,
    decision: str = Form(...),
    fare_type_id: Optional[int] = Form(None),
    exemption_category: Optional[str] = Form(None)
):
    """Process an exemption application (approve or reject)"""
    # Update application status
    status_query = """
        UPDATE exemption_application
        SET status = %s
        WHERE application_id = %s
    """
    status_params = (decision, application_id)
    execute_query(status_query, status_params, fetch=False)
    
    # If approved, create an exemption record
    if decision == "Approved" and fare_type_id and exemption_category:
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
            execute_query(exemption_query, exemption_params, fetch=False)
    
    return RedirectResponse(
        url="/admin/exemption-applications",
        status_code=303
    )

# 5.1 Generate Fare Usage Report
@router.get("/reports/fare-usage", response_class=HTMLResponse)
async def fare_usage_report(request: Request, start_date: Optional[str] = None, end_date: Optional[str] = None):
    """Generate fare usage report with optional date filtering"""
    today = date.today()
    if not start_date:
        # Default to last 30 days
        start_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    if not end_date:
        end_date = today.strftime("%Y-%m-%d")
    
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
    
    # Calculate totals
    total_tickets = sum(row["tickets_sold"] for row in report_data) if report_data else 0
    total_revenue = sum(row["total_revenue"] for row in report_data) if report_data else 0
    
    return templates.TemplateResponse(
        "admin/fare_usage_report.html",
        {
            "request": request,
            "report_data": report_data,
            "start_date": start_date,
            "end_date": end_date,
            "total_tickets": total_tickets,
            "total_revenue": total_revenue
        }
    )

# 5.2 Generate Exemption Statistics
@router.get("/reports/exemption-stats", response_class=HTMLResponse)
async def exemption_statistics_report(request: Request, period: Optional[str] = None):
    """Generate exemption statistics report"""
    today = date.today()
    start_date = None
    
    if period == "week":
        start_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    elif period == "month":
        start_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    elif period == "year":
        start_date = (today - timedelta(days=365)).strftime("%Y-%m-%d")
    else:
        # Default to all-time
        period = "all"
    
    # Base query for exemption applications
    query = """
        SELECT 
            exemption_category,
            COUNT(a.application_id) as total_applications,
            SUM(CASE WHEN a.status = 'Approved' THEN 1 ELSE 0 END) as approved,
            (SUM(CASE WHEN a.status = 'Approved' THEN 1 ELSE 0 END) / COUNT(a.application_id)) * 100 as approval_rate
        FROM exemption e
        JOIN exemption_application a ON e.passenger_id = a.passenger_id
    """
    
    params = ()
    if start_date:
        query += " WHERE a.submitted_date >= %s"
        params = (start_date,)
    
    query += " GROUP BY exemption_category ORDER BY total_applications DESC"
    
    stats = execute_query(query, params if params else None)
    
    return templates.TemplateResponse(
        "admin/exemption_statistics.html",
        {
            "request": request,
            "stats": stats,
            "period": period
        }
    )