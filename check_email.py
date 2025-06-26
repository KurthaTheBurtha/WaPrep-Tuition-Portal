import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check the current value
default_from_email = os.getenv('DEFAULT_FROM_EMAIL')
print(f"Current DEFAULT_FROM_EMAIL: {default_from_email}") 