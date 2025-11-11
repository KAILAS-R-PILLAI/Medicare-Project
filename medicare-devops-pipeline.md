# Medicare App: CI/CD Pipeline with ECS Fargate, Slack Integration, and Grafana Monitoring

## Project Overview
This project automates the deployment of a Dockerized web application to AWS ECS Fargate using Jenkins. It includes IAM role setup, GitHub integration, Slack notifications, and Grafana-based monitoring via CloudWatch Container Insights.

---

## Workflow Summary

### 1. AWS Infrastructure Setup
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

### 2. Dockerize the Web App
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

### 3. Automated CI/CD Pipeline with Jenkins
Created a multi-stage Jenkins pipeline that automates the entire deployment process:

- Clones the GitHub repository
- Builds and tags the Docker image
- Pushes the image to Amazon ECR (automatically creates the repository if it doesn't exist)
- Registers a new ECS task definition with the latest image
- Creates an ECS cluster and enables CloudWatch Container Insights (if not already present)
- Creates an ECS service and deploys the app to AWS Fargate
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
 
---

### 4. Slack Integration

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

---

### 6. Grafana Monitoring

Grafana was integrated into the workflow to provide real-time observability of the ECS Fargate deployment using CloudWatch metrics. This setup enables proactive monitoring, alerting, and dashboard sharing for better operational visibility.

#### Monitoring Setup Steps

- **Step-1: Deploy Grafana via Grafana Cloud**
   - Signed up for a **Grafana Cloud** account at [grafana.com](https://grafana.com)
   - Created a new hosted Grafana instance
   - Logged into the Grafana Cloud dashboard and accessed the workspace
   - No local installation required — dashboards and data sources are managed via the cloud UI

- **Step-2: Enable CloudWatch Container Insights**
   - Container Insights was enabled for the ECS cluster via Jenkins using the AWS CLI:
     ```bash
     aws ecs update-cluster-settings \
       --cluster medicare-cluster \
       --settings name=containerInsights,value=enabled \
       --region ap-south-1
     ```
   - This allows ECS to publish detailed metrics (CPU, memory, task count) to CloudWatch

- **Step-3: Add CloudWatch as a Data Source in Grafana Cloud**
   - In Grafana Cloud:
     - Go to **Connections → Add data source**
     - Select **Amazon CloudWatch**
     - Provide:
       - AWS region: `ap-south-1`
       - Authentication: Access & secret keys or IAM role (via AWS Cloud integration)
     - Click **Save & Test**

- **Step-4: Create Dashboard Panels**
   - A custom dashboard was created with the following panels:
     - **CPUUtilization**: Monitors CPU usage of ECS tasks
     - **MemoryUtilization**: Tracks memory consumption
     - **TaskCount**: Shows the number of running tasks
   - Metrics were queried from the namespace: `ECS/ContainerInsights`

---

## Technologies Used
- **AWS ECS Fargate** – for container orchestration
- **Amazon ECR** – for Docker image storage
- **IAM Roles & Policies** – for secure AWS access
- **Jenkins** – for CI/CD automation
- **Docker** – for containerizing the application
- **Slack** – for build notifications
- **GitHub** – for source control and webhook triggers
- **Grafana Cloud** – for dashboarding and alerting
- **CloudWatch** – for metrics and logs








