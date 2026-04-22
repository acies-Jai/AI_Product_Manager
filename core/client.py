from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

ROOT = Path(__file__).parent.parent
INPUTS_DIR = ROOT / "inputs"
OUTPUTS_DIR = ROOT / "outputs"
MODEL = "llama-3.3-70b-versatile"

client = Groq()
