# Import all models to avoid circular import issues
from .diseases import Disease
from .skintype import SkinType  
from .symptom import Symptom
from .user import User
from .diagnosis import Diagnosis

# Ensure all models are available
__all__ = [
    "Disease",
    "SkinType", 
    "Symptom",
    "User",
    "Diagnosis"
]
