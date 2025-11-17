from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, Header
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import qrcode
from io import BytesIO
import requests
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Stripe setup
stripe_api_key = os.environ.get('STRIPE_API_KEY')

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# ============ MODELS ============

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    name: str
    picture: Optional[str] = None
    role: str = "attendee"  # attendee, organizer, admin
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserSession(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    session_token: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Category(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str

class Event(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    creator_id: str
    title: str
    description: str
    date: str  # ISO format datetime string
    location: str
    capacity: int
    category: str
    image_url: Optional[str] = None
    status: str = "active"  # active, cancelled
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class EventWithCreator(Event):
    creator_name: str
    creator_email: str

class TicketType(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_id: str
    name: str
    price: float  # 0 for free tickets
    quantity_available: int
    quantity_sold: int = 0

class Booking(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    event_id: str
    ticket_type_id: str
    quantity: int
    total_price: float
    status: str = "pending"  # pending, confirmed, cancelled
    payment_intent_id: Optional[str] = None
    qr_code_data: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class BookingWithDetails(Booking):
    event_title: str
    event_date: str
    event_location: str
    ticket_type_name: str

class PaymentTransaction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    booking_id: str
    user_id: str
    amount: float
    currency: str = "usd"
    payment_status: str = "pending"  # pending, paid, failed
    status: str = "initiated"  # initiated, completed, expired
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ============ INPUT MODELS ============

class EventCreate(BaseModel):
    title: str
    description: str
    date: str
    location: str
    capacity: int
    category: str
    image_url: Optional[str] = None

class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    date: Optional[str] = None
    location: Optional[str] = None
    capacity: Optional[int] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    status: Optional[str] = None

class TicketTypeCreate(BaseModel):
    name: str
    price: float
    quantity_available: int

class BookingCreate(BaseModel):
    event_id: str
    ticket_type_id: str
    quantity: int

class CheckoutRequest(BaseModel):
    booking_id: str
    origin_url: str

class RoleUpdateRequest(BaseModel):
    role: str

class UserWithRole(BaseModel):
    id: str
    email: str
    name: str
    picture: Optional[str] = None
    role: str
    created_at: str

# ============ AUTH HELPERS ============

async def get_current_user(request: Request, authorization: Optional[str] = Header(None)) -> Optional[User]:
    """Get current user from session token (cookie or header)"""
    session_token = request.cookies.get("session_token")
    
    if not session_token and authorization:
        if authorization.startswith("Bearer "):
            session_token = authorization.replace("Bearer ", "")
    
    if not session_token:
        return None
    
    session = await db.user_sessions.find_one({"session_token": session_token})
    if not session or datetime.fromisoformat(session['expires_at']) < datetime.now(timezone.utc):
        return None
    
    user_doc = await db.users.find_one({"id": session["user_id"]}, {"_id": 0})
    if not user_doc:
        return None
    
    # Convert ISO string timestamps back to datetime
    if isinstance(user_doc.get('created_at'), str):
        user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
    
    return User(**user_doc)

async def require_auth(user: Optional[User] = Depends(get_current_user)) -> User:
    """Require authentication"""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

async def require_organizer(user: User = Depends(require_auth)) -> User:
    """Require organizer or admin role"""
    if user.role not in ["organizer", "admin"]:
        raise HTTPException(status_code=403, detail="Organizer or admin role required")
    return user

async def require_admin(user: User = Depends(require_auth)) -> User:
    """Require admin role"""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return user

# ============ AUTH ROUTES ============

@api_router.post("/auth/session")
async def create_session(request: Request, response: Response):
    """Exchange session_id for session_token"""
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        raise HTTPException(status_code=400, detail="Missing session ID")
    
    # Call Emergent auth service
    try:
        auth_response = requests.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": session_id}
        )
        auth_response.raise_for_status()
        user_data = auth_response.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid session: {str(e)}")
    
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data["email"]}, {"_id": 0})
    
    if not existing_user:
        # Check if this is the first user (make them admin)
        user_count = await db.users.count_documents({})
        default_role = "admin" if user_count == 0 else "attendee"
        
        # Create new user
        user = User(
            email=user_data["email"],
            name=user_data["name"],
            picture=user_data.get("picture"),
            role=default_role
        )
        user_dict = user.model_dump()
        user_dict['created_at'] = user_dict['created_at'].isoformat()
        await db.users.insert_one(user_dict)
        user_id = user.id
        is_new_user = True
    else:
        user_id = existing_user["id"]
        is_new_user = False
    
    # Create session
    session_token = user_data["session_token"]
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    
    session = UserSession(
        user_id=user_id,
        session_token=session_token,
        expires_at=expires_at
    )
    
    session_dict = session.model_dump()
    session_dict['expires_at'] = session_dict['expires_at'].isoformat()
    session_dict['created_at'] = session_dict['created_at'].isoformat()
    
    await db.user_sessions.insert_one(session_dict)
    
    # Set cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=7*24*60*60
    )
    
    return {"success": True, "is_new_user": is_new_user}

@api_router.get("/auth/me")
async def get_me(user: User = Depends(require_auth)):
    """Get current user info"""
    return user

@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    """Logout user"""
    session_token = request.cookies.get("session_token")
    if session_token:
        await db.user_sessions.delete_one({"session_token": session_token})
    
    response.delete_cookie("session_token", path="/")
    return {"success": True}

@api_router.patch("/auth/select-role")
async def select_role(role_data: RoleUpdateRequest, user: User = Depends(require_auth)):
    """Allow user to select their role (attendee or organizer) during signup"""
    if role_data.role not in ["attendee", "organizer"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'attendee' or 'organizer'")
    
    # Don't allow changing from admin
    if user.role == "admin":
        raise HTTPException(status_code=403, detail="Cannot change admin role")
    
    # Update user role
    await db.users.update_one(
        {"id": user.id},
        {"$set": {"role": role_data.role}}
    )
    
    return {"success": True, "role": role_data.role}

# ============ CATEGORY ROUTES ============

@api_router.get("/categories", response_model=List[Category])
async def get_categories():
    """Get all categories"""
    categories = await db.categories.find({}, {"_id": 0}).to_list(1000)
    return categories

# Initialize default categories if empty
@app.on_event("startup")
async def init_categories():
    count = await db.categories.count_documents({})
    if count == 0:
        default_categories = [
            Category(name="Conference"),
            Category(name="Workshop"),
            Category(name="Concert"),
            Category(name="Sports"),
            Category(name="Exhibition"),
            Category(name="Networking"),
            Category(name="Festival"),
            Category(name="Other")
        ]
        for cat in default_categories:
            await db.categories.insert_one(cat.model_dump())

# ============ EVENT ROUTES ============

@api_router.post("/events", response_model=Event)
async def create_event(event_data: EventCreate, user: User = Depends(require_organizer)):
    """Create a new event (requires organizer or admin role)"""
    event = Event(
        creator_id=user.id,
        **event_data.model_dump()
    )
    
    event_dict = event.model_dump()
    event_dict['created_at'] = event_dict['created_at'].isoformat()
    await db.events.insert_one(event_dict)
    
    return event

@api_router.get("/events", response_model=List[EventWithCreator])
async def get_events(category: Optional[str] = None, search: Optional[str] = None):
    """Get all events with filters"""
    query = {"status": "active"}
    if category:
        query["category"] = category
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}}
        ]
    
    events = await db.events.find(query, {"_id": 0}).to_list(1000)
    
    # Add creator info
    events_with_creator = []
    for event in events:
        creator = await db.users.find_one({"id": event["creator_id"]}, {"_id": 0})
        if creator:
            event["creator_name"] = creator["name"]
            event["creator_email"] = creator["email"]
            events_with_creator.append(EventWithCreator(**event))
    
    return events_with_creator

@api_router.get("/events/{event_id}", response_model=EventWithCreator)
async def get_event(event_id: str):
    """Get single event"""
    event = await db.events.find_one({"id": event_id}, {"_id": 0})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    creator = await db.users.find_one({"id": event["creator_id"]}, {"_id": 0})
    if creator:
        event["creator_name"] = creator["name"]
        event["creator_email"] = creator["email"]
    
    return EventWithCreator(**event)

@api_router.put("/events/{event_id}", response_model=Event)
async def update_event(event_id: str, update_data: EventUpdate, user: User = Depends(require_auth)):
    """Update event (owner only)"""
    event = await db.events.find_one({"id": event_id}, {"_id": 0})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if event["creator_id"] != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    if update_dict:
        await db.events.update_one({"id": event_id}, {"$set": update_dict})
    
    updated_event = await db.events.find_one({"id": event_id}, {"_id": 0})
    return Event(**updated_event)

@api_router.delete("/events/{event_id}")
async def delete_event(event_id: str, user: User = Depends(require_auth)):
    """Delete event (owner only)"""
    event = await db.events.find_one({"id": event_id}, {"_id": 0})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if event["creator_id"] != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await db.events.update_one({"id": event_id}, {"$set": {"status": "cancelled"}})
    return {"success": True}

@api_router.get("/events/my-events/list", response_model=List[Event])
async def get_my_events(user: User = Depends(require_auth)):
    """Get user's created events"""
    events = await db.events.find({"creator_id": user.id}, {"_id": 0}).to_list(1000)
    return [Event(**e) for e in events]

# ============ TICKET TYPE ROUTES ============

@api_router.post("/events/{event_id}/ticket-types", response_model=TicketType)
async def create_ticket_type(event_id: str, ticket_data: TicketTypeCreate, user: User = Depends(require_auth)):
    """Add ticket type to event"""
    event = await db.events.find_one({"id": event_id}, {"_id": 0})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if event["creator_id"] != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    ticket_type = TicketType(
        event_id=event_id,
        **ticket_data.model_dump()
    )
    
    await db.ticket_types.insert_one(ticket_type.model_dump())
    return ticket_type

@api_router.get("/events/{event_id}/ticket-types", response_model=List[TicketType])
async def get_ticket_types(event_id: str):
    """Get ticket types for an event"""
    ticket_types = await db.ticket_types.find({"event_id": event_id}, {"_id": 0}).to_list(1000)
    return [TicketType(**t) for t in ticket_types]

# ============ BOOKING ROUTES ============

@api_router.post("/bookings", response_model=Dict[str, Any])
async def create_booking(booking_data: BookingCreate, user: User = Depends(require_auth)):
    """Create a booking"""
    # Validate event exists
    event = await db.events.find_one({"id": booking_data.event_id}, {"_id": 0})
    if not event or event["status"] != "active":
        raise HTTPException(status_code=404, detail="Event not found or inactive")
    
    # Validate ticket type
    ticket_type = await db.ticket_types.find_one({"id": booking_data.ticket_type_id}, {"_id": 0})
    if not ticket_type or ticket_type["event_id"] != booking_data.event_id:
        raise HTTPException(status_code=404, detail="Ticket type not found")
    
    # Check availability
    available = ticket_type["quantity_available"] - ticket_type["quantity_sold"]
    if available < booking_data.quantity:
        raise HTTPException(status_code=400, detail="Not enough tickets available")
    
    total_price = ticket_type["price"] * booking_data.quantity
    
    # Create booking
    booking = Booking(
        user_id=user.id,
        event_id=booking_data.event_id,
        ticket_type_id=booking_data.ticket_type_id,
        quantity=booking_data.quantity,
        total_price=total_price,
        status="pending" if total_price > 0 else "confirmed",
        qr_code_data=str(uuid.uuid4()) if total_price == 0 else None
    )
    
    booking_dict = booking.model_dump()
    booking_dict['created_at'] = booking_dict['created_at'].isoformat()
    await db.bookings.insert_one(booking_dict)
    
    # Update ticket sold count for free tickets
    if total_price == 0:
        await db.ticket_types.update_one(
            {"id": booking_data.ticket_type_id},
            {"$inc": {"quantity_sold": booking_data.quantity}}
        )
    
    return {"booking": booking, "requires_payment": total_price > 0}

@api_router.post("/bookings/checkout")
async def create_checkout_session(checkout_req: CheckoutRequest, request: Request, user: User = Depends(require_auth)):
    """Create Stripe checkout session for booking payment"""
    booking = await db.bookings.find_one({"id": checkout_req.booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if booking["status"] != "pending":
        raise HTTPException(status_code=400, detail="Booking already processed")
    
    # Initialize Stripe
    host_url = checkout_req.origin_url
    webhook_url = f"{host_url}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)
    
    # Create checkout session
    success_url = f"{host_url}/booking-success?session_id={{{{CHECKOUT_SESSION_ID}}}}"
    cancel_url = f"{host_url}/events"
    
    checkout_request = CheckoutSessionRequest(
        amount=booking["total_price"],
        currency="usd",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"booking_id": booking["id"], "user_id": user.id}
    )
    
    session: CheckoutSessionResponse = await stripe_checkout.create_checkout_session(checkout_request)
    
    # Create payment transaction
    transaction = PaymentTransaction(
        session_id=session.session_id,
        booking_id=booking["id"],
        user_id=user.id,
        amount=booking["total_price"],
        metadata=checkout_request.metadata
    )
    
    transaction_dict = transaction.model_dump()
    transaction_dict['created_at'] = transaction_dict['created_at'].isoformat()
    transaction_dict['updated_at'] = transaction_dict['updated_at'].isoformat()
    await db.payment_transactions.insert_one(transaction_dict)
    
    # Update booking with payment intent
    await db.bookings.update_one(
        {"id": booking["id"]},
        {"$set": {"payment_intent_id": session.session_id}}
    )
    
    return {"url": session.url, "session_id": session.session_id}

@api_router.get("/bookings/payment-status/{session_id}")
async def check_payment_status(session_id: str, user: User = Depends(require_auth)):
    """Check payment status and update booking"""
    # Get transaction
    transaction = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Check if already processed
    if transaction["payment_status"] == "paid":
        return {"status": "completed", "payment_status": "paid"}
    
    # Initialize Stripe and check status
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url="")
    checkout_status: CheckoutStatusResponse = await stripe_checkout.get_checkout_status(session_id)
    
    # Update transaction
    await db.payment_transactions.update_one(
        {"session_id": session_id},
        {"$set": {
            "payment_status": checkout_status.payment_status,
            "status": checkout_status.status,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # If payment successful, update booking
    if checkout_status.payment_status == "paid":
        booking_id = transaction["booking_id"]
        booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
        
        if booking and booking["status"] == "pending":
            # Generate QR code data
            qr_code_data = str(uuid.uuid4())
            
            await db.bookings.update_one(
                {"id": booking_id},
                {"$set": {
                    "status": "confirmed",
                    "qr_code_data": qr_code_data
                }}
            )
            
            # Update ticket sold count
            await db.ticket_types.update_one(
                {"id": booking["ticket_type_id"]},
                {"$inc": {"quantity_sold": booking["quantity"]}}
            )
    
    return {
        "status": checkout_status.status,
        "payment_status": checkout_status.payment_status,
        "amount_total": checkout_status.amount_total,
        "currency": checkout_status.currency
    }

@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks"""
    body = await request.body()
    signature = request.headers.get("Stripe-Signature")
    
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url="")
    
    try:
        webhook_response = await stripe_checkout.handle_webhook(body, signature)
        
        # Update transaction based on webhook
        if webhook_response.event_type == "checkout.session.completed":
            await db.payment_transactions.update_one(
                {"session_id": webhook_response.session_id},
                {"$set": {
                    "payment_status": webhook_response.payment_status,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }}
            )
        
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@api_router.get("/bookings/my-bookings/list", response_model=List[BookingWithDetails])
async def get_my_bookings(user: User = Depends(require_auth)):
    """Get user's bookings"""
    bookings = await db.bookings.find({"user_id": user.id}, {"_id": 0}).to_list(1000)
    
    bookings_with_details = []
    for booking in bookings:
        event = await db.events.find_one({"id": booking["event_id"]}, {"_id": 0})
        ticket_type = await db.ticket_types.find_one({"id": booking["ticket_type_id"]}, {"_id": 0})
        
        if event and ticket_type:
            booking["event_title"] = event["title"]
            booking["event_date"] = event["date"]
            booking["event_location"] = event["location"]
            booking["ticket_type_name"] = ticket_type["name"]
            
            if isinstance(booking.get('created_at'), str):
                booking['created_at'] = datetime.fromisoformat(booking['created_at'])
            
            bookings_with_details.append(BookingWithDetails(**booking))
    
    return bookings_with_details

@api_router.get("/bookings/{booking_id}/qr")
async def get_booking_qr(booking_id: str, user: User = Depends(require_auth)):
    """Get QR code for booking"""
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if booking["status"] != "confirmed" or not booking.get("qr_code_data"):
        raise HTTPException(status_code=400, detail="Booking not confirmed or QR code not available")
    
    # Generate QR code image
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(booking["qr_code_data"])
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to bytes
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    
    return StreamingResponse(buf, media_type="image/png")

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()