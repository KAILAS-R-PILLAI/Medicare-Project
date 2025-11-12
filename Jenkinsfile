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
        SLACK_CHANNEL = '#medicare-jenkins'
    }

    stages {
        stage('Terraform Provisioning') {
            steps {
                withAwsCredentials {
                    dir('terraform') {
                        sh '''
                            terraform init
                            terraform apply -auto-approve
                        '''
                    }
                }
            }
        }

        stage('Checkout and Build Docker Image') {
            steps {
                echo "Cloning repository and building Docker image..."
                checkout([
                    $class: 'GitSCM',
                    branches: [[name: 'main']],
                    userRemoteConfigs: [[
                        credentialsId: 'agent-1key',
                        url: 'https://github.com/KAILAS-R-PILLAI/Medicare-CICD-Project'
                    ]]
                ])
                sh "docker build -t ${DOCKER_IMAGE_NAME}:${IMAGE_TAG} ."
            }
        }

        stage('Push Image to ECR') {
            steps {
                withAwsCredentials {
                    sh '''
                        aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY_URL}
                        docker tag ${DOCKER_IMAGE_NAME}:${IMAGE_TAG} ${ECR_REPOSITORY}:${IMAGE_TAG}
                        docker push ${ECR_REPOSITORY}:${IMAGE_TAG}
                    '''
                }
            }
        }

        stage('Trigger ECS Deployment') {
            steps {
                withAwsCredentials {
                    sh '''
                        echo "Triggering ECS deployment with new image..."
                        aws ecs update-service \
                            --cluster ${ECS_CLUSTER} \
                            --service ${ECS_SERVICE} \
                            --force-new-deployment \
                            --region ${AWS_REGION}
                    '''
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
