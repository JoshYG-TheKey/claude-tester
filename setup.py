from setuptools import setup, find_packages

setup(
    name="sarah-streamlit",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "streamlit>=1.32.0",
        "pandas>=2.2.0",
        "numpy>=1.26.3",
        "google-cloud-aiplatform>=1.45.0",
        "anthropic>=0.45.2",
        "python-dotenv>=1.0.1",
        "supabase>=2.13.0",
    ],
    python_requires=">=3.12",
) 