import os

# Set test-mode flag globally for all tests to bypass slow operations or remote downloads
os.environ["ARTHA_TESTING"] = "true"
