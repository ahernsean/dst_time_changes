# Use a base image
FROM python:3

# Set the working directory
WORKDIR /app

# Copy the application files to the container
COPY dst_time_changes /app/dst_time_changes

# Install any dependencies
RUN python -m pip install -r dst_time_changes/requirements.txt

# Set the container entrypoint
EXPOSE 8888
WORKDIR dst_time_changes
ENV FLASK_APP=app.py
ENTRYPOINT [ "python", "-m", "flask", "run", "--host=0.0.0.0", "--port=8888" ]