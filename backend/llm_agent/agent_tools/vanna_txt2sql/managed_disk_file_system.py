
import os
from pathlib import Path
import shutil
from vanna.capabilities.file_system import FileSystem

class ManagedDiskFileSystem(FileSystem):
    def __init__(self, base_dir: Path):
        self.wip_dir = base_dir / "wip_queries"
        self.finished_dir = base_dir / "finished_queries"

        self.wip_dir.mkdir(exist_ok=True)
        self.finished_dir.mkdir(exist_ok=True)

    async def write_file(self, filename, content, *args, **kwargs):
        path = os.path.join(self.wip_dir, filename)
        with open(path, "w") as f:
            f.write(content)

    async def read_file(self, filename, *args, **kwargs):
        path = os.path.join(self.wip_dir, filename)
        if os.path.exists(path):
            with open(path) as f:
                return f.read()
        return None

    async def exists(self, filename, *args, **kwargs):
        return os.path.exists(os.path.join(self.wip_dir, filename))

    async def list_files(self, *args, **kwargs):
        return os.listdir(self.wip_dir)

    async def search_files(self, *args, **kwargs):
        return os.listdir(self.wip_dir)

    async def is_directory(self, *args, **kwargs):
        return False

    async def run_bash(self, *args, **kwargs):
        return ""

    # lifecycle helpers (not part of Vanna interface)
    def finalize_request(self):
        # Move all files from wip to finished
        for f in os.listdir(self.wip_dir):
            shutil.move(
                os.path.join(self.wip_dir, f),
                os.path.join(self.finished_dir, f)
            )

    def cleanup_finished(self):
        # Remove all files in finished directory
        for f in os.listdir(self.finished_dir):
            os.remove(os.path.join(self.finished_dir, f))