"""
Comprehensive Unit Tests for PC Optimizer (Mocks only - zero system mutation).
"""

import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock, mock_open

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import optimizer

class TestPCOptimizer(unittest.TestCase):

    def test_version_constant(self):
        self.assertEqual(optimizer.VERSION, "2.0.1")

    @patch("psutil.virtual_memory")
    @patch("psutil.disk_usage")
    def test_calculate_health_score_good(self, mock_disk, mock_ram):
        optimizer.invalidate_health_score_cache()
        mock_ram.return_value.percent = 40.0
        mock_disk.return_value.free = 50 * (1024 ** 3)
        score, status, issues = optimizer.calculate_health_score()
        self.assertGreaterEqual(score, 70)
        self.assertIn(status, ["Excellent", "Good"])

    @patch("os.path.exists", return_value=False)
    def test_load_state_missing_default(self, mock_exists):
        state = optimizer.load_state()
        self.assertEqual(state["last_run"], "Never")
        self.assertIn("modified_settings", state)
        self.assertIn("startup_entries", state["modified_settings"])

    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data="INVALID JSON {{{")
    def test_load_state_corrupted_fallback(self, mock_file, mock_exists):
        state = optimizer.load_state()
        self.assertEqual(state["last_run"], "Never")
        self.assertIn("modified_settings", state)

    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    def test_save_state(self, mock_file, mock_mkdir):
        data = optimizer.default_state_structure()
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

    @patch("optimizer.get_cleanup_targets", return_value=[r"C:\Windows\Temp"])
    @patch("os.walk")
    @patch("os.path.islink", return_value=False)
    @patch("os.path.getsize", return_value=512)
    @patch("os.remove")
    def test_clean_temp_files_result_metrics(self, mock_remove, mock_getsize, mock_islink, mock_walk, mock_targets):
        mock_walk.return_value = [(r"C:\Windows\Temp", [], ["a.tmp", "b.tmp"])]
        res = optimizer.clean_temp_files_log(logger=lambda msg: None, advanced_mode=False)
        self.assertEqual(res.files_deleted_count, 2)
        self.assertEqual(res.actual_reclaimed_bytes, 1024)

    @patch("subprocess.run")
    @patch("optimizer.is_task_scheduled", return_value=False)
    def test_toggle_weekly_schedule_create(self, mock_is_sched, mock_subproc):
        mock_subproc.return_value.returncode = 0
        with patch("optimizer.load_state", return_value=optimizer.default_state_structure()), \
             patch("optimizer.save_state"):
            res = optimizer.toggle_weekly_schedule_log(logger=lambda msg: None)
            self.assertTrue(res)
            mock_subproc.assert_called_once()
            cmd_list = mock_subproc.call_args[0][0]
            self.assertEqual(cmd_list[0], "schtasks")
            self.assertEqual(cmd_list[1], "/create")
            self.assertIn("PCOptimizerWeekly", cmd_list)

    @patch("subprocess.run")
    def test_restore_normal_mode_ownership_filtering(self, mock_subproc):
        mock_subproc.return_value.returncode = 0
        test_state = optimizer.default_state_structure()
        
        # Telemetry modified_by_optimizer is FALSE -> restore should NOT run sc config for Telemetry
        test_state["modified_settings"]["telemetry_service"]["modified_by_optimizer"] = False
        test_state["modified_settings"]["power_plan"]["modified_by_optimizer"] = True
        test_state["modified_settings"]["power_plan"]["original_scheme_guid"] = "SCHEME_BALANCED"

        with patch("optimizer.load_state", return_value=test_state), \
             patch("optimizer.save_state"), \
             patch("winreg.CreateKey"), patch("winreg.OpenKey"), patch("winreg.SetValueEx"):
            optimizer.restore_normal_mode_log(logger=lambda msg: None)
            
            # Check that sc config for DiagTrack was NOT called because modified_by_optimizer was False
            calls = [c[0][0] for c in mock_subproc.call_args_list if len(c[0]) > 0 and isinstance(c[0][0], list)]
            diagtrack_calls = [c for c in calls if "DiagTrack" in c]
            self.assertEqual(len(diagtrack_calls), 0)

if __name__ == "__main__":
    unittest.main()
