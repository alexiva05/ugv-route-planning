"""Log UGV pose, commanded track speeds, and elapsed physics time to CSV.

Run in Isaac Sim Script Editor after opening the stage-2 or stage-3 scene. The logger
records while Play is active and leaves the USD stage unchanged. Run this
script again to close the previous log and start a new one.
"""

import csv
import math
import time
from datetime import datetime
from pathlib import Path

import omni.kit.app
import omni.physx
import omni.timeline
import omni.usd
from pxr import Gf, Usd, UsdGeom


if "ugv_pose_logger" in globals():
    ugv_pose_logger.close()


class UGVPoseLogger:
    def __init__(self):
        self.stage = omni.usd.get_context().get_stage()
        if self.stage is None:
            raise RuntimeError("No USD stage is open")
        self.ugv = self.stage.GetPrimAtPath("/World/UGV")
        if not self.ugv.IsValid():
            raise RuntimeError("/World/UGV is missing")
        self.track_attrs = {}
        for side in ("PosX", "NegX"):
            path = f"/World/UGV/Colliders/TrackCollider_{side}"
            prim = self.stage.GetPrimAtPath(path)
            attr = prim.GetAttribute("physxSurfaceVelocity:surfaceVelocity")
            if not attr.IsValid():
                raise RuntimeError(f"Track surface velocity is missing: {path}")
            self.track_attrs[side] = attr

        self.timeline = omni.timeline.get_timeline_interface()
        output_dir = Path("/workspace/research-data/runs")
        output_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self.path = output_dir / f"ugv_track_probe_simtime_{stamp}.csv"
        self.file = self.path.open("w", newline="", encoding="utf-8")
        self.writer = csv.writer(self.file)
        self.writer.writerow(
            ["wall_s", "sim_s", "x_m", "y_m", "z_m", "heading_rad",
             "pos_x_surface_y_mps", "neg_x_surface_y_mps"]
        )
        self.file.flush()
        self.started = time.monotonic()
        self.sim_elapsed = 0.0
        self.last_sample_sim = -1.0
        self.physics_subscription = (
            omni.physx.get_physx_interface()
            .subscribe_physics_step_events(self.on_physics_step)
        )
        self.subscription = (
            omni.kit.app.get_app()
            .get_update_event_stream()
            .create_subscription_to_pop(self.update)
        )
        print(f"UGV pose log: {self.path}")

    def on_physics_step(self, dt):
        if self.timeline.is_playing():
            self.sim_elapsed += dt

    def update(self, event):
        if omni.usd.get_context().get_stage() != self.stage:
            self.close()
            return
        if not self.timeline.is_playing():
            return
        elapsed = time.monotonic() - self.started
        if self.sim_elapsed - self.last_sample_sim < 0.1:
            return
        self.last_sample_sim = self.sim_elapsed

        matrix = UsdGeom.XformCache(Usd.TimeCode.Default()).GetLocalToWorldTransform(self.ugv)
        position = matrix.ExtractTranslation()
        forward = matrix.TransformDir(Gf.Vec3d(0.0, -1.0, 0.0))
        heading = math.atan2(forward[0], -forward[1])
        sim_time = self.sim_elapsed
        pos_x = self.track_attrs["PosX"].Get()
        neg_x = self.track_attrs["NegX"].Get()
        self.writer.writerow(
            [elapsed, sim_time, position[0], position[1], position[2],
             heading, pos_x[1], neg_x[1]]
        )
        self.file.flush()

    def close(self):
        self.subscription = None
        self.physics_subscription = None
        if not self.file.closed:
            self.file.close()
            print(f"UGV pose log closed: {self.path}")


ugv_pose_logger = UGVPoseLogger()
