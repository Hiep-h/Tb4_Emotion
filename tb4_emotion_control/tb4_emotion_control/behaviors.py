"""Robot trajectories for each emotion, as timed velocity segments (no ROS)."""

import math
from dataclasses import dataclass

# Hard limits so a bad parameter cannot make the robot move fast.
MAX_LINEAR = 0.25    # m/s
MAX_ANGULAR = 1.2    # rad/s


@dataclass(frozen=True)
class Segment:
    linear: float
    angular: float
    duration: float


@dataclass(frozen=True)
class BehaviorParams:
    curve_linear: float = 0.12     # m/s along the arc
    curve_angular: float = 0.5     # rad/s; arc radius = linear / angular = 0.24 m
    curve_duration: float = 4.0    # s; turns the robot by angular * duration = 2 rad
    back_speed: float = 0.10       # m/s
    back_duration: float = 1.5     # s; about 0.15 m
    forward_speed: float = 0.10    # m/s
    forward_duration: float = 1.5  # s; about 0.15 m
    spin_speed: float = 0.8        # rad/s
    spin_turns: float = 1.0


def validate(params):
    for name in ('curve_linear', 'back_speed', 'forward_speed'):
        if not 0.0 < getattr(params, name) <= MAX_LINEAR:
            raise ValueError(f'{name} phải trong (0, {MAX_LINEAR}] m/s')
    for name in ('curve_angular', 'spin_speed'):
        if not 0.0 < getattr(params, name) <= MAX_ANGULAR:
            raise ValueError(f'{name} phải trong (0, {MAX_ANGULAR}] rad/s')
    for name in ('curve_duration', 'back_duration', 'forward_duration', 'spin_turns'):
        if getattr(params, name) <= 0.0:
            raise ValueError(f'{name} phải dương')


def build_behaviors(params):
    """Map each emotion to its segments. Neutral is empty: it means stop."""
    validate(params)
    spin_time = 2.0 * math.pi * params.spin_turns / params.spin_speed
    return {
        'happy': [Segment(params.curve_linear, params.curve_angular, params.curve_duration)],
        'sad': [Segment(params.curve_linear, -params.curve_angular, params.curve_duration)],
        'neutral': [],
        'angry': [Segment(-params.back_speed, 0.0, params.back_duration)],
        'surprise': [Segment(0.0, params.spin_speed, spin_time)],
        'fear': [Segment(params.forward_speed, 0.0, params.forward_duration)],
    }


def total_duration(segments):
    return sum(s.duration for s in segments)


def velocity_at(segments, t):
    """(linear, angular) at time t seconds after the start, or None when finished."""
    elapsed = 0.0
    for seg in segments:
        if t < elapsed + seg.duration:
            return seg.linear, seg.angular
        elapsed += seg.duration
    return None
