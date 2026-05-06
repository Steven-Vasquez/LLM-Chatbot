import dotenv
import os

dotenv.load_dotenv()


#################################################################
# Ollama LLM Configuration
####################################################################
# Set up Ollama for local LLM
from vanna.integrations.ollama import OllamaLlmService

llm = OllamaLlmService(
    model=os.getenv("very_smart_model", "qwen3:30b"),
    host=os.getenv("llm_server_url")
)


#####################################################################
# Custom Tool Configuration with Managed Disk File System
# - MSQL Runner Tool
# - Visualization Tool
#####################################################################
# Import MSSQL tool
from vanna.tools import RunSqlTool
from vanna.integrations.mssql import MSSQLRunner
from pathlib import Path
from managed_disk_file_system import ManagedDiskFileSystem
from sqlalchemy import event

# Set up managed disk file system (for managing saved queries and results on disk)
BASE_DIR = Path(__file__).resolve().parent
fs = ManagedDiskFileSystem(BASE_DIR)

# 1) Create ONE runner instance
runner = MSSQLRunner(
    odbc_conn_str="Driver={" + os.getenv("db_driver", "ODBC Driver 18 for SQL Server") + "};"
                  "Server=" + os.getenv("db_server") + ";"
                  "Database=" + os.getenv("db_name", "my_db") + ";"
                  "UID=" + os.getenv("db_user", "readonly_user") + ";"
                  "PWD=" + os.getenv("db_password", "password") + ";"
                  "TrustServerCertificate=yes;"
                  "Encrypt=no;"
)

# 2) Attach the SQL guard to the engine used by pandas/SQLAlchemy
@event.listens_for(runner.engine, "before_cursor_execute")
def guard_sql(conn, cursor, statement, parameters, context, executemany):
    
    #########################################
    # !!! Once SQL use cases are known, set proper guardrails using https://chatgpt.com/c/698ce745-f934-8332-9e02-a0cc2c9d1606
    #########################################
    s = statement.lower()

    # Intercepting `df = pd.read_sql_query(self.sa.text(args.sql), conn)` call at mssql.sql_runner level, which is used by the RunSqlTool to execute SQL queries and return results as DataFrames. This allows us to inspect and modify the raw SQL before it hits the database, giving us a chance to block dangerous queries or add limits to prevent memory issues with pandas.
    print("\n[SQL intercepted at engine level]:")
    print(statement)

    # Block dangerous full-table ACES scans
    if "tbl_aces" in s and "where" not in s:
        raise Exception("Blocked unsafe query: tbl_aces requires filters @ engine")

    # Prevent pandas memory explosion from SELECT *
    if s.strip().startswith("select") and "top" not in s:
        limited = f"SELECT TOP 1000 * FROM ({statement}) AS limited"
        context.statement = limited
        print("\n[SQL modified with TOP 1000 to prevent memory issues]:")
        print(limited)

# 3) Use THIS SAME runner everywhere
run_sql_tool = RunSqlTool(
    sql_runner=runner,
    file_system=fs
)

from vanna.tools import VisualizeDataTool
visualize_data_tool = VisualizeDataTool(
    file_system=fs
)
################################################################
# Agent Memory Configuration
#################################################################
# Import agent memory tools
from vanna.tools.agent_memory import SaveQuestionToolArgsTool, SearchSavedCorrectToolUsesTool, SaveTextMemoryTool
from vanna.integrations.chromadb import ChromaAgentMemory
from vanna.core.registry import ToolRegistry

# Set up ChromaDB for persistent agent memory
agent_memory = ChromaAgentMemory(
    collection_name="vanna_memory",
    persist_directory="../../../chroma_db"
)


#####################################################################
# User Authentication Configuration
#####################################################################
# Import user authentication classes
from vanna.core.user import UserResolver, User, RequestContext

# Create a simple user resolver
class SimpleUserResolver(UserResolver):
    async def resolve_user(self, request_context: RequestContext) -> User:
        user_email = request_context.get_cookie('vanna_email') or 'guest@example.com'
        group = 'admin' if user_email == 'admin@example.com' else 'user'
        return User(id=user_email, email=user_email, group_memberships=[group])

# Initialize the user resolver
user_resolver = SimpleUserResolver()


#####################################################################
# Agent and Tool Setup
#####################################################################
# Import base classes
from vanna import Agent
from vanna.core.registry import ToolRegistry
from vanna.core.agent.config import AgentConfig
from semantic_schema_enhancer import SemanticSchemaEnhancer


# Register tools
tools = ToolRegistry()
tools.register_local_tool(run_sql_tool, access_groups=['admin', 'user'])
#tools.register_local_tool(visualize_data_tool, access_groups=['admin', 'user'])
#tools.register_local_tool(SaveQuestionToolArgsTool(), access_groups=['admin'])
#tools.register_local_tool(SearchSavedCorrectToolUsesTool(), access_groups=['admin', 'user'])

# Set max tool iteration limit
config = AgentConfig(
    max_tool_iterations=25  # default is 10
)

# Create the agent
agent = Agent(
    llm_service=llm,
    tool_registry=tools,
    user_resolver=user_resolver,
    agent_memory=agent_memory,
    llm_context_enhancer=SemanticSchemaEnhancer(sql_runner=run_sql_tool.sql_runner), # Testing the SchemaEnhancer which adds schema information to the prompt, to see if it helps with SQL generation and if it can pull schema info from our custom MSSQLRunner that includes column descriptions. We can switch to the SqlMemoryAwarePromptBuilder later if we want to test the agent's use of memory for schema info instead of the enhancer.
    config=config
)


######################################################################
# Server Setup and Run
######################################################################

# Run the server with FastAPI for custom endpoints https://vanna.ai/docs/placeholder/deployment/fastapi
from fastapi import FastAPI
from pydantic import BaseModel
from vanna import Agent
from vanna.servers.base import ChatHandler, ChatRequest
from vanna.servers.fastapi.routes import register_chat_routes

# --- 1. Create your FastAPI app ---
app = FastAPI(title="Custom Vanna Server")


# --- 2. Register Vanna chat endpoints if you still want them ---
chat_handler = ChatHandler(agent)
register_chat_routes(app, chat_handler, config={
    "dev_mode": False,
    "cdn_url": "https://img.vanna.ai/vanna-components.js"
})

# --- 3. Add your custom endpoint that calls the agent directly ---
class QueryRequest(BaseModel):
    message: str


chat_handler = ChatHandler(agent)

@app.post("/custom_agent_query")
async def custom_agent_query(req: QueryRequest):
    try:
        # Before query: clear old finished files
        fs.cleanup_finished()

        chat_request = ChatRequest(
            message=req.message,
            user="anonymous",
            conversation_id=None
        )

        result = await chat_handler.handle_poll(chat_request)

        # After query: move WIP -> finished
        fs.finalize_request()
        
        return result  # already clean JSON
    except Exception as e:
        return {"error": str(e)}
    
# --- 4. Run the server ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)