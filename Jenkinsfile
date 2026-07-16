pipeline {
    agent any

    environment {
        GHCR_CREDENTIALS_ID = 'ghcr-credentials'
        GITHUB_USER         = 'thathsarabandara'
        IMAGE_NAME          = "ghcr.io/${GITHUB_USER}/07-rex-robot-service"
        IMAGE_TAG           = "${env.BUILD_NUMBER}"

        APP_ENV = 'test'
        MYSQL_HOST = '127.0.0.1'
        MYSQL_PORT = '3306'
        MYSQL_DATABASE = 'rex_robot_test'
        MYSQL_USER = 'rex_user'
        MYSQL_PASSWORD = 'rex_password'
        REDIS_URL = 'redis://127.0.0.1:6379/1'
        USER_JWT_SECRET_KEY = 'jenkins-user-secret'
        USER_JWT_ALGORITHM = 'HS256'
        USER_JWT_ISSUER = 'rex-auth-service'
        USER_JWT_AUDIENCE = 'rex-platform'
        ROBOT_JWT_SECRET_KEY = 'jenkins-robot-secret'
        ROBOT_JWT_ALGORITHM = 'HS256'
        ROBOT_ACCESS_TOKEN_EXPIRE_HOURS = '12'
        ROBOT_REFRESH_TOKEN_EXPIRE_DAYS = '30'
        MQTT_HOST = 'localhost'
        MQTT_PORT = '1883'
        MQTT_USERNAME = 'test'
        MQTT_PASSWORD = 'test'
        MQTT_TLS_ENABLED = 'false'
        KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092'
        KAFKA_CLIENT_ID = 'rex-robot-service-jenkins'
        CONTROL_LEASE_EXPIRE_SECONDS = '10'
        JOYSTICK_COMMAND_TIMEOUT_MS = '500'
        MAX_WEBSOCKET_MESSAGES_PER_SECOND = '30'
        DEFAULT_HEARTBEAT_INTERVAL_SECONDS = '5'
        DEFAULT_HEARTBEAT_TIMEOUT_SECONDS = '20'
    }

    stages {

        stage('Checkout') {
            steps {
                echo 'Checking out source code from SCM...'
                checkout scm
            }
        }

        stage('Environment') {
            steps {
                echo 'Verifying runtime tools are available...'
                sh '''
                    python3 --version
                    pip3 --version
                    docker --version
                '''
            }
        }

        stage('Install Dependencies') {
            steps {
                echo 'Creating virtual environment and installing dependencies...'
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    python -m pip install --upgrade pip
                    pip install -r requirements.txt -r requirements-dev.txt
                '''
            }
        }

        stage('Lint') {
            steps {
                echo 'Running lint...'
                sh '''
                    . venv/bin/activate
                    ruff check .
                    mypy app
                '''
            }
        }

        stage('Test') {
            steps {
                echo 'Running tests...'
                sh '''
                    . venv/bin/activate
                    alembic upgrade head
                    pytest \
                      --cov=app \
                      --cov-report=term-missing \
                      --cov-report=xml \
                      --cov-fail-under=90
                '''
            }
        }

        stage('Build') {
            steps {
                echo "Building Docker image: ${IMAGE_NAME}:${IMAGE_TAG}"
                sh """
                    docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .
                    docker tag  ${IMAGE_NAME}:${IMAGE_TAG} ${IMAGE_NAME}:latest
                    docker tag  ${IMAGE_NAME}:${IMAGE_TAG} ${IMAGE_NAME}:main
                """
            }
        }

        stage('Push') {
            when {
                branch 'main'
            }
            steps {
                echo "Pushing to GitHub Container Registry: ${IMAGE_NAME}"
                withCredentials([usernamePassword(
                    credentialsId: GHCR_CREDENTIALS_ID,
                    usernameVariable: 'GHCR_USER',
                    passwordVariable: 'GHCR_TOKEN'
                )]) {
                    sh """
                        echo "\${GHCR_TOKEN}" | docker login ghcr.io -u "\${GHCR_USER}" --password-stdin
                        docker push ${IMAGE_NAME}:${IMAGE_TAG}
                        docker push ${IMAGE_NAME}:latest
                        docker push ${IMAGE_NAME}:main
                        echo "Pushed ${IMAGE_NAME}:${IMAGE_TAG}, ${IMAGE_NAME}:latest, and ${IMAGE_NAME}:main"
                    """
                }
            }
        }

    }

    post {
        always {
            sh 'docker logout ghcr.io || true'
            cleanWs()
        }
        success {
            echo "Pipeline SUCCESS — ${IMAGE_NAME}:${IMAGE_TAG} is live on GHCR!"
        }
        failure {
            echo 'Pipeline FAILED — check console output above for details.'
        }
    }
}
