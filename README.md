# Sarah Streamlit

A modern Streamlit chat application with Claude integration via Vertex AI and Supabase.

## Features

- Chat interface with Claude 3.5 integration
- Question and prompt testing capabilities
- Source document management
- Response evaluation and comparison
- Data persistence with Supabase

## Local Development

1. Install dependencies using Poetry:
```bash
poetry install
```

2. Set up environment variables:
   - Copy `.env.example` to `.env`:
     ```bash
     cp .env.example .env
     ```
   - Edit `.env` and add your API keys:
     ```
     ANTHROPIC_API_KEY=your_api_key_here
     SUPABASE_URL=your_supabase_url_here
     SUPABASE_KEY=your_supabase_key_here
     ```

3. Run the application:
```bash
poetry run streamlit run app.py
```

## Streamlit Cloud Deployment

1. Fork this repository
2. Add the following secrets in your Streamlit Cloud dashboard:
   - `ANTHROPIC_API_KEY`: Your Anthropic API key
   - `SUPABASE_URL`: Your Supabase project URL
   - `SUPABASE_KEY`: Your Supabase anon/public key
3. Deploy using `app.py` as the main entry point

## Project Structure

```
.
├── .streamlit/              # Streamlit configuration
│   └── config.toml
├── src/
│   └── sarah_streamlit/     # Main application code
│       ├── app.py          # Main chat application
│       ├── testing_app.py  # Testing interface
│       ├── chat.py        # Chat functionality
│       └── db.py          # Database operations
├── app.py                  # Entry point
├── requirements.txt        # Dependencies for Streamlit Cloud
├── pyproject.toml         # Poetry configuration
├── .env.example           # Example environment variables
└── README.md
```

## Environment Variables

The following environment variables are required:

- `ANTHROPIC_API_KEY`: Your Anthropic API key for Claude access
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Your Supabase anon/public key

For local development, copy `.env.example` to `.env` and fill in your values. For Streamlit Cloud deployment, add these as secrets in your app settings.

## Database Setup

1. Create a new project in Supabase
2. Run the following SQL to set up the required tables:

```sql
create table questions (
  id bigint primary key generated always as identity,
  name text not null,
  content text not null,
  created_at timestamp with time zone default timezone('utc'::text, now())
);

create table sources (
  id bigint primary key generated always as identity,
  question_id bigint references questions(id),
  title text not null,
  content text not null,
  created_at timestamp with time zone default timezone('utc'::text, now())
);

create table prompts (
  id bigint primary key generated always as identity,
  name text not null,
  content text not null,
  version integer not null,
  created_at timestamp with time zone default timezone('utc'::text, now())
);

create table test_runs (
  id bigint primary key generated always as identity,
  prompt_id bigint references prompts(id),
  name text not null,
  description text,
  model text not null,
  created_at timestamp with time zone default timezone('utc'::text, now())
);

create table run_results (
  id bigint primary key generated always as identity,
  run_id bigint references test_runs(id),
  question_id bigint references questions(id),
  response text not null,
  created_at timestamp with time zone default timezone('utc'::text, now())
);
```

## Security Note

This repository is public. Make sure to:
- Never commit your `.env` file
- Never share your API keys
- Use environment variables for all sensitive data
- Always use the `.gitignore` file to exclude sensitive information

## License

MIT