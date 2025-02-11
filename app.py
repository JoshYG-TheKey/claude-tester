"""
Sarah Streamlit - A modern Streamlit chat application with Claude integration.
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import and run the main app
from sarah_streamlit.app import main

if __name__ == "__main__":
    main() 