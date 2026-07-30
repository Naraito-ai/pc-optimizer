"""
Unit tests for PC Optimizer (Mocks only - zero system mutation).
"""

import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock, mock_open

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import optimizer

class TestPCOptimizer(unittest.TestCase):

    def test_version_constant(self):
        self.assertEqual(optimizer.VERSION, "2.0.0")

    @patch("psutil.virtual_memory")
    @patch("psutil.disk_usage")
    def test_calculate_health_score_good(self, mock_disk, mock_ram):
        mock_ram.return_value.percent = 40.0
        mock_disk.return_value.free = 50 * (1024 ** 3)
        score, status, issues = optimizer.calculate_health_score()
        self.assertGreaterEqual(score, 70)
        self.assertIn(status, ["Excellent", "Good"])

    @patch("os.path.exists", return_value=False)
    def test_load_state_default(self, mock_exists):
        state = optimizer.load_state()
        self.assertEqual(state["last_run"], "Never")
        self.assertIn("startup_backups", state)
        self.assertIsInstance(state["startup_backups"], list)

    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    def test_save_state(self, mock_file, mock_mkdir):
        data = {"last_run": "Today", "startup_backups": []}
        optimizer.save_state(data)
        mock_mkdir.assert_called_once()
        mock_file.assert_called_once()

    @patch("optimizer.get_cleanup_targets", return_value=[r"C:\Windows\Temp"])
    @patch("os.walk")
    @patch("os.path.islink", return_value=False)
    @patch("os.path.getsize", return_value=1024 * 1024)
    def test_estimate_cleanup_size(self, mock_getsize, mock_islink, mock_walk, mock_targets):
        mock_walk.return_value = [(r"C:\Windows\Temp", [], ["test.tmp"])]
        plan = optimizer.estimate_cleanup_size()
        self.assertEqual(plan.estimated_files, 1)
        self.assertEqual(plan.estimated_bytes, 1024 * 1024)

    @patch("subprocess.run")
    @patch("optimizer.is_task_scheduled", return_value=False)
    def test_toggle_weekly_schedule_create(self, mock_is_sched, mock_subproc):
        mock_subproc.return_value.returncode = 0
        res = optimizer.toggle_weekly_schedule_log(logger=lambda msg: None)
        self.assertTrue(res)
        mock_subproc.assert_called_once()
        args, kwargs = mock_subproc.call_args
        cmd_list = args[0]
        self.assertEqual(cmd_list[0], "schtasks")
        self.assertEqual(cmd_list[1], "/create")
        self.assertIn("/tn", cmd_list)
        self.assertIn("PCOptimizerWeekly", cmd_list)

    @patch("subprocess.run")
    def test_restore_normal_mode_log(self, mock_subproc):
        mock_subproc.return_value.returncode = 0
        with patch("winreg.CreateKey"), patch("winreg.OpenKey"), patch("winreg.SetValueEx"), patch("optimizer.save_state"):
            optimizer.restore_normal_mode_log(logger=lambda msg: None)
            self.assertTrue(mock_subproc.called)

if __name__ == "__main__":
    unittest.main()
