import subprocess
import sys
from pathlib import Path

# Paths
project_dir = Path(__file__).parent
vanna_path = project_dir  / "llm_agent" / "agent_tools" / "vanna_txt2sql" / "vanna_server.py"
chatbot_path = project_dir / "server.py"

# Launch chatbot server
chatbot_process = subprocess.Popen([sys.executable, str(chatbot_path)], 
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# Launch Vanna server (from subdirectory)
vanna_process = subprocess.Popen([sys.executable, str(vanna_path)])

print("Both servers started! Chatbot:5000, Vanna:8000")

try:
    chatbot_process.wait()
    vanna_process.wait()
except KeyboardInterrupt:
    print("Shutting down servers...")
    chatbot_process.terminate()
    vanna_process.terminate()
