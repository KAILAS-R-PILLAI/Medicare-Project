# Medicare App: CI/CD Pipeline with ECS Fargate, Slack Integration, and Grafana Monitoring

## Project Overview
This project automates the deployment of a Dockerized web application to AWS ECS Fargate using Jenkins. It includes IAM role setup, GitHub integration, Slack notifications, and Grafana-based monitoring via CloudWatch Container Insights.

---

## Workflow Summary

### 1. Terraform Infrastructure as Code Setup

To ensure consistent provisioning of AWS resources, Terraform was used to automate the creation of:

- Amazon ECR  
- ECS Fargate Cluster, Task Definition & Service  
- IAM Roles & Policies  
- CloudWatch Log Groups  
- Container Insights  

This enables a fully reproducible deployment environment.

---

#### File-wise Summary

- **main.tf**
  - Configures AWS provider  
  - Loads all infrastructure modules  
  - Defines the region (`ap-south-1`)  

- **ecr.tf**
  -Creates the ECR repository used by Jenkins to push application images:
  
    - `aws_ecr_repository`  

- **ecs.tf**
  - Creates all ECS resources:

    - ECS Cluster  
    - Fargate task definition  
    - ECS service with networking  
    - Security group for port 80 inbound  
    - Subnet attachments  

  - ECS is configured to pull images from ECR and run containers in Fargate.

- **iam.tf**
  -Defines the IAM roles required for:

    - ECS Task Execution Role  
    - ECS Task Role  
    - Jenkins ECR/ECS permissions  

  -Policies include:
    - `AmazonECS_FullAccess`  
    - `AmazonEC2ContainerRegistryFullAccess`  

- **cloudwatch.tf**
  - Enables observability:

    - Creates CloudWatch log group  
    - Attaches log configuration to ECS task  
    - Activates **Container Insights** for ECS cluster  

  - This allows Grafana to fetch ECS metrics later.

- **variables.tf**
  - Stores all environment-specific variables:
 
    - Repository name    
    - Subnets ID  
    - Security group IDs  

- **outputs.tf**
  - Exposes useful resource values such as:

    - ECR repository URL  
    - ECS cluster ARN  
    - ECS service name  
    - Task definition ARN  
    - CloudWatch log group  

  - These values are used by Jenkins during deployment.


#### 5.3 Terraform Deployment Steps

- **Initialize**
```
terraform init
```

- **Preview**
```
terraform plan
```

- **Apply**
```
terraform apply -auto-approve
```

This provisions the entire AWS environment.

<img width="1057" height="433" alt="Screenshot 2025-11-20 173722" src="https://github.com/user-attachments/assets/a4015f9a-c7bf-43b0-b878-fbea869535fb" />


---


### 2. AWS Infrastructure Setup
All AWS resources and permissions were provisioned to support secure, automated deployment and monitoring:

#### IAM Roles and Policies
Created and attached the following IAM roles to the Jenkins user:
- `AmazonEC2ContainerRegistryPowerUser`
- `AmazonEC2ContainerRegistryFullAccess`
- `IAMFullAccess`
- `AmazonECS_FullAccess`

These roles enabled Jenkins to interact with ECR, ECS, IAM, and other AWS services via CLI.

#### Security Group and Subnet Configuration
To allow public access to the deployed app:
- **Inbound Rule**:
  - Protocol: `TCP`
  - Port Range: `80`
  - Source: `0.0.0.0/0` (open to all IPs)
  - Used subnet for ECS networking


---

### 3. Dockerize the Web App
- Built a `Dockerfile` exposing port 80 for public access
- Used `gunicorn` to serve the Flask app:

```dockerfile

# Use the official TensorFlow image (version 2.18.0) as the base image
FROM tensorflow/tensorflow:2.18.0

# Ensure Python output is sent straight to the terminal (no buffering)
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /usr/src/app

# Copy the requirements file into the working directory
COPY requirements.txt ./

# Install Python dependencies listed in requirements.txt
# --no-cache-dir avoids caching to reduce image size
# --ignore-installed ensures fresh installs even if packages exist in base image
RUN pip install --no-cache-dir -r requirements.txt --ignore-installed

# Copy all remaining project files into the container
COPY . .

# Expose port 80 so the container can accept HTTP traffic
EXPOSE 80

# Start the Flask app using Gunicorn on port 80
CMD ["gunicorn", "--bind", "0.0.0.0:80", "app:app"]


```
---

### 4. Automated CI/CD Pipeline with Jenkins
Created a multi-stage Jenkins pipeline that automates the entire deployment process:

- Clones the GitHub repository
- Builds and tags the Docker image
- Pushes the image to Amazon ECR 
  <img width="1916" height="694" alt="Screenshot 2025-11-19 224438" src="https://github.com/user-attachments/assets/7ad03040-2464-49cf-acf6-b4d2e8a2d955" />
  <img width="1916" height="696" alt="Screenshot 2025-11-19 224503" src="https://github.com/user-attachments/assets/6b3ffb5e-a814-438c-b828-7628e4eaa67a" />

- Creates an ECS service with cotainer insights enabled and deploys the app to AWS Fargate
  <img width="1894" height="815" alt="Screenshot 2025-11-19 224536" src="https://github.com/user-attachments/assets/7b35103b-8900-4b64-833b-5c255acc4fcd" />
  <img width="1904" height="720" alt="Screenshot 2025-11-19 224553" src="https://github.com/user-attachments/assets/1a71943c-c8f6-4ed0-83d3-11e54303688c" />

- Cleans up local Docker images after deployment

All AWS CLI operations are executed using securely injected credentials via Jenkins.

To enable this:
- AWS access key and secret key were added to Jenkins using **Manage Jenkins → Credentials → Add Credentials**
- The credentials were stored as **AWS Credentials** with a unique ID (e.g., `aws-jenkins-user`)
- Inside the Jenkinsfile, the credentials were injected using the `withCredentials` block:
  ```groovy
  def withAwsCredentials(closure) {
    withCredentials([[
        $class: 'AmazonWebServicesCredentialsBinding',
        credentialsId: 'aws-jenkins-user',
        accessKeyVariable: 'AWS_ACCESS_KEY_ID',
        secretKeyVariable: 'AWS_SECRET_ACCESS_KEY'
    ]]) {
        closure()
    }
  }
  ```
 <img width="1876" height="756" alt="Screenshot 2025-11-19 225010" src="https://github.com/user-attachments/assets/9a95b410-dc01-44c8-9262-f0c550e407f7" />
 <img width="1916" height="696" alt="Screenshot 2025-11-19 224503" src="https://github.com/user-attachments/assets/f92744bd-f723-4a61-8647-4f4db5f8a292" />
 <img width="1916" height="696" alt="Screenshot 2025-11-19 224503" src="https://github.com/user-attachments/assets/9172365e-b0d1-46ce-b11d-af271708d5cd" />



---

### 5. Slack Integration

Slack notifications were integrated into the Jenkins pipeline to improve visibility and team collaboration. Build status alerts are automatically sent to a designated Slack channel upon success or failure.

#### Configuration Steps

- **Install Slack Plugin in Jenkins**
   - Navigate to **Manage Jenkins → Plugins**
   - Search for and install the **Slack Notification Plugin**
   - Restart Jenkins after installation

- **Configure Slack in Jenkins**
   - Go to **Manage Jenkins → Configure System**
   - Scroll to the **Slack** section
   - Fill in the following:
     - **Workspace**: your Slack workspace name
     - **Credential**: Slack token (generated via a Slack App with `chat:write` permission)
     - **Default Channel**: `#medicare-jenkins`
     - **Base URL**: `https://slack.com/api/`
   - Click **Test Connection** to verify integration

- **Add Slack Notification to Jenkinsfile**
   - Inside the `post` block of the pipeline, add:

     ```groovy
     post {
         success {
             slackSend(channel: '#medicare-jenkins', message: "✅ Build #${env.BUILD_NUMBER} succeeded for ${env.JOB_NAME}")
         }
         failure {
             slackSend(channel: '#medicare-jenkins', message: "❌ Build #${env.BUILD_NUMBER} failed for ${env.JOB_NAME}")
         }
         unstable {
             slackSend(channel: '#medicare-jenkins', message: "⚠️ Build #${env.BUILD_NUMBER} is unstable for ${env.JOB_NAME}")
         }
     }
     ```


   - Slack credentials are securely stored in Jenkins and injected at runtime. They are never exposed in the Jenkinsfile or logs.

   - Slack integration ensures that the team receives real-time updates on build outcomes, helping to quickly identify issues and maintain deployment velocity.
  <img width="1079" height="455" alt="Screenshot 2025-11-23 110647" src="https://github.com/user-attachments/assets/607dfa3d-8051-46fa-a6db-780a71935003" />

---

### 6. Grafana Monitoring

Grafana was integrated into the workflow to provide real-time observability of the ECS Fargate deployment using CloudWatch metrics. This setup enables proactive monitoring, alerting, and dashboard sharing for better operational visibility.

- Add CloudWatch as a Data Source in Grafana Cloud
   - In Grafana :
     - Go to **Connections → Add data source**
     - Select **Amazon CloudWatch**
     - Provide:
       - AWS region: `ap-south-1`
       - Authentication: Access & secret keys or IAM role (via AWS Cloud integration)
     - Click **Save & Test**
     - Create Dashboard Panels
     - A custom dashboard was created with the following panels:
       - **CPUUtilization**: Monitors CPU usage of ECS tasks
       - **MemoryUtilization**: Tracks memory consumption
       - **TaskCount**: Shows the number of running tasks
     - Metrics were queried from the namespace: `ECS/ContainerInsights`

---

## Technologies Used
- **Terraform** - for provisioning Infrastructure as Code
- **AWS ECS Fargate** – for container orchestration
- **Amazon ECR** – for Docker image storage
- **IAM Roles & Policies** – for secure AWS access
- **Jenkins** – for CI/CD automation
- **Docker** – for containerizing the application
- **Slack** – for build notifications
- **GitHub** – for source control and webhook triggers
- **Grafana Cloud** – for dashboarding and alerting
- **CloudWatch** – for metrics and logs








