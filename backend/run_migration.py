import sys
import os
from alembic.config import Config
from alembic import command

def run_migration():
    # Set up the Alembic configuration
    alembic_cfg = Config("alembic.ini")
    
    # Run the upgrade command
    try:
        command.upgrade(alembic_cfg, "head")
        print("Migration successful!")
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    # Ensure run from backend dir
    if not os.path.exists("alembic.ini"):
        print("Error: alembic.ini not found. Run from backend directory.")
        sys.exit(1)
    run_migration()
