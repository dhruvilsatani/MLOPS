pipeline {
    agent any

    environment {
    DOCKERHUB_CREDENTIALS = credentials('dockerhub-credentials')
    AZURE_CREDENTIALS = credentials('azure-sp-credentials')
    IMAGE_NAME = "dhruvilsatani/ml-app"
    ACR_NAME = "mlappacr1"
       }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Lint') {
            steps {
                script {
                    docker.image('python:3.9-slim').inside {
                        sh 'pip install flake8'
                        sh 'flake8 . --select=E9,F --show-source'
                    }
                }
            }
        }

        stage('SonarQube Analysis') {
            steps {
                script {
                    def scannerHome = tool 'SonarScanner'
                    withSonarQubeEnv('mysonarqube') {
                        sh "${scannerHome}/bin/sonar-scanner -Dsonar.projectKey=ml-app -Dsonar.sources=."
                    }
                }
            }
        }

        stage('Quality Gate') {
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        stage('Train & Test') {
            steps {
                script {
                    docker.image('python:3.9-slim').inside {
                        sh 'pip install -r requirements-dev.txt'
                        sh 'python train.py --no-tracking'
                        sh 'python -m pytest -q'
                    }
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                sh "docker build -t ${IMAGE_NAME}:${BUILD_NUMBER} ."
            }
        }

        stage('Push Image') {
            steps {
                sh "echo ${DOCKERHUB_CREDENTIALS_PSW} | docker login -u ${DOCKERHUB_CREDENTIALS_USR} --password-stdin"
                sh "docker build --platform linux/amd64 -t ${IMAGE_NAME}:${BUILD_NUMBER} ."
            }
        }
        stage('Deploy to AKS') {
           steps {
                sh """
                    az login --service-principal -u ${AZURE_CREDENTIALS_USR} -p ${AZURE_CREDENTIALS_PSW} --tenant 70d30f56-bbca-47ce-bb1d-500137fb00f4
                    az acr login --name ${ACR_NAME}
                    docker tag ${IMAGE_NAME}:${BUILD_NUMBER} ${ACR_NAME}.azurecr.io/ml-app:${BUILD_NUMBER}
                    docker push ${ACR_NAME}.azurecr.io/ml-app:${BUILD_NUMBER}
                    az aks get-credentials --resource-group ml-app-rg --name ml-app-aks --overwrite-existing
                    helm upgrade --install ml-app-azure k8s/ml-app-chart -f k8s/ml-app-chart/values-azure.yaml --set image.tag=${BUILD_NUMBER}
                """
    }
}
    }

    post {
        always {
            sh "docker logout"
        }
    }
}
