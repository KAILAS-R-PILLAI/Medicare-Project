# 1. BASE IMAGE: Use a lightweight official Python image for smaller size
# Choose a specific Python version that matches your development environment
FROM tensorflow/tensorflow:2.18.0

# 2. ENVIRONMENT: Set unbuffered output for real-time logging in ECS
ENV PYTHONUNBUFFERED=1

# 3. WORKING DIRECTORY: Set the path inside the container
WORKDIR /usr/src/app

# 4. DEPENDENCIES: Install dependencies first to leverage Docker's build cache
# This layer is only rebuilt if requirements.txt changes.
COPY requirements.txt ./

# Dockerfile:16 - Added --ignore-installed to bypass distutils uninstall error
RUN pip install --no-cache-dir -r requirements.txt --ignore-installed

# 5. APPLICATION CODE: Copy all the source code (respecting .gitignore)
# The application files must be in the working directory
COPY . .

# 6. PORT: Expose the port Gunicorn will run on (ECS/Fargate will map this)
EXPOSE 8000

# 7. COMMAND: Run the application using a production WSGI server (Gunicorn)
# FIXED: Changed the target from 'medicare:login' to 'app:app' 
# (Module 'app' -> app.py; Callable 'app' -> the application instance name)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]