# Asynchronous Virtual Card-Sorting Research Platform

A modular web application built with Python 3.12 and Streamlit for designing, hosting, and analyzing virtual open, closed, hybrid, and proposed-organization card sorts.

## Setup Instructions

1. Install the project packages:

   ```bash
   pip install -r requirements.txt
   ```

2. Create your local settings file:

   ```bash
   cp env.example.txt .env
   ```

   For a publicly hosted app, edit `.env` and set `APP_BASE_URL` to its full address (for example, `https://your-app.example`). This makes the participant link on the Researcher page complete and ready to copy into an email.

3. Start the app:

   ```bash
   streamlit run app.py
   ```
