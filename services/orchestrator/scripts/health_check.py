#!/usr/bin/env python3
"""
Health check script for EcoCode Orchestrator production monitoring.
Can be used with monitoring systems like Nagios, Zabbix, or Prometheus.
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class HealthChecker:
    """Health checker for EcoCode Orchestrator service."""
    
    def __init__(self, base_url: str = "http://localhost:8890", timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        self.session.timeout = timeout
    
    def check_api_health(self) -> Dict[str, Any]:
        """Check API health endpoint."""
        try:
            response = self.session.get(f"{self.base_url}/health")
            response.raise_for_status()
            
            health_data = response.json()
            return {
                'status': 'ok',
                'response_time_ms': response.elapsed.total_seconds() * 1000,
                'api_version': health_data.get('version', 'unknown'),
                'api_status': health_data.get('status', 'unknown'),
                'timestamp': health_data.get('timestamp')
            }
        except requests.exceptions.ConnectionError:
            return {
                'status': 'error',
                'error': 'Connection refused - service may be down',
                'response_time_ms': None
            }
        except requests.exceptions.Timeout:
            return {
                'status': 'error',
                'error': f'Request timeout after {self.timeout}s',
                'response_time_ms': None
            }
        except requests.exceptions.HTTPError as e:
            return {
                'status': 'error',
                'error': f'HTTP error: {e.response.status_code}',
                'response_time_ms': e.response.elapsed.total_seconds() * 1000 if e.response else None
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': f'Unexpected error: {str(e)}',
                'response_time_ms': None
            }
    
    def check_specs_endpoint(self) -> Dict[str, Any]:
        """Check specs endpoint functionality."""
        try:
            response = self.session.get(f"{self.base_url}/specs")
            response.raise_for_status()
            
            specs_data = response.json()
            return {
                'status': 'ok',
                'response_time_ms': response.elapsed.total_seconds() * 1000,
                'specs_count': len(specs_data.get('specs', [])),
                'total_count': specs_data.get('total_count', 0)
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': f'Specs endpoint error: {str(e)}',
                'response_time_ms': None
            }
    
    def check_file_system(self, projects_root: Optional[Path] = None) -> Dict[str, Any]:
        """Check file system health."""
        if projects_root is None:
            projects_root = Path.cwd()
        
        try:
            # Check if projects root is accessible
            if not projects_root.exists():
                return {
                    'status': 'error',
                    'error': f'Projects root does not exist: {projects_root}'
                }
            
            if not projects_root.is_dir():
                return {
                    'status': 'error',
                    'error': f'Projects root is not a directory: {projects_root}'
                }
            
            # Check write permissions
            test_file = projects_root / '.ecocode_health_check'
            try:
                test_file.write_text('health check')
                test_file.unlink()
            except Exception as e:
                return {
                    'status': 'error',
                    'error': f'Cannot write to projects root: {e}'
                }
            
            # Check disk space
            import shutil
            total, used, free = shutil.disk_usage(projects_root)
            free_percent = (free / total) * 100
            
            status = 'ok'
            warnings = []
            
            if free_percent < 5:
                status = 'error'
                warnings.append('Critical: Less than 5% disk space remaining')
            elif free_percent < 15:
                status = 'warning'
                warnings.append('Warning: Less than 15% disk space remaining')
            
            return {
                'status': status,
                'projects_root': str(projects_root),
                'disk_free_percent': round(free_percent, 2),
                'disk_free_gb': round(free / (1024**3), 2),
                'disk_total_gb': round(total / (1024**3), 2),
                'warnings': warnings if warnings else None
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': f'File system check failed: {str(e)}'
            }
    
    def check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage."""
        try:
            import psutil
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Load average (Unix-like systems)
            load_avg = None
            try:
                load_avg = psutil.getloadavg()
            except AttributeError:
                # Windows doesn't have load average
                pass
            
            # Determine status
            status = 'ok'
            warnings = []
            
            if cpu_percent > 90:
                status = 'warning'
                warnings.append(f'High CPU usage: {cpu_percent}%')
            
            if memory_percent > 90:
                status = 'error'
                warnings.append(f'Critical memory usage: {memory_percent}%')
            elif memory_percent > 80:
                status = 'warning'
                warnings.append(f'High memory usage: {memory_percent}%')
            
            result = {
                'status': status,
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'memory_available_gb': round(memory.available / (1024**3), 2),
                'warnings': warnings if warnings else None
            }
            
            if load_avg:
                result['load_average'] = {
                    '1min': load_avg[0],
                    '5min': load_avg[1],
                    '15min': load_avg[2]
                }
            
            return result
            
        except ImportError:
            return {
                'status': 'warning',
                'error': 'psutil not available - cannot check system resources'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': f'System resource check failed: {str(e)}'
            }
    
    def run_comprehensive_check(self, projects_root: Optional[Path] = None) -> Dict[str, Any]:
        """Run all health checks and return comprehensive status."""
        
        start_time = time.time()
        
        checks = {
            'api': self.check_api_health(),
            'specs': self.check_specs_endpoint(),
            'filesystem': self.check_file_system(projects_root),
            'system': self.check_system_resources()
        }
        
        # Determine overall status
        overall_status = 'ok'
        errors = []
        warnings = []
        
        for check_name, check_result in checks.items():
            if check_result['status'] == 'error':
                overall_status = 'error'
                errors.append(f"{check_name}: {check_result.get('error', 'Unknown error')}")
            elif check_result['status'] == 'warning' and overall_status != 'error':
                overall_status = 'warning'
                if 'warnings' in check_result and check_result['warnings']:
                    warnings.extend([f"{check_name}: {w}" for w in check_result['warnings']])
        
        result = {
            'overall_status': overall_status,
            'check_duration_ms': round((time.time() - start_time) * 1000, 2),
            'timestamp': time.time(),
            'checks': checks
        }
        
        if errors:
            result['errors'] = errors
        if warnings:
            result['warnings'] = warnings
        
        return result


def main():
    """Main function for command-line usage."""
    
    parser = argparse.ArgumentParser(description='EcoCode Orchestrator Health Check')
    parser.add_argument(
        '--url', 
        default='http://localhost:8890',
        help='Base URL for the orchestrator service (default: http://localhost:8890)'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Request timeout in seconds (default: 30)'
    )
    parser.add_argument(
        '--projects-root',
        type=Path,
        help='Path to projects root directory (default: current directory)'
    )
    parser.add_argument(
        '--format',
        choices=['json', 'text', 'nagios'],
        default='text',
        help='Output format (default: text)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.INFO)
    
    # Run health check
    checker = HealthChecker(args.url, args.timeout)
    result = checker.run_comprehensive_check(args.projects_root)
    
    # Output results
    if args.format == 'json':
        print(json.dumps(result, indent=2, default=str))
    elif args.format == 'nagios':
        # Nagios-compatible output
        status_code = {
            'ok': 0,
            'warning': 1,
            'error': 2
        }.get(result['overall_status'], 3)
        
        status_text = result['overall_status'].upper()
        message = f"EcoCode Orchestrator {status_text}"
        
        if 'errors' in result:
            message += f" - Errors: {'; '.join(result['errors'])}"
        elif 'warnings' in result:
            message += f" - Warnings: {'; '.join(result['warnings'])}"
        
        print(message)
        sys.exit(status_code)
    else:
        # Human-readable text output
        print(f"EcoCode Orchestrator Health Check")
        print(f"Overall Status: {result['overall_status'].upper()}")
        print(f"Check Duration: {result['check_duration_ms']}ms")
        print()
        
        for check_name, check_result in result['checks'].items():
            print(f"{check_name.title()} Check: {check_result['status'].upper()}")
            if check_result['status'] == 'error' and 'error' in check_result:
                print(f"  Error: {check_result['error']}")
            elif 'warnings' in check_result and check_result['warnings']:
                for warning in check_result['warnings']:
                    print(f"  Warning: {warning}")
            print()
        
        if result['overall_status'] != 'ok':
            sys.exit(1)


if __name__ == '__main__':
    main()