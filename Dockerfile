# Use an official Python runtime as a parent image
FROM python:3.10-slim-bookworm

# Set the working directory in the container
WORKDIR /app

# Install system dependencies for the forensic tools
RUN apt-get update && apt-get install -y \
    steghide \
    binwalk \
    file \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Make port 8501 available to the world outside this container
EXPOSE 8501

# Define environment variable for Streamlit
ENV STREAMLIT_SERVER_PORT 8501
ENV STREAMLIT_SERVER_ADDRESS 0.0.0.0

# Run app.py when the container launches
CMD ["streamlit", "run", "app.py"]