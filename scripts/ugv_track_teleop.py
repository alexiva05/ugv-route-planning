"""UGV track controller: one active instance and calibrated low-speed profile.

Run from Isaac Sim's Script Editor after opening
ugv_tracks_stage3_mass50_2026-10-09.usd.
I/K: forward/reverse; J/L: left/right turn. Run again to replace the controller.
"""

import builtins
import gc
import time

import carb.input
import omni.appwindow
import omni.kit.app
import omni.timeline
import omni.usd
from pxr import Gf


# Script Editor tabs may have separate globals. Find earlier controller instances
# and unsubscribe them before creating the new controller.
_previous_controllers = []
_registered_controller = getattr(builtins, "_vkr_ugv_track_controller", None)
if _registered_controller is not None:
    _previous_controllers.append(_registered_controller)
for _candidate in gc.get_objects():
    if type(_candidate).__name__ != "UGVTrackKeyboard":
        continue
    _attrs = getattr(_candidate, "track_attrs", None)
    if not isinstance(_attrs, dict) or set(_attrs) != {"PosX", "NegX"}:
        continue
    if all(_candidate is not item for item in _previous_controllers):
        _previous_controllers.append(_candidate)
for _controller in _previous_controllers:
    _controller.close()
if _previous_controllers:
    print(f"Closed {len(_previous_controllers)} previous UGV track controller(s)")
builtins._vkr_ugv_track_controller = None


class UGVTrackKeyboard:
    def __init__(self):
        self.stage = omni.usd.get_context().get_stage()
        self.timeline = omni.timeline.get_timeline_interface()
        self.input = carb.input.acquire_input_interface()
        self.keyboard = omni.appwindow.get_default_app_window().get_keyboard()
        self.track_attrs = {}
        for side in ("PosX", "NegX"):
            path = f"/World/UGV/Colliders/TrackCollider_{side}"
            prim = self.stage.GetPrimAtPath(path)
            if not prim.IsValid() or not prim.IsActive():
                raise RuntimeError(f"Active track body is missing: {path}")
            attr = prim.GetAttribute("physxSurfaceVelocity:surfaceVelocity")
            if not attr.IsValid():
                raise RuntimeError(f"Surface velocity is missing: {path}")
            self.track_attrs[side] = attr
        self.forward = 0.0
        self.yaw = 0.0
        self.last_time = time.monotonic()
        self.subscription = (
            omni.kit.app.get_app()
            .get_update_event_stream()
            .create_subscription_to_pop(self.update)
        )
        self.set_tracks(0.0, 0.0)

    def pressed(self, key):
        return int(self.input.get_keyboard_value(self.keyboard, key) > 0.5)

    def set_tracks(self, pos_x_speed, neg_x_speed):
        # The visual front is +Y. Positive surface velocity drives the robot forward.
        self.track_attrs["PosX"].Set(Gf.Vec3f(0.0, pos_x_speed, 0.0))
        self.track_attrs["NegX"].Set(Gf.Vec3f(0.0, neg_x_speed, 0.0))

    def update(self, event):
        if omni.usd.get_context().get_stage() != self.stage:
            self.close()
            return
        now = time.monotonic()
        dt = min(now - self.last_time, 0.05)
        self.last_time = now
        if not self.timeline.is_playing():
            self.forward = 0.0
            self.yaw = 0.0
            self.set_tracks(0.0, 0.0)
            return

        keys = carb.input.KeyboardInput
        # Commands calibrated on the 50 kg stage-3 scene on 2026-10-09.
        target_forward = 0.225 * (self.pressed(keys.I) - self.pressed(keys.K))
        # J turns toward the visual left; L turns toward the visual right.
        target_yaw = 0.375 * (self.pressed(keys.L) - self.pressed(keys.J))

        def approach(current, target, step):
            return current + max(-step, min(step, target - current))

        self.forward = approach(self.forward, target_forward, 0.25 * dt)
        self.yaw = approach(self.yaw, target_yaw, 0.5 * dt)
        half_spacing = 0.40
        self.set_tracks(
            self.forward - self.yaw * half_spacing,
            self.forward + self.yaw * half_spacing,
        )

    def close(self):
        self.subscription = None
        if omni.usd.get_context().get_stage() == self.stage:
            self.set_tracks(0.0, 0.0)


ugv_track_controls = UGVTrackKeyboard()
builtins._vkr_ugv_track_controller = ugv_track_controls
print("UGV tracks: I/K forward/reverse, J/L left/right (stage-3 profile).")
