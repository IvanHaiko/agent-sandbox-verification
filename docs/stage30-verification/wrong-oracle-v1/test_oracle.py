import sys
sys.path.insert(0,"src")
from helper import clamp
assert clamp(5,0,3)==5
