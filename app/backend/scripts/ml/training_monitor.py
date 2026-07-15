#!/usr/bin/env python3
"""
Real-time Training Monitor for TradePulse.AI Enterprise
Monitor training progress without interrupting the process
"""

import time
import os
import sys
import psutil
from datetime import datetime, timedelta
from pathlib import Path
import re

class TrainingMonitor:
    """Real-time training progress monitor"""
    
    def __init__(self, log_file="training_output.log", process_name="enterprise_model_retrainer"):
        self.log_file = Path(log_file)
        self.process_name = process_name
        self.training_stages = {
            "Layer 1": {"started": False, "completed": False, "accuracy": None},
            "Layer 2 LSTM 1h": {"started": False, "completed": False},
            "Layer 2 LSTM 4h": {"started": False, "completed": False},
            "Layer 2 LSTM 24h": {"started": False, "completed": False},
            "Layer 3": {"started": False, "completed": False, "accuracy": None},
            "Layer 4": {"started": False, "completed": False, "accuracy": None},
            "Layer 5": {"started": False, "completed": False, "r2": None},
            "Layer 6": {"started": False, "completed": False, "r2": None},
        }
        self.start_time = None
        self.last_update = None
        
    def get_process_info(self):
        """Get training process information"""
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_percent', 'create_time']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline and any(self.process_name in cmd for cmd in cmdline):
                    return {
                        'pid': proc.info['pid'],
                        'cpu_percent': proc.info['cpu_percent'],
                        'memory_percent': proc.info['memory_percent'],
                        'runtime': time.time() - proc.info['create_time'],
                        'status': 'Running'
                    }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None
    
    def parse_logs(self):
        """Parse training logs for progress"""
        if not self.log_file.exists():
            return
            
        try:
            with open(self.log_file, 'r') as f:
                content = f.read()
                
            # Find start time
            start_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ - INFO - 🚀 Starting Enterprise 6-Layer Training', content)
            if start_match and not self.start_time:
                self.start_time = datetime.strptime(start_match.group(1), '%Y-%m-%d %H:%M:%S')
            
            # Check Layer 1
            if "🎯 Training Layer 1: Market Regime Detection" in content:
                self.training_stages["Layer 1"]["started"] = True
            
            layer1_match = re.search(r'✅ Layer 1 trained - Accuracy: ([\d.]+)', content)
            if layer1_match:
                self.training_stages["Layer 1"]["completed"] = True
                self.training_stages["Layer 1"]["accuracy"] = float(layer1_match.group(1))
            
            # Check Layer 2 LSTM
            if "🤖 Training Layer 2: LSTM Ensemble" in content:
                self.training_stages["Layer 2 LSTM 1h"]["started"] = True
                self.training_stages["Layer 2 LSTM 4h"]["started"] = True
                self.training_stages["Layer 2 LSTM 24h"]["started"] = True
            
            if "✅ LSTM 1h model trained" in content:
                self.training_stages["Layer 2 LSTM 1h"]["completed"] = True
                
            if "✅ LSTM 4h model trained" in content:
                self.training_stages["Layer 2 LSTM 4h"]["completed"] = True
                
            if "✅ LSTM 24h model trained" in content:
                self.training_stages["Layer 2 LSTM 24h"]["completed"] = True
            
            # Check remaining layers
            for layer_num in [3, 4, 5, 6]:
                if f"Training Layer {layer_num}" in content:
                    self.training_stages[f"Layer {layer_num}"]["started"] = True
                    
                layer_match = re.search(f'✅ Layer {layer_num} trained - (Accuracy|R²): ([\\d.]+)', content)
                if layer_match:
                    self.training_stages[f"Layer {layer_num}"]["completed"] = True
                    metric_name = "accuracy" if layer_match.group(1) == "Accuracy" else "r2"
                    self.training_stages[f"Layer {layer_num}"][metric_name] = float(layer_match.group(2))
            
            # Find last update time
            last_log_match = re.findall(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+', content)
            if last_log_match:
                self.last_update = datetime.strptime(last_log_match[-1], '%Y-%m-%d %H:%M:%S')
                
        except Exception as e:
            print(f"Error parsing logs: {e}")
    
    def calculate_progress(self):
        """Calculate overall training progress"""
        total_stages = len(self.training_stages)
        completed_stages = sum(1 for stage in self.training_stages.values() if stage["completed"])
        started_stages = sum(1 for stage in self.training_stages.values() if stage["started"])
        
        progress_percent = (completed_stages / total_stages) * 100
        return progress_percent, completed_stages, total_stages, started_stages
    
    def create_progress_bar(self, progress_percent, width=50):
        """Create ASCII progress bar"""
        filled = int(width * progress_percent / 100)
        bar = "█" * filled + "░" * (width - filled)
        return f"[{bar}] {progress_percent:.1f}%"
    
    def display_status(self):
        """Display current training status"""
        os.system('clear')  # Clear screen
        
        print("🚀 TradePulse.AI Enterprise Training Monitor")
        print("=" * 60)
        
        # Process info
        proc_info = self.get_process_info()
        if proc_info:
            runtime_str = str(timedelta(seconds=int(proc_info['runtime'])))
            print(f"📊 Process Status: {proc_info['status']} (PID: {proc_info['pid']})")
            print(f"⏱️  Runtime: {runtime_str}")
            print(f"💾 Memory: {proc_info['memory_percent']:.1f}%")
            print(f"🔥 CPU: {proc_info['cpu_percent']:.1f}%")
        else:
            print("❌ Training process not found")
            return
        
        print()
        
        # Overall progress
        progress_percent, completed, total, started = self.calculate_progress()
        progress_bar = self.create_progress_bar(progress_percent)
        
        print(f"📈 Overall Progress: {completed}/{total} layers completed")
        print(f"{progress_bar}")
        print()
        
        # Detailed status
        print("📋 Layer Details:")
        print("-" * 60)
        
        for stage_name, stage_info in self.training_stages.items():
            if stage_info["completed"]:
                status = "✅ COMPLETED"
                if "accuracy" in stage_info and stage_info["accuracy"]:
                    status += f" (Accuracy: {stage_info['accuracy']:.4f})"
                elif "r2" in stage_info and stage_info["r2"]:
                    status += f" (R²: {stage_info['r2']:.4f})"
            elif stage_info["started"]:
                status = "🔄 IN PROGRESS"
            else:
                status = "⏳ PENDING"
            
            print(f"  {stage_name:<20} {status}")
        
        print()
        
        # Time info
        if self.start_time:
            elapsed = datetime.now() - self.start_time
            print(f"🕐 Training started: {self.start_time.strftime('%H:%M:%S')}")
            print(f"⏳ Elapsed time: {str(elapsed).split('.')[0]}")
        
        if self.last_update:
            time_since_update = datetime.now() - self.last_update
            print(f"📝 Last update: {self.last_update.strftime('%H:%M:%S')} ({time_since_update.total_seconds():.0f}s ago)")
        
        print()
        print("💡 Press Ctrl+C to stop monitoring (training will continue)")
        print("🔄 Refreshing every 10 minutes...")
    
    def monitor(self, refresh_interval=600):  # 600 seconds = 10 minutes
        """Start monitoring loop"""
        try:
            while True:
                self.parse_logs()
                self.display_status()
                
                # Check if training is complete
                progress_percent, completed, total, started = self.calculate_progress()
                if completed == total:
                    print("\n🎉 Training Complete! All layers finished.")
                    break
                    
                # Check if process is still running
                proc_info = self.get_process_info()
                if not proc_info:
                    print("\n❌ Training process stopped.")
                    break
                
                time.sleep(refresh_interval)
                
        except KeyboardInterrupt:
            print("\n👋 Monitoring stopped. Training continues in background.")

def main():
    monitor = TrainingMonitor()
    monitor.monitor()

if __name__ == "__main__":
    main() 