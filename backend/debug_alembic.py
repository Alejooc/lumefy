import traceback
import sys
from alembic.config import Config
from alembic import command

alembic_cfg = Config("alembic.ini")
try:
    command.upgrade(alembic_cfg, "head")
except Exception as e:
    print(getattr(e, 'orig', str(e)))
