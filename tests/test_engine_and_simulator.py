from unittest.mock import MagicMock, patch

from config import AppConfig
from engine import EngineState, UnIdleEngine
from simulator import ActivitySimulator


def test_engine_paused_and_monitoring_transitions():
    detector = MagicMock()
    detector.get_idle_seconds.return_value = 5.0
    simulator = MagicMock()

    with patch("engine.IdleDetector", return_value=detector), patch(
        "engine.ActivitySimulator", return_value=simulator
    ):
        eng = UnIdleEngine(AppConfig(enabled=False, idle_threshold_sec=10.0, pulse_interval_sec=5.0))
        assert eng.state == EngineState.PAUSED

        eng.start()
        try:
            import time
            time.sleep(0.35)
            assert eng.state == EngineState.PAUSED

            eng.update_config(AppConfig(enabled=True, idle_threshold_sec=10.0, pulse_interval_sec=5.0))
            time.sleep(0.35)
            assert eng.state == EngineState.MONITORING

            detector.get_idle_seconds.return_value = 15.0
            time.sleep(0.35)
            assert eng.state == EngineState.SIMULATING
            assert simulator.pulse.call_count >= 1
        finally:
            eng.stop()

    detector.stop.assert_called_once()
    simulator.cleanup.assert_called_once()


def test_simulator_caffeinate_cleanup():
    proc = MagicMock()
    with patch("simulator.platform.system", return_value="Darwin"), patch(
        "simulator.subprocess.Popen", return_value=proc
    ) as popen_mock:
        sim = ActivitySimulator()
        sim.set_awake_assertion(True)
        popen_mock.assert_called_once()
        assert sim._awake_asserted is True

        sim.cleanup()
        proc.terminate.assert_called_once()
        assert sim._awake_asserted is False
