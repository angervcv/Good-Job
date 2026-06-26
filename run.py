"""启动入口"""
import subprocess
import sys
from pathlib import Path
import config


def main():
    """启动 Streamlit 应用"""
    app_path = Path(__file__).parent / "app" / "main.py"
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        str(app_path),
        "--server.port", str(config.STREAMLIT_PORT),
    ]
    subprocess.run(cmd)


if __name__ == "__main__":
    main()