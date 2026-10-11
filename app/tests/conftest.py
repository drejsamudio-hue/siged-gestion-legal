import os
import sys
import tempfile
from pathlib import Path

os.environ["ORGANIZADOR_CONFIG"] = os.path.join(tempfile.mkdtemp(prefix="cfg_tests_"), "config.json")
os.environ.pop("ORGANIZADOR_BASE", None)
os.environ.pop("ORGANIZADOR_APELLIDOS", None)
os.environ["ORGANIZADOR_CORPUS"] = tempfile.mkdtemp(prefix="corpus_tests_")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
