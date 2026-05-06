from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# Import FastAPI routers (to be refactored in route files)
from routes.ollamaRoutes import router as ollama_router
from routes.chromadbRoutes import router as chromadb_router
from routes.chat_routes import router as chat_router

from routes.websocket_routes import router as websocket_router

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(ollama_router)
app.include_router(chromadb_router)
app.include_router(chat_router)
app.include_router(websocket_router)

# To run: uvicorn server:app --reload

#write main
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)