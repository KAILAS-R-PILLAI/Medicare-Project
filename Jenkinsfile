pipeline {
   
    agent any

    environment {
        DOCKER_IMAGE_NAME = 'medicare-app-repo'
        IMAGE_TAG = "${env.BUILD_NUMBER}"
        AWS_REGION = 'ap-south-1'
        AWS_ACCOUNT_ID = '354121451612'
        ECR_REPOSITORY = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${DOCKER_IMAGE_NAME}"
        ECR_REGISTRY_URL = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
        ECS_CLUSTER = 'medicare-cluster'
        ECS_SERVICE = 'medicare-app-service'
        ECS_TASK_ROLE = 'ecsTaskExecutionRole'
        ECS_TASK_FAMILY = 'medicare-task-def'
        CONTAINER_NAME = 'medicare-container'
        SUBNET_ID = 'subnet-0e9bb756b190aeda6'
        SECURITY_GROUP_ID = 'sg-0564fef9413077c4b'
        SLACK_CHANNEL = '#medicare-jenkins'
    }

    stages {
        stage('Checkout and Build Image') {
            steps {
                echo "Cloning repository and building Docker image..."
                checkout([
                    $class: 'GitSCM',
                    branches: [[name: 'main']],
                    userRemoteConfigs: [[
                        credentialsId: 'agent-1key',
                        url: 'https://github.com/KAILAS-R-PILLAI/Medicare-Project'
                    ]]
                ])
                sh "docker build -t ${DOCKER_IMAGE_NAME}:${IMAGE_TAG} ."
            }
        }

        stage('Ensure ECR to Push Image') {
            steps {
                withAwsCredentials {
                    sh """
                        if ! aws ecr describe-repositories --repository-names ${DOCKER_IMAGE_NAME} --region ${AWS_REGION} > /dev/null 2>&1; then
                            echo "Creating ECR repository: ${DOCKER_IMAGE_NAME}"
                            aws ecr create-repository --repository-name ${DOCKER_IMAGE_NAME} --region ${AWS_REGION}
                        else
                            echo "ECR repository already exists."
                        fi

                        echo "Logging into ECR and pushing image..."
                        aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY_URL}
                        docker tag ${DOCKER_IMAGE_NAME}:${IMAGE_TAG} ${ECR_REPOSITORY}:${IMAGE_TAG}
                        docker push ${ECR_REPOSITORY}:${IMAGE_TAG}
                    """
                }
            }
        }

        stage('Provision ECS Cluster and Define Task') {
            steps {
                withAwsCredentials {
                    sh """
                        CLUSTER_STATUS=\$(aws ecs describe-clusters --clusters ${ECS_CLUSTER} --region ${AWS_REGION} --query "clusters[0].status" --output text 2>/dev/null || echo "MISSING")
                        echo "CLUSTER_STATUS=\$CLUSTER_STATUS"
                        if [ "\$CLUSTER_STATUS" = "INACTIVE" ] || [ "\$CLUSTER_STATUS" = "MISSING" ] || [ "\$CLUSTER_STATUS" = "None" ]; then
                            echo "Creating ECS cluster: ${ECS_CLUSTER}"
                            aws ecs create-cluster --cluster-name ${ECS_CLUSTER} --region ${AWS_REGION}
                        fi

                        echo "Enabling Container Insights..."
                        aws ecs update-cluster-settings \
                            --cluster ${ECS_CLUSTER} \
                            --settings name=containerInsights,value=enabled \
                            --region ${AWS_REGION}

                        echo "Registering ECS task definition..."
                        aws ecs register-task-definition \
                            --family ${ECS_TASK_FAMILY} \
                            --requires-compatibilities FARGATE \
                            --network-mode awsvpc \
                            --cpu "256" \
                            --memory "512" \
                            --execution-role-arn arn:aws:iam::${AWS_ACCOUNT_ID}:role/${ECS_TASK_ROLE} \
                            --container-definitions '[{
                                "name": "${CONTAINER_NAME}",
                                "image": "${ECR_REPOSITORY}:${IMAGE_TAG}",
                                "essential": true,
                                "portMappings": [{
                                    "containerPort": 80,
                                    "hostPort": 80,
                                    "protocol": "tcp"
                                }]
                            }]' \
                            --region ${AWS_REGION}
                    """
                }
            }
        }

        stage('Deploy Service on ECS') {
            steps {
                withAwsCredentials {
                    sh """
                        SERVICE_STATUS=\$(aws ecs describe-services --cluster ${ECS_CLUSTER} --services ${ECS_SERVICE} --region ${AWS_REGION} --query "services[0].status" --output text 2>/dev/null || echo "MISSING")
                        if [ "\$SERVICE_STATUS" = "MISSING" ] || [ "\$SERVICE_STATUS" = "None" ]; then
                            echo "Creating ECS service: ${ECS_SERVICE}"
                            aws ecs create-service \
                                --cluster ${ECS_CLUSTER} \
                                --service-name ${ECS_SERVICE} \
                                --task-definition ${ECS_TASK_FAMILY} \
                                --desired-count 1 \
                                --launch-type FARGATE \
                                --network-configuration awsvpcConfiguration={subnets=["${SUBNET_ID}"],securityGroups=["${SECURITY_GROUP_ID}"],assignPublicIp="ENABLED"} \
                                --region ${AWS_REGION}
                        else
                            echo "ECS service already exists."
                        fi

                        echo "Deploying image to ECS..."
                        aws ecs update-service \
                            --cluster ${ECS_CLUSTER} \
                            --service ${ECS_SERVICE} \
                            --force-new-deployment \
                            --region ${AWS_REGION}
                    """
                }
            }
        }

        stage('Local Cleanup') {
            steps {
                echo "Cleaning up local Docker image..."
                sh "docker rmi -f ${DOCKER_IMAGE_NAME}:${IMAGE_TAG} || true"
            }
        }
    }
    
    post {
        always {
            echo '✅ Pipeline completed (success or failure)'
            slackSend(
                channel: env.SLACK_CHANNEL,
                color: '#439FE0',
                message: "🧹 *Build Completed:* `${env.JOB_NAME} #${env.BUILD_NUMBER}`\n" +
                         "Status: ${currentBuild.currentResult}\n" +
                         "Triggered by: ${env.BUILD_USER ?: 'Jenkins'}\n" +
                         "<${env.BUILD_URL}|View Build Logs>"
            )
            cleanWs()
        }

        success {
            echo '🎉 Deployment successful!'
            slackSend(
                channel: env.SLACK_CHANNEL,
                color: 'good',
                message: "✅ *SUCCESS:* `${env.JOB_NAME} #${env.BUILD_NUMBER}` deployed successfully!\n" +
                         "<${env.BUILD_URL}|View Build Details>"
            )
        }

        failure {
            echo '❌ Pipeline failed — check logs for details'
            slackSend(
                channel: env.SLACK_CHANNEL,
                color: 'danger',
                message: "❌ *FAILED:* `${env.JOB_NAME} #${env.BUILD_NUMBER}`\n" +
                         "<${env.BUILD_URL}|Check logs here>"
            )
        }
    }
}

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