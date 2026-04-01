# Sample dubug files

import sys
import os

print("Debugging Python execution...")
print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")
print(f"Script location: {__file__}")

# Try to write to a file
with open("debug_output.txt", "w") as f:
    f.write("Python is working!\n")
    f.write(f"Python version: {sys.version}\n")

print("Debug file created: debug_output.txt")