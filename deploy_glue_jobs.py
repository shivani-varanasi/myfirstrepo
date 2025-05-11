import os
import boto3
import sys

# Check if the current branch is 'main' (this can be passed from environment variables or GitHub commit hooks)
branch = os.getenv('CODEBUILD_SOURCE_VERSION', 'main')  # Can also fetch the branch dynamically if needed

if 'main' not in branch:
    print("Error: Deployment can only be triggered from the 'main' branch.")
    sys.exit(1)  # Exit if not on the main branch

# If 'main' branch, proceed with deployment
s3_client = boto3.client('s3')
glue_client = boto3.client('glue')

# Define S3 Bucket and Glue job details
s3_bucket = 'your-glue-scripts-bucket'
glue_jobs = [
    {
        'name': 'job1',
        'script_path': 'job1/script.py',
        'role': 'your-glue-role',
        'job_config': 'job1/job_config.py'  # Optional: use if you have specific job configurations
    },
    {
        'name': 'job2',
        'script_path': 'job2/script.py',
        'role': 'your-glue-role',
        'job_config': 'job2/job_config.py'  # Optional: use if you have specific job configurations
    }
]

def upload_to_s3(local_file, s3_path):
    """Upload the local file to S3."""
    try:
        s3_client.upload_file(local_file, s3_bucket, s3_path)
        print(f"Successfully uploaded {local_file} to {s3_path}")
    except Exception as e:
        print(f"Error uploading {local_file} to {s3_path}: {e}")

def create_or_update_glue_job(job_details):
    """Create or update the Glue job."""
    job_name = job_details['name']
    script_path = job_details['script_path']
    job_config = job_details.get('job_config')
    
    s3_script_path = f"scripts/{job_name}/{os.path.basename(script_path)}"
    upload_to_s3(script_path, s3_script_path)

    # If there's a job config, upload it as well
    if job_config:
        s3_config_path = f"scripts/{job_name}/{os.path.basename(job_config)}"
        upload_to_s3(job_config, s3_config_path)
    
    # Define Glue job parameters
    glue_job_params = {
        'Name': job_name,
        'Role': job_details['role'],
        'Command': {
            'Name': 'glueetl',
            'ScriptLocation': f"s3://{s3_bucket}/{s3_script_path}"
        },
        'MaxCapacity': 2  # Adjust as needed
    }

    # If you have a job config, add it here (optional)
    if job_config:
        glue_job_params['DefaultArguments'] = {
            '--job-config': f"s3://{s3_bucket}/{s3_config_path}"
        }

    # Try to create the Glue job or update it if it already exists
    try:
        glue_client.create_job(**glue_job_params)
        print(f"Successfully created Glue job: {job_name}")
    except glue_client.exceptions.AlreadyExistsException:
        glue_client.update_job(JobName=job_name, JobUpdate=glue_job_params)
        print(f"Successfully updated Glue job: {job_name}")

def deploy_glue_jobs():
    """Deploy all Glue jobs."""
    for job in glue_jobs:
        create_or_update_glue_job(job)

if __name__ == "__main__":
    deploy_glue_jobs()
