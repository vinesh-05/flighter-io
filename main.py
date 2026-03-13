from fastapi import FastAPI
from database import engine, Base
from routers import users
from routers import chat
from routers import flights
from routers import details_upload
from fastapi.openapi.utils import get_openapi
from routers import ticket_listing
from routers import bookings
from routers import payments
from routers import forgot_password
from routers import reset_password
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or set specific origins like ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# Include routers
app.include_router(users.router)
app.include_router(bookings.router)
app.include_router(chat.router)
app.include_router(details_upload.router)
app.include_router(flights.router)
app.include_router(ticket_listing.router)
app.include_router(payments.router)
app.include_router(forgot_password.router)
app.include_router(reset_password.router)
# Create tables
Base.metadata.create_all(bind=engine)

@app.get("/")
def root():
    return {"message": "Flight Booking AI Bot is running!"}


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Flight Booking AI",
        version="1.0.0",
        description="API for chatting with Gemini AI and booking flights",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    for path in openapi_schema["paths"].values():
        for method in path.values():
            method["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
