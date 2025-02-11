# Claude Testing Streamlit Application

A Streamlit application for testing and evaluating Claude AI responses. This application allows you to:
- Create and manage test questions with source materials
- Run tests with different prompts and parameters
- Compare and evaluate responses
- Maintain a persistent database of results

## Features

- 📝 Question Management
  - Add questions with multiple source documents
  - Organize sources into pages
  - View and manage existing questions

- 🤖 Prompt Testing
  - Test different prompt versions
  - Configure Claude parameters (temperature, top_p, top_k)
  - Run batch tests across multiple questions

- 📊 Results Analysis
  - Compare responses from different runs
  - Export results to CSV
  - Track performance metrics

- 💾 Data Persistence
  - SQLite database with Cloud Storage sync
  - Automatic backup and restore
  - Multi-instance safe

## Deployment

The application is configured to run on Google Cloud Run in the London region (europe-west2).

### Quick Deploy

```bash
# Make the deployment script executable
chmod +x deploy.sh

# Deploy the application
./deploy.sh
```

The deployment script will:
1. Set up a Cloud Storage bucket for database persistence
2. Build and push the Docker container
3. Deploy to Cloud Run with appropriate scaling settings
4. Configure all necessary IAM permissions

### Configuration

Default settings:
- Region: London (europe-west2)
- Memory: 2GB
- CPU: 2 cores
- Min instances: 1 (prevents cold starts)
- Max instances: 10 (for scaling)
- Timeout: 3600 seconds (1 hour)

## Local Development

1. Install dependencies:
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install poetry
poetry install
```

2. Run the application:
```bash
poetry run streamlit run src/sarah_streamlit/testing_app.py
```

## Project Structure

```
sarah-streamlit/
├── src/
│   └── sarah_streamlit/
│       ├── testing_app.py    # Main Streamlit application
│       ├── db.py            # Database operations
│       └── cloud_storage.py # Cloud Storage integration
├── deploy.sh               # Deployment script
├── Dockerfile             # Container configuration
├── pyproject.toml        # Poetry dependencies
└── README.md            # This file
```

## Environment Variables

- `BUCKET_NAME`: Cloud Storage bucket for database persistence
- `DB_PATH`: Local path for SQLite database
- `CLOUD_RUN_SERVICE`: Set to "true" when running in Cloud Run

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

[Add your license information here]