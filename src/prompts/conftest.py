import sys
from pathlib import Path

# Force Python to see 'src' on module searches
sys.path.insert(0, str(Path(__file__).parent))