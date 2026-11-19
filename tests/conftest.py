import os
import shutil
from pathlib import Path
TEST_STORAGE=Path('/tmp/kkd-studio-pytest')
shutil.rmtree(TEST_STORAGE,ignore_errors=True)
os.environ['KKD_STORAGE']=str(TEST_STORAGE)
