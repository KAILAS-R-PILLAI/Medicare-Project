pipeline {
   
    agent any

    environment {
        DOCKER_IMAGE_NAME = 'medicare-app-repo'
        IMAGE_TAG = "${env.BUILD_NUMBER}"
        AWS_REGION = 'ap-south-1'
        AWS_ACCOUNT_ID = #['Your account ID']
        ECR_REPOSITORY = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${DOCKER_IMAGE_NAME}"
        ECR_REGISTRY_URL = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
        ECS_CLUSTER = 'medicare-cluster'
        ECS_SERVICE = 'medicare-app-service'
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
                        credentialsId: 'github-agent',
                        url: 'https://github.com/KAILAS-R-PILLAI/Medicare-CICD-Project'
                    ]]
                ])
            }
        }
        
        stage('Docker Build') {
            steps {
                echo "Building Docker image: ${DOCKER_IMAGE_NAME}:${IMAGE_TAG}"
                sh "docker build -t ${DOCKER_IMAGE_NAME}:${IMAGE_TAG} ."
            }
        }

        stage('ECR Login to Push Image') {
            steps {
                withAwsCredentials {
                    sh """
                        echo "Logging into ECR and pushing image..."

                        aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY_URL}
                        
                        docker tag ${DOCKER_IMAGE_NAME}:${IMAGE_TAG} ${ECR_REPOSITORY}:${IMAGE_TAG}
                    
                        docker push ${ECR_REPOSITORY}:${IMAGE_TAG}
                    """
                }
            }
        }

        stage('Deploy Service on ECS') {
            steps {
                withAwsCredentials {
                    sh """
                        echo "Deploying the image to ECS Fargate service: ${ECS_SERVICE}..."
                        aws ecs update-service \\
                            --cluster ${ECS_CLUSTER} \\
                            --service ${ECS_SERVICE} \\
                            --settings name=containerInsights,value=enabled
                            --force-new-deployment \\
                            --region ${AWS_REGION}
                            echo "Deployment initiated. ECS will now perform a rolling update."
                            
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
                message: "🧹 Build Completed: ${env.JOB_NAME} #${env.BUILD_NUMBER}\n" +
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
                message: "✅ SUCCESS: ${env.JOB_NAME} #${env.BUILD_NUMBER} deployed successfully!\n" +
                         "<${env.BUILD_URL}|View Build Details>"
            )
        }

        failure {
            echo '❌ Pipeline failed — check logs for details'
            slackSend(
                channel: env.SLACK_CHANNEL,
                color: 'danger',
                message: "❌ FAILED: ${env.JOB_NAME} #${env.BUILD_NUMBER}\n" +
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
