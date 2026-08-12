from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from simulation.jetracer.nvidia_racecar import NvidiaRacecar

@dataclass
class DriveCommand:
    steering: float = 0.0
    throttle: float = 0.0
    description: str = ''


@dataclass
class PerceptionResult:
    lane_detected: bool = False
    lane_offset: float | None = None
    sign_type: str | None = None
    sign_data: dict[str, Any] | None = None


class DrivePolicy(ABC):
    """Trừu tượng cho các chiến lược quyết định lệnh lái."""

    @abstractmethod
    def get_command(self, frame: Any, perception: PerceptionResult | None = None) -> DriveCommand:
        raise NotImplementedError


class ConstantDrivePolicy(DrivePolicy):
    def __init__(self, steering: float = 0.2, throttle: float = 0.2):
        self._steering = steering
        self._throttle = throttle

    def get_command(self, frame: Any, perception: PerceptionResult | None = None) -> DriveCommand:
        return DriveCommand(
            steering=self._steering,
            throttle=self._throttle,
            description='constant speed policy',
        )


class LaneFollowPolicy(DrivePolicy):
    def get_command(self, frame: Any, perception: PerceptionResult | None = None) -> DriveCommand:
        # TODO: thay bằng logic xử lý ảnh bám làn.
        if perception and perception.lane_detected and perception.lane_offset is not None:
            steering = max(min(-perception.lane_offset, 1.0), -1.0)
            throttle = 0.2
            return DriveCommand(
                steering=steering,
                throttle=throttle,
                description='lane following',
            )
        return DriveCommand(description='no lane data, stop')


class SignAwarePolicy(DrivePolicy):
    def get_command(self, frame: Any, perception: PerceptionResult | None = None) -> DriveCommand:
        # TODO: dùng perception.sign_type để điều chỉnh hành vi.
        if perception and perception.sign_type == 'STOP':
            return DriveCommand(steering=0.0, throttle=0.0, description='stop sign')
        if perception and perception.sign_type == 'TURN_LEFT':
            return DriveCommand(steering=-0.5, throttle=0.1, description='turn left')
        return DriveCommand(description='no sign action')


class HybridDrivePolicy(DrivePolicy):
    def __init__(self, lane_policy: DrivePolicy | None = None, sign_policy: DrivePolicy | None = None):
        self.lane_policy = lane_policy or LaneFollowPolicy()
        self.sign_policy = sign_policy or SignAwarePolicy()

    def get_command(self, frame: Any, perception: PerceptionResult | None = None) -> DriveCommand:
        sign_command = self.sign_policy.get_command(frame, perception)
        if sign_command.throttle == 0.0 and sign_command.description:
            return sign_command
        lane_command = self.lane_policy.get_command(frame, perception)
        if lane_command.throttle != 0.0:
            return lane_command
        return sign_command


class RacecarDriver:
    def __init__(self, car: NvidiaRacecar, policy: DrivePolicy | None = None):
        self.car = car
        self.policy = policy or ConstantDrivePolicy()

    def apply(self, frame: Any, perception: PerceptionResult | None = None) -> DriveCommand:
        command = self.policy.get_command(frame, perception)
        self.car.steering = command.steering
        self.car.throttle = command.throttle
        return command

    def stop(self) -> None:
        self.car.steering = 0.0
        self.car.throttle = 0.0
