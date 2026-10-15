pipeline {
    agent any

    environment {
        DOCKERHUB_CREDENTIALS = credentials('dockerhub-credentials')
        IMAGE_NAME = "dhruvilsatani/ml-app"
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
                sh "docker push ${IMAGE_NAME}:${BUILD_NUMBER}"
            }
        }
    }

    post {
        always {
            sh "docker logout"
        }
    }
}
