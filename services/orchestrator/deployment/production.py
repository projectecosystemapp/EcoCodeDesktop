"""Production deployment configuration and utilities."""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

from eco_api.config import Settings
from eco_api.logging import configure_logging


@dataclass
class ProductionConfig:
    """Production-specific configuration settings."""
    
    # Logging configuration
    log_level: str = "INFO"
    log_file: Optional[Path] = None
    enable_structured_logging: bool = True
    log_rotation_max_bytes: int = 50 * 1024 * 1024  # 50MB
    log_backup_count: int = 10
    
    # Performance settings
    enable_file_caching: bool = True
    enable_ai_caching: bool = True
    file_cache_size: int = 200
    ai_cache_size: int = 100
    cache_ttl_seconds: int = 1800  # 30 minutes
    
    # Security settings
    enforce_https: bool = True
    enable_cors: bool = False
    allowed_origins: list[str] = None
    
    # Resource limits
    max_concurrent_specs: int = 10
    max_concurrent_tasks: int = 5
    task_timeout_minutes: int = 60
    max_file_size_mb: int = 10
    
    # Health check settings
    health_check_interval: int = 30
    enable_metrics: bool = True
    
    def __post_init__(self):
        if self.allowed_origins is None:
            self.allowed_origins = []


def load_production_config() -> ProductionConfig:
    """Load production configuration from environment variables."""
    
    config = ProductionConfig()
    
    # Logging configuration
    config.log_level = os.getenv('ECOCODE_LOG_LEVEL', config.log_level)
    
    log_file_path = os.getenv('ECOCODE_LOG_FILE')
    if log_file_path:
        config.log_file = Path(log_file_path)
    
    config.enable_structured_logging = os.getenv('ECOCODE_STRUCTURED_LOGGING', 'true').lower() == 'true'
    
    # Performance settings
    config.enable_file_caching = os.getenv('ECOCODE_FILE_CACHING', 'true').lower() == 'true'
    config.enable_ai_caching = os.getenv('ECOCODE_AI_CACHING', 'true').lower() == 'true'
    
    if cache_size := os.getenv('ECOCODE_FILE_CACHE_SIZE'):
        config.file_cache_size = int(cache_size)
    
    if ai_cache_size := os.getenv('ECOCODE_AI_CACHE_SIZE'):
        config.ai_cache_size = int(ai_cache_size)
    
    if cache_ttl := os.getenv('ECOCODE_CACHE_TTL'):
        config.cache_ttl_seconds = int(cache_ttl)
    
    # Security settings
    config.enforce_https = os.getenv('ECOCODE_ENFORCE_HTTPS', 'true').lower() == 'true'
    config.enable_cors = os.getenv('ECOCODE_ENABLE_CORS', 'false').lower() == 'true'
    
    if allowed_origins := os.getenv('ECOCODE_ALLOWED_ORIGINS'):
        config.allowed_origins = [origin.strip() for origin in allowed_origins.split(',')]
    
    # Resource limits
    if max_specs := os.getenv('ECOCODE_MAX_CONCURRENT_SPECS'):
        config.max_concurrent_specs = int(max_specs)
    
    if max_tasks := os.getenv('ECOCODE_MAX_CONCURRENT_TASKS'):
        config.max_concurrent_tasks = int(max_tasks)
    
    if task_timeout := os.getenv('ECOCODE_TASK_TIMEOUT_MINUTES'):
        config.task_timeout_minutes = int(task_timeout)
    
    if max_file_size := os.getenv('ECOCODE_MAX_FILE_SIZE_MB'):
        config.max_file_size_mb = int(max_file_size)
    
    return config


def setup_production_environment(config: ProductionConfig) -> None:
    """Set up the production environment with optimizations."""
    
    # Configure logging
    configure_logging(
        level=getattr(logging, config.log_level.upper()),
        log_file=config.log_file,
        max_bytes=config.log_rotation_max_bytes,
        backup_count=config.log_backup_count,
        enable_structured_logging=config.enable_structured_logging,
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Production environment setup initiated")
    
    # Configure performance optimizations
    if config.enable_file_caching or config.enable_ai_caching:
        from eco_api.specs.performance import _file_cache, _ai_cache
        
        if config.enable_file_caching:
            _file_cache.max_size = config.file_cache_size
            _file_cache.ttl_seconds = config.cache_ttl_seconds
            logger.info(f"File caching enabled - Size: {config.file_cache_size}, TTL: {config.cache_ttl_seconds}s")
        
        if config.enable_ai_caching:
            _ai_cache.max_size = config.ai_cache_size
            _ai_cache.ttl_seconds = config.cache_ttl_seconds
            logger.info(f"AI caching enabled - Size: {config.ai_cache_size}, TTL: {config.cache_ttl_seconds}s")
    
    # Set resource limits
    os.environ['ECOCODE_MAX_CONCURRENT_SPECS'] = str(config.max_concurrent_specs)
    os.environ['ECOCODE_MAX_CONCURRENT_TASKS'] = str(config.max_concurrent_tasks)
    os.environ['ECOCODE_TASK_TIMEOUT_MINUTES'] = str(config.task_timeout_minutes)
    
    logger.info("Production environment setup completed")


def get_health_check_info() -> Dict[str, Any]:
    """Get comprehensive health check information for production monitoring."""
    
    from eco_api.specs.performance import get_cache_stats
    import psutil
    import sys
    
    # System information
    process = psutil.Process()
    
    health_info = {
        'status': 'healthy',
        'timestamp': str(process.create_time()),
        'system': {
            'python_version': sys.version,
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_usage_percent': psutil.disk_usage('/').percent,
        },
        'process': {
            'pid': process.pid,
            'memory_mb': process.memory_info().rss / 1024 / 1024,
            'cpu_percent': process.cpu_percent(),
            'num_threads': process.num_threads(),
            'open_files': len(process.open_files()),
        },
        'caches': get_cache_stats(),
    }
    
    # Check for potential issues
    warnings = []
    
    if health_info['system']['memory_percent'] > 90:
        warnings.append('High system memory usage')
        health_info['status'] = 'warning'
    
    if health_info['process']['memory_mb'] > 1000:  # 1GB
        warnings.append('High process memory usage')
        health_info['status'] = 'warning'
    
    if health_info['system']['disk_usage_percent'] > 95:
        warnings.append('High disk usage')
        health_info['status'] = 'warning'
    
    if warnings:
        health_info['warnings'] = warnings
    
    return health_info


def validate_production_settings(settings: Settings) -> list[str]:
    """Validate settings for production deployment."""
    
    issues = []
    
    # Check required settings
    if not settings.master_passphrase:
        issues.append("Master passphrase is required for production")
    
    if len(settings.master_passphrase) < 32:
        issues.append("Master passphrase should be at least 32 characters for production")
    
    # Check AWS configuration
    if settings.aws.use_bedrock and not settings.aws.region_name:
        issues.append("AWS region is required when Bedrock is enabled")
    
    if settings.aws.use_s3_sync and not settings.aws.workspace_bucket:
        issues.append("S3 workspace bucket is required when S3 sync is enabled")
    
    # Check file system permissions
    try:
        test_file = settings.projects_root / '.ecocode_test'
        test_file.write_text('test')
        test_file.unlink()
    except Exception as e:
        issues.append(f"Cannot write to projects root directory: {e}")
    
    # Check spec configuration
    if not settings.specs.enabled:
        issues.append("Spec-driven features are disabled")
    
    return issues


def create_systemd_service(
    service_name: str = 'ecocode-orchestrator',
    user: str = 'ecocode',
    working_directory: str = '/opt/ecocode/services/orchestrator',
    python_path: str = '/opt/ecocode/services/orchestrator/.venv/bin/python',
    port: int = 8890,
) -> str:
    """Generate systemd service file for production deployment."""
    
    service_content = f"""[Unit]
Description=EcoCode Orchestrator Service
After=network.target
Wants=network.target

[Service]
Type=exec
User={user}
Group={user}
WorkingDirectory={working_directory}
Environment=PATH={working_directory}/.venv/bin
Environment=ECOCODE_LOG_LEVEL=INFO
Environment=ECOCODE_LOG_FILE=/var/log/ecocode/orchestrator.log
Environment=ECOCODE_STRUCTURED_LOGGING=true
ExecStart={python_path} -m uvicorn eco_api.main:app --host 0.0.0.0 --port {port} --workers 1
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier={service_name}

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths={working_directory} /var/log/ecocode /tmp

# Resource limits
LimitNOFILE=65536
MemoryMax=2G
CPUQuota=200%

[Install]
WantedBy=multi-user.target
"""
    
    return service_content


def create_nginx_config(
    server_name: str = 'ecocode.local',
    upstream_port: int = 8890,
    ssl_cert_path: Optional[str] = None,
    ssl_key_path: Optional[str] = None,
) -> str:
    """Generate nginx configuration for production deployment."""
    
    ssl_config = ""
    if ssl_cert_path and ssl_key_path:
        ssl_config = f"""
    listen 443 ssl http2;
    ssl_certificate {ssl_cert_path};
    ssl_certificate_key {ssl_key_path};
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
"""
    
    redirect_config = ""
    if ssl_config:
        redirect_config = f"""
server {{
    listen 80;
    server_name {server_name};
    return 301 https://$server_name$request_uri;
}}
"""
    
    nginx_config = f"""upstream ecocode_orchestrator {{
    server 127.0.0.1:{upstream_port};
    keepalive 32;
}}

{redirect_config}

server {{
    listen 80;{ssl_config}
    server_name {server_name};
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;
    
    # Proxy settings
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_cache_bypass $http_upgrade;
    
    # Timeouts
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
    
    location / {{
        proxy_pass http://ecocode_orchestrator;
    }}
    
    location /health {{
        proxy_pass http://ecocode_orchestrator;
        access_log off;
    }}
    
    # Static files (if any)
    location /static/ {{
        alias /opt/ecocode/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }}
}}
"""
    
    return nginx_config