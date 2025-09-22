import psutil
import os
import subprocess
import time
from datetime import datetime, timedelta
import json
import logging

class SystemInfoCollector:
    """
    Collects and provides system information about the Raspberry Pi.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.boot_time = psutil.boot_time()
        
    def get_cpu_info(self):
        """Get CPU information including usage, frequency, and temperature."""
        cpu_info = {}
        
        try:
            # CPU usage
            cpu_info['usage_percent'] = psutil.cpu_percent(interval=1)
            cpu_info['usage_per_core'] = psutil.cpu_percent(interval=1, percpu=True)
            
            # CPU frequency
            cpu_freq = psutil.cpu_freq()
            if cpu_freq:
                cpu_info['frequency_current'] = cpu_freq.current
                cpu_info['frequency_min'] = cpu_freq.min
                cpu_info['frequency_max'] = cpu_freq.max
            
            # CPU temperature (Raspberry Pi specific)
            cpu_info['temperature'] = self._get_cpu_temperature()
            
            # Load average
            load_avg = os.getloadavg()
            cpu_info['load_average'] = {
                '1min': load_avg[0],
                '5min': load_avg[1],
                '15min': load_avg[2]
            }
            
        except Exception as e:
            self.logger.error(f"Error getting CPU info: {e}")
            cpu_info['error'] = str(e)
        
        return cpu_info
    
    def get_memory_info(self):
        """Get memory usage information."""
        memory_info = {}
        
        try:
            # Virtual memory
            vmem = psutil.virtual_memory()
            memory_info['total'] = vmem.total
            memory_info['available'] = vmem.available
            memory_info['used'] = vmem.used
            memory_info['percent'] = vmem.percent
            memory_info['free'] = vmem.free
            
            # Swap memory
            swap = psutil.swap_memory()
            memory_info['swap'] = {
                'total': swap.total,
                'used': swap.used,
                'free': swap.free,
                'percent': swap.percent
            }
            
        except Exception as e:
            self.logger.error(f"Error getting memory info: {e}")
            memory_info['error'] = str(e)
        
        return memory_info
    
    def get_disk_info(self):
        """Get disk usage information."""
        disk_info = {}
        
        try:
            # Root filesystem
            root_usage = psutil.disk_usage('/')
            disk_info['root'] = {
                'total': root_usage.total,
                'used': root_usage.used,
                'free': root_usage.free,
                'percent': (root_usage.used / root_usage.total) * 100
            }
            
            # Disk I/O statistics
            disk_io = psutil.disk_io_counters()
            if disk_io:
                disk_info['io'] = {
                    'read_bytes': disk_io.read_bytes,
                    'write_bytes': disk_io.write_bytes,
                    'read_count': disk_io.read_count,
                    'write_count': disk_io.write_count
                }
            
        except Exception as e:
            self.logger.error(f"Error getting disk info: {e}")
            disk_info['error'] = str(e)
        
        return disk_info
    
    def get_network_info(self):
        """Get network interface information."""
        network_info = {}
        
        try:
            # Network I/O statistics
            net_io = psutil.net_io_counters(pernic=True)
            network_info['interfaces'] = {}
            
            for interface, stats in net_io.items():
                network_info['interfaces'][interface] = {
                    'bytes_sent': stats.bytes_sent,
                    'bytes_recv': stats.bytes_recv,
                    'packets_sent': stats.packets_sent,
                    'packets_recv': stats.packets_recv,
                    'errors_in': stats.errin,
                    'errors_out': stats.errout,
                    'drops_in': stats.dropin,
                    'drops_out': stats.dropout
                }
            
            # Network addresses
            addrs = psutil.net_if_addrs()
            for interface, addr_list in addrs.items():
                if interface in network_info['interfaces']:
                    network_info['interfaces'][interface]['addresses'] = []
                    for addr in addr_list:
                        network_info['interfaces'][interface]['addresses'].append({
                            'family': str(addr.family),
                            'address': addr.address,
                            'netmask': addr.netmask,
                            'broadcast': addr.broadcast
                        })
            
        except Exception as e:
            self.logger.error(f"Error getting network info: {e}")
            network_info['error'] = str(e)
        
        return network_info
    
    def get_uptime_info(self):
        """Get system uptime information."""
        uptime_info = {}
        
        try:
            boot_timestamp = datetime.fromtimestamp(self.boot_time)
            current_time = datetime.now()
            uptime_delta = current_time - boot_timestamp
            
            uptime_info['boot_time'] = boot_timestamp.isoformat()
            uptime_info['current_time'] = current_time.isoformat()
            uptime_info['uptime_seconds'] = uptime_delta.total_seconds()
            uptime_info['uptime_formatted'] = self._format_uptime(uptime_delta)
            
        except Exception as e:
            self.logger.error(f"Error getting uptime info: {e}")
            uptime_info['error'] = str(e)
        
        return uptime_info
    
    def get_process_info(self):
        """Get running process information."""
        process_info = {}
        
        try:
            # Process count
            process_info['total_processes'] = len(psutil.pids())
            
            # Top processes by CPU usage
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # Sort by CPU usage and get top 5
            top_cpu = sorted(processes, key=lambda x: x['cpu_percent'] or 0, reverse=True)[:5]
            process_info['top_cpu'] = top_cpu
            
            # Sort by memory usage and get top 5
            top_memory = sorted(processes, key=lambda x: x['memory_percent'] or 0, reverse=True)[:5]
            process_info['top_memory'] = top_memory
            
        except Exception as e:
            self.logger.error(f"Error getting process info: {e}")
            process_info['error'] = str(e)
        
        return process_info
    
    def _get_cpu_temperature(self):
        """Get CPU temperature for Raspberry Pi."""
        try:
            # Try reading from thermal zone (standard Linux method)
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp_str = f.read().strip()
                return float(temp_str) / 1000.0
        except:
            try:
                # Try vcgencmd (Raspberry Pi specific)
                result = subprocess.run(['vcgencmd', 'measure_temp'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    temp_str = result.stdout.strip()
                    # Extract temperature from "temp=XX.X'C"
                    if 'temp=' in temp_str:
                        temp_value = temp_str.split('=')[1].replace("'C", "")
                        return float(temp_value)
            except:
                pass
        
        return None
    
    def _format_uptime(self, uptime_delta):
        """Format uptime delta into human-readable string."""
        days = uptime_delta.days
        hours, remainder = divmod(uptime_delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if seconds > 0 or not parts:
            parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
        
        return ", ".join(parts)
    
    def get_system_summary(self):
        """Get a comprehensive system information summary."""
        summary = {
            'timestamp': datetime.now().isoformat(),
            'cpu': self.get_cpu_info(),
            'memory': self.get_memory_info(),
            'disk': self.get_disk_info(),
            'network': self.get_network_info(),
            'uptime': self.get_uptime_info(),
            'processes': self.get_process_info()
        }
        
        return summary
    
    def get_lightweight_summary(self):
        """Get a lightweight system summary for frequent updates."""
        try:
            summary = {
                'timestamp': datetime.now().isoformat(),
                'cpu_usage': psutil.cpu_percent(interval=0.1),
                'cpu_temp': self._get_cpu_temperature(),
                'memory_percent': psutil.virtual_memory().percent,
                'uptime_seconds': (datetime.now() - datetime.fromtimestamp(self.boot_time)).total_seconds()
            }
            
            return summary
        except Exception as e:
            self.logger.error(f"Error getting lightweight summary: {e}")
            return {'error': str(e), 'timestamp': datetime.now().isoformat()}