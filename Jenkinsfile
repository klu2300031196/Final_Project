pipeline {
    agent any

    environment {
        PYTHONUNBUFFERED = '1'
        WORKSPACE_DIR = "${WORKSPACE}"
    }

    stages {
        stage('Checkout Source') {
            steps {
                echo 'Checking out source code from Git repository...'
                checkout scm
            }
        }

        stage('Environment Setup & Lint') {
            steps {
                echo 'Setting up Python runtime and validating syntax...'
                bat 'python --version'
                bat 'python -m pip install -r requirements.txt || echo Skipping network install'
            }
        }

        stage('Security SAST Scan') {
            steps {
                echo 'Executing Static Application Security Testing (SAST)...'
                bat 'python -m tests.security.security_scanner'
            }
        }

        stage('Continuous Testing Matrix') {
            parallel {
                stage('Unit & Integration Tests') {
                    steps {
                        echo 'Running Pytest test suites across AUT layers...'
                        bat 'python -m pytest tests/unit tests/integration tests/e2e -v'
                    }
                }
                stage('Code Coverage Verification') {
                    steps {
                        echo 'Measuring AST Code Coverage against minimum 75% SLA...'
                        bat 'python -m engine.coverage_analyzer'
                    }
                }
                stage('Performance & Latency SLAs') {
                    steps {
                        echo 'Running concurrent load simulation and measuring P95 latency...'
                        bat 'python -m tests.performance.load_engine'
                    }
                }
            }
        }

        stage('DevOps Quality Gate Evaluation') {
            steps {
                echo 'Enforcing DevOps Quality Gate rules...'
                bat 'python -m engine.test_runner'
            }
        }
    }

    post {
        always {
            echo 'Archiving test reports and executive summary artifacts...'
            junit allowEmptyResults: true, testResults: 'reports/junit_report.xml'
            archiveArtifacts artifacts: 'reports/*.*', fingerprint: true, allowEmptyArchive: true
        }
        success {
            echo '==========================================================='
            echo ' DEVOPS CONTINUOUS TESTING QUALITY GATE: PASSED '
            echo ' Software is verified and approved for production rollout! '
            echo '==========================================================='
        }
        failure {
            echo '==========================================================='
            echo ' DEVOPS CONTINUOUS TESTING QUALITY GATE: FAILED '
            echo ' Deployment halted due to test or quality gate violations. '
            echo '==========================================================='
        }
    }
}
