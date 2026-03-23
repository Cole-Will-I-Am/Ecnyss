#!/usr/bin/env python3
"""Scheduler for Ecnyss - runs evolution cycles every 7 minutes with resilience.

Provides the perpetual execution loop that drives autonomous evolution,
integrating recovery mechanisms to ensure continuity through failures.
"""
import time
import sys
import signal
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add Ecnyss to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from main import main as run_evolution_cycle
from recovery_engine import RecoveryEngine
from health_monitor import HealthMonitor


class EcnyssScheduler:
    """Manages continuous execution of evolution cycles with 7-minute intervals."""
    
    INTERVAL_SECONDS = 420  # 7 minutes
    
    def __init__(self, max_consecutive_failures: int = 3):
        self.running = False
        self.cycle_count = 0
        self.consecutive_failures = 0
        self.max_consecutive_failures = max_consecutive_failures
        self.recovery = RecoveryEngine()
        self.health = HealthMonitor()
        self.start_time: Optional[datetime] = None
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler('/root/Ecnyss/scheduler.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('scheduler')
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    def _wait_interval(self):
        """Wait for the configured interval, checking for shutdown."""
        elapsed = 0
        while self.running and elapsed < self.INTERVAL_SECONDS:
            time.sleep(1)
            elapsed += 1
    
    def _check_health(self) -> bool:
        """Check if system is healthy enough to run a cycle."""
        try:
            status = self.health.check_system_health()
            if status.get('status') != 'healthy':
                self.logger.warning(f"System unhealthy: {status}")
                return False
            return True
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return True  # Proceed anyway if health check itself fails
    
    def _run_cycle(self) -> bool:
        """Run a single evolution cycle with error recovery."""
        try:
            self.logger.info(f"Starting evolution cycle {self.cycle_count + 1}")
            
            # Run the cycle
            result = run_evolution_cycle()
            
            self.cycle_count += 1
            self.consecutive_failures = 0
            
            self.logger.info(f"Cycle {self.cycle_count} completed: {result}")
            return True
            
        except Exception as e:
            self.logger.error(f"Cycle failed with exception: {e}")
            self.consecutive_failures += 1
            
            # Attempt recovery
            try:
                recovery_result = self.recovery.attempt_recovery(e, self.cycle_count)
                self.logger.info(f"Recovery result: {recovery_result}")
            except Exception as recovery_error:
                self.logger.error(f"Recovery failed: {recovery_error}")
            
            return False
    
    def run(self):
        """Main execution loop - runs until interrupted."""
        self.logger.info("=" * 60)
        self.logger.info("Ecnyss Scheduler Starting")
        self.logger.info(f"Interval: {self.INTERVAL_SECONDS}s (7 minutes)")
        self.logger.info(f"Max consecutive failures: {self.max_consecutive_failures}")
        self.logger.info("=" * 60)
        
        self.start_time = datetime.utcnow()
        self.running = True
        
        while self.running:
            # Check health before running
            if not self._check_health():
                self.logger.warning("Health check failed, skipping cycle")
                self._wait_interval()
                continue
            
            # Run the cycle
            success = self._run_cycle()
            
            # Check for too many failures
            if self.consecutive_failures >= self.max_consecutive_failures:
                self.logger.error(f"Max consecutive failures ({self.max_consecutive_failures}) reached")
                self.logger.info("Entering extended cooldown (60 minutes)")
                time.sleep(3600)
                self.consecutive_failures = 0
                continue
            
            # Wait for next cycle
            if self.running:
                self.logger.info(f"Waiting {self.INTERVAL_SECONDS}s until next cycle...")
                self._wait_interval()
        
        # Shutdown
        uptime = datetime.utcnow() - self.start_time if self.start_time else None
        self.logger.info(f"Scheduler stopped. Total cycles: {self.cycle_count}. Uptime: {uptime}")
    
    def get_stats(self) -> dict:
        """Get scheduler statistics."""
        return {
            'cycles_completed': self.cycle_count,
            'consecutive_failures': self.consecutive_failures,
            'running': self.running,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'uptime_seconds': (datetime.utcnow() - self.start_time).total_seconds() if self.start_time else 0
        }


def main():
    """Entry point for scheduler."""
    scheduler = EcnyssScheduler()
    
    # Daemonize (optional, can be run with & or systemd)
    if len(sys.argv) > 1 and sys.argv[1] == '--daemon':
        try:
            import os
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError as e:
            sys.stderr.write(f"Fork failed: {e}\n")
            sys.exit(1)
    
    scheduler.run()


if __name__ == "__main__":
    main()
