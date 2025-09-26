# Use an official Python runtime as a parent image
FROM python:3.9

# Set the working directory in the container
WORKDIR /app

# Install system dependencies for pymupdf
RUN apt-get update && apt-get install -y libmupdf-dev && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN useradd -m -u 1000 streamlit

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code
COPY . .

# Change ownership of the app directory
RUN chown -R streamlit:streamlit /app

# Switch to the non-root user
USER streamlit

# Make port 7860 available to the world outside this container
EXPOSE 7860

# Define environment variables
ENV STREAMLIT_SERVER_PORT 7860
ENV STREAMLIT_SERVER_ADDRESS 0.0.0.0

# Run app.py when the container launches
CMD ["streamlit", "run", "app.py"]