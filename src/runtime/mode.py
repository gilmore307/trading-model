from __future__ import annotations

from enum import StrEnum


class RuntimeMode(StrEnum):
    DEVELOP = 'develop'
    TEST = 'test'
    TRADE = 'trade'
    REVIEW = 'review'
    CALIBRATE = 'calibrate'
    RESET = 'reset'
