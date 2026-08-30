import hashlib
from typing import Dict, Optional

class AuthManager:
    """
    Role-based access control and user authentication manager.
    Protects clinical encounter entry and central database access.
    """

    USERS: Dict[str, Dict[str, str]] = {
        "dr_smith": {
            "name": "Dr. Sarah Smith, MD",
            "role": "Attending Physician",
            "password_hash": hashlib.sha256("doctor123".encode()).hexdigest(),
            "department": "Cardiology"
        },
        "nurse_amina": {
            "name": "Nurse Amina Bello, RN",
            "role": "Triage Nurse",
            "password_hash": hashlib.sha256("nurse123".encode()).hexdigest(),
            "department": "Emergency Triage"
        },
        "tech_onahi": {
            "name": "Onahi Emmanuel, Tech",
            "role": "Technician",
            "password_hash": hashlib.sha256("tech123".encode()).hexdigest(),
            "department": "Clinical Laboratory"
        },
        "admin_idsr": {
            "name": "Dr. Ibrahim Musa, Epidemiologist",
            "role": "Admin / Registry Specialist",
            "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
            "department": "WHO IDSR Central Registry"
        }
    }

    @staticmethod
    def authenticate(username: str, password: str) -> Optional[Dict[str, str]]:
        """Verifies username and password against secure hash."""
        username_clean = username.strip().lower()
        if username_clean in AuthManager.USERS:
            user_record = AuthManager.USERS[username_clean]
            pwd_hash = hashlib.sha256(password.strip().encode()).hexdigest()
            if pwd_hash == user_record["password_hash"]:
                return {
                    "username": username_clean,
                    "name": user_record["name"],
                    "role": user_record["role"],
                    "department": user_record["department"]
                }
        return None