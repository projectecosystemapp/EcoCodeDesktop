#!/bin/bash

# EcoCode Orchestrator Production Deployment Script
# This script sets up the orchestrator service for production deployment

set -euo pipefail

# Configuration
SERVICE_NAME="ecocode-orchestrator"
SERVICE_USER="ecocode"
INSTALL_DIR="/opt/ecocode"
LOG_DIR="/var/log/ecocode"
PYTHON_VERSION="3.11"
VENV_DIR="$INSTALL_DIR/services/orchestrator/.venv"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

# Create service user
create_service_user() {
    log_info "Creating service user: $SERVICE_USER"
    
    if ! id "$SERVICE_USER" &>/dev/null; then
        useradd --system --shell /bin/bash --home-dir "$INSTALL_DIR" --create-home "$SERVICE_USER"
        log_info "Service user created: $SERVICE_USER"
    else
        log_info "Service user already exists: $SERVICE_USER"
    fi
}

# Create directories
create_directories() {
    log_info "Creating directories"
    
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "/etc/ecocode"
    
    chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
    chown -R "$SERVICE_USER:$SERVICE_USER" "$LOG_DIR"
    
    log_info "Directories created and permissions set"
}

# Install system dependencies
install_system_dependencies() {
    log_info "Installing system dependencies"
    
    # Update package list
    apt-get update
    
    # Install required packages
    apt-get install -y \
        python3.11 \
        python3.11-venv \
        python3.11-dev \
        build-essential \
        curl \
        git \
        nginx \
        logrotate \
        supervisor
    
    log_info "System dependencies installed"
}

# Setup Python virtual environment
setup_python_environment() {
    log_info "Setting up Python virtual environment"
    
    # Create virtual environment
    sudo -u "$SERVICE_USER" python3.11 -m venv "$VENV_DIR"
    
    # Upgrade pip
    sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel
    
    log_info "Python virtual environment created"
}

# Install Python dependencies
install_python_dependencies() {
    log_info "Installing Python dependencies"
    
    # Copy requirements and install
    if [[ -f "requirements.txt" ]]; then
        sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" install -r requirements.txt
    else
        log_warn "requirements.txt not found, installing from pyproject.toml"
        sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" install -e .
    fi
    
    log_info "Python dependencies installed"
}

# Create systemd service
create_systemd_service() {
    log_info "Creating systemd service"
    
    # Generate service file using Python
    sudo -u "$SERVICE_USER" "$VENV_DIR/bin/python" -c "
from deployment.production import create_systemd_service
service_content = create_systemd_service(
    service_name='$SERVICE_NAME',
    user='$SERVICE_USER',
    working_directory='$INSTALL_DIR/services/orchestrator',
    python_path='$VENV_DIR/bin/python'
)
print(service_content)
" > "/etc/systemd/system/$SERVICE_NAME.service"
    
    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"
    
    log_info "Systemd service created and enabled"
}

# Configure nginx
configure_nginx() {
    log_info "Configuring nginx"
    
    # Generate nginx config
    sudo -u "$SERVICE_USER" "$VENV_DIR/bin/python" -c "
from deployment.production import create_nginx_config
nginx_content = create_nginx_config(server_name='localhost')
print(nginx_content)
" > "/etc/nginx/sites-available/ecocode"
    
    # Enable site
    ln -sf "/etc/nginx/sites-available/ecocode" "/etc/nginx/sites-enabled/ecocode"
    
    # Remove default site
    rm -f "/etc/nginx/sites-enabled/default"
    
    # Test nginx configuration
    nginx -t
    
    log_info "Nginx configured"
}

# Setup log rotation
setup_log_rotation() {
    log_info "Setting up log rotation"
    
    cat > "/etc/logrotate.d/ecocode" << EOF
$LOG_DIR/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $SERVICE_USER $SERVICE_USER
    postrotate
        systemctl reload $SERVICE_NAME
    endscript
}
EOF
    
    log_info "Log rotation configured"
}

# Create environment file
create_environment_file() {
    log_info "Creating environment configuration"
    
    cat > "/etc/ecocode/orchestrator.env" << EOF
# EcoCode Orchestrator Environment Configuration
# Copy this file and customize for your environment

# Required: Master passphrase for encryption (minimum 32 characters)
ECOCODE_MASTER_PASSPHRASE=your-secure-master-passphrase-here-change-this

# Logging configuration
ECOCODE_LOG_LEVEL=INFO
ECOCODE_LOG_FILE=$LOG_DIR/orchestrator.log
ECOCODE_STRUCTURED_LOGGING=true

# Performance settings
ECOCODE_FILE_CACHING=true
ECOCODE_AI_CACHING=true
ECOCODE_FILE_CACHE_SIZE=200
ECOCODE_AI_CACHE_SIZE=100
ECOCODE_CACHE_TTL=1800

# AWS Configuration (optional)
# ECOCODE_AWS_REGION_NAME=us-east-1
# ECOCODE_AWS_PROFILE_NAME=default
# ECOCODE_AWS_USE_BEDROCK=true
# ECOCODE_AWS_USE_S3_SYNC=false
# ECOCODE_AWS_USE_SECRETS_MANAGER=false

# Spec-driven workflow settings
ECOCODE_SPEC_ENABLED=true
ECOCODE_SPEC_AUTO_BACKUP=true
ECOCODE_SPEC_MAX_CONCURRENT_TASKS=3
ECOCODE_SPEC_TASK_TIMEOUT_MINUTES=30

# Security settings
ECOCODE_ENFORCE_HTTPS=false
ECOCODE_ENABLE_CORS=false
# ECOCODE_ALLOWED_ORIGINS=https://yourdomain.com

# Resource limits
ECOCODE_MAX_CONCURRENT_SPECS=10
ECOCODE_MAX_CONCURRENT_TASKS=5
ECOCODE_MAX_FILE_SIZE_MB=10
EOF
    
    chown "$SERVICE_USER:$SERVICE_USER" "/etc/ecocode/orchestrator.env"
    chmod 600 "/etc/ecocode/orchestrator.env"
    
    log_warn "Environment file created at /etc/ecocode/orchestrator.env"
    log_warn "Please edit this file and set your master passphrase and other configuration"
}

# Validate installation
validate_installation() {
    log_info "Validating installation"
    
    # Check if service user exists
    if ! id "$SERVICE_USER" &>/dev/null; then
        log_error "Service user not found: $SERVICE_USER"
        return 1
    fi
    
    # Check if directories exist
    for dir in "$INSTALL_DIR" "$LOG_DIR" "/etc/ecocode"; do
        if [[ ! -d "$dir" ]]; then
            log_error "Directory not found: $dir"
            return 1
        fi
    done
    
    # Check if virtual environment exists
    if [[ ! -f "$VENV_DIR/bin/python" ]]; then
        log_error "Python virtual environment not found: $VENV_DIR"
        return 1
    fi
    
    # Check if systemd service exists
    if [[ ! -f "/etc/systemd/system/$SERVICE_NAME.service" ]]; then
        log_error "Systemd service not found: $SERVICE_NAME"
        return 1
    fi
    
    log_info "Installation validation passed"
}

# Main deployment function
main() {
    log_info "Starting EcoCode Orchestrator deployment"
    
    check_root
    create_service_user
    create_directories
    install_system_dependencies
    setup_python_environment
    install_python_dependencies
    create_systemd_service
    configure_nginx
    setup_log_rotation
    create_environment_file
    validate_installation
    
    log_info "Deployment completed successfully!"
    log_warn "Next steps:"
    log_warn "1. Edit /etc/ecocode/orchestrator.env and set your configuration"
    log_warn "2. Start the service: systemctl start $SERVICE_NAME"
    log_warn "3. Start nginx: systemctl start nginx"
    log_warn "4. Check service status: systemctl status $SERVICE_NAME"
    log_warn "5. Check logs: journalctl -u $SERVICE_NAME -f"
}

# Run main function
main "$@"