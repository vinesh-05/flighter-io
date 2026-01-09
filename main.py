from fastapi import FastAPI
from database import engine, Base
from services.redis_client import close_redis
from routers import users
from routers import chat
from routers import flights
from fastapi.openapi.utils import get_openapi
from routers import ticket_listing
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or set specific origins like ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown():
    await close_redis()


# Include routers
app.include_router(users.router)
app.include_router(chat.router)
app.include_router(flights.router)
app.include_router(ticket_listing.router)
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
