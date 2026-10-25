import os
from backend.worker.main import next_idle_sleep


def test_next_idle_sleep_doubles_until_cap():
    current = 3.0
    max_idle = 300.0

    current = next_idle_sleep(current, max_idle)
    assert current == 6.0

    current = next_idle_sleep(current, max_idle)
    assert current == 12.0

    current = next_idle_sleep(current, max_idle)
    assert current == 24.0

    current = next_idle_sleep(current, max_idle)
    assert current == 48.0

    current = next_idle_sleep(current, max_idle)
    assert current == 96.0

    current = next_idle_sleep(current, max_idle)
    assert current == 192.0

    current = next_idle_sleep(current, max_idle)
    assert current == 300.0  # capped at 300

    current = next_idle_sleep(current, max_idle)
    assert current == 300.0  # stays capped at 300


def test_next_idle_sleep_custom_cap():
    assert next_idle_sleep(10.0, max_idle=15.0) == 15.0
    assert next_idle_sleep(2.0, max_idle=10.0) == 4.0
