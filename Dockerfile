# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Expose the port for Hugging Face Spaces
EXPOSE 7860

# Set the command to run the Streamlit application on the correct port
CMD ["streamlit", "run", "app.py", "--server.port=7860", "--server.address=0.0.0.0", "--browser.gatherUsageStats=false", "--server.enableXsrfProtection=false"]