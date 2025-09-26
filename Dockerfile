# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies for pymupdf
RUN apt-get update && apt-get install -y libmupdf-dev && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container at /app
COPY . .

# Make port 8501 available to the world outside this container
EXPOSE 7860

# Define environment variable
ENV STREAMLIT_SERVER_PORT 7860
ENV STREAMLIT_SERVER_ADDRESS 0.0.0.0
ENV STREAMLIT_BROWSER_GATHERUSAGSTATS false

# Run app.py when the container launches
CMD ["streamlit", "run", "app.py"]