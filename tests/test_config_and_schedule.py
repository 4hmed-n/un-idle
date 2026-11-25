from datetime import datetime
from pathlib import Path
import os
from unittest.mock import patch

from config import AppConfig, ScheduleConfig, load_config, save_config, DEFAULT_CONFIG_DIR
from engine import is_within_schedule


def test_config_normalization_and_roundtrip(tmp_path: Path):
    cfg_file = tmp_path / "config.json"
    cfg = AppConfig(
        enabled=True,
        mode="invalid_mode",
        idle_threshold_sec=1.0,
        pulse_interval_sec=2.0,
        jiggle_pixels=999,
        hide_from_capture=True,
        schedule=ScheduleConfig(enabled=True, start_time="09:00", end_time="17:00", days=[0, 2, 4]),
    )
    save_config(cfg, cfg_file)
    assert cfg_file.exists()

    loaded = load_config(cfg_file)
    assert loaded.mode == "micro-jiggle"
    assert loaded.idle_threshold_sec == 5.0
    assert loaded.pulse_interval_sec == 5.0
    assert loaded.jiggle_pixels == 25
    assert loaded.hide_from_capture is True
    assert loaded.schedule.days == [0, 2, 4]


def test_config_dir_env_override(tmp_path: Path, monkeypatch):
    """Test UN_IDLE_CONFIG_DIR environment variable override."""
    custom_dir = tmp_path / "custom-config"
    monkeypatch.setenv("UN_IDLE_CONFIG_DIR", str(custom_dir))
    
    # Need to reload config module to pick up new env var
    import importlib
    import config
    importlib.reload(config)
    
    cfg_file = config.DEFAULT_CONFIG_PATH
    assert config.DEFAULT_CONFIG_DIR == custom_dir
    
    cfg = AppConfig(enabled=True, mode="f15")
    config.save_config(cfg, cfg_file)
    assert cfg_file.exists()
    assert cfg_file.parent == custom_dir
    
    loaded = config.load_config(cfg_file)
    assert loaded.mode == "f15"


def test_corrupt_json_recovery(tmp_path: Path):
    """Test that corrupt JSON returns default config without crashing."""
    cfg_file = tmp_path / "corrupt.json"
    
    # Write malformed JSON
    cfg_file.write_text("{ this is not valid json }", encoding="utf-8")
    
    loaded = load_config(cfg_file)
    assert loaded.mode == "micro-jiggle"
    assert loaded.enabled is True
    assert loaded.idle_threshold_sec == 45.0
    

def test_missing_config_file_returns_default(tmp_path: Path):
    """Test that missing config file returns normalized default."""
    cfg_file = tmp_path / "nonexistent.json"
    
    loaded = load_config(cfg_file)
    assert loaded.mode == "micro-jiggle"
    assert loaded.enabled is True
    assert loaded.idle_threshold_sec >= 5.0


def test_partial_config_fills_defaults(tmp_path: Path):
    """Test that partial config JSON fills missing fields with defaults."""
    cfg_file = tmp_path / "partial.json"
    cfg_file.write_text('{"mode": "f15"}', encoding="utf-8")
    
    loaded = load_config(cfg_file)
    assert loaded.mode == "f15"
    assert loaded.enabled is True  # default
    assert loaded.idle_threshold_sec == 45.0  # default


def test_schedule_normal_and_overnight():
    mon_morning = datetime(2026, 11, 23, 10, 30)
    mon_evening = datetime(2026, 11, 23, 20, 00)

    daytime_cfg = AppConfig(
        schedule=ScheduleConfig(enabled=True, start_time="09:00", end_time="17:00", days=[0])
    )
    assert is_within_schedule(daytime_cfg, mon_morning) is True
    assert is_within_schedule(daytime_cfg, mon_evening) is False

    overnight_cfg = AppConfig(
        schedule=ScheduleConfig(enabled=True, start_time="22:00", end_time="06:00", days=[0])
    )
    assert is_within_schedule(overnight_cfg, mon_evening) is False
    assert is_within_schedule(overnight_cfg, datetime(2026, 11, 23, 23, 15)) is True
