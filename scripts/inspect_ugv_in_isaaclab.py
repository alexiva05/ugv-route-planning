"""Read-only check of the open stage-3 UGV scene from Isaac Lab's Script Editor."""

import math
from pathlib import Path

import isaaclab.sim as sim_utils
import omni.usd
from pxr import Usd, UsdGeom, UsdPhysics


EXPECTED_SCENE = "ugv_tracks_stage3_mass50_2026-10-09.usd"
ROOT = "/World/UGV"
TRACKS = {
    "PosX": (6.36, "/World/UGV/Joints/Track_PosX_Fixed"),
    "NegX": (6.36, "/World/UGV/Joints/Track_NegX_Fixed"),
}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def read_mass(prim):
    value = UsdPhysics.MassAPI(prim).GetMassAttr().Get()
    require(value is not None, f"No explicit mass: {prim.GetPath()}")
    return float(value)


def main():
    stage = omni.usd.get_context().get_stage()
    require(stage is not None, "No USD stage is open in Isaac Sim")
    lab_stage = sim_utils.get_current_stage()
    scene_path = stage.GetRootLayer().identifier
    require(Path(scene_path).name == EXPECTED_SCENE, f"Open the stage-3 scene first: {scene_path}")

    root = stage.GetPrimAtPath(ROOT)
    require(root.IsValid() and root.IsActive(), f"Missing active prim: {ROOT}")
    require(UsdPhysics.RigidBodyAPI(root).GetRigidBodyEnabledAttr().Get() is True, "UGV rigid body is disabled")
    body_mass = read_mass(root)
    require(math.isclose(body_mass, 37.28, abs_tol=0.01), f"Unexpected body mass: {body_mass}")
    require(stage.GetPrimAtPath("/World/PhysicsScene").IsValid(), "PhysicsScene is missing")

    total_mass = body_mass
    for side, (expected_mass, joint_path) in TRACKS.items():
        path = f"{ROOT}/Colliders/TrackCollider_{side}"
        track = stage.GetPrimAtPath(path)
        require(track.IsValid() and track.IsActive(), f"Missing active track: {path}")
        require(UsdPhysics.RigidBodyAPI(track).GetRigidBodyEnabledAttr().Get() is True, f"Rigid body disabled: {path}")
        require(UsdPhysics.CollisionAPI(track).GetCollisionEnabledAttr().Get() is True, f"Collision disabled: {path}")
        require(track.GetAttribute("physxSurfaceVelocity:surfaceVelocity").IsValid(), f"No track drive: {path}")
        track_mass = read_mass(track)
        require(math.isclose(track_mass, expected_mass, abs_tol=0.01), f"Unexpected mass: {path}: {track_mass}")
        joint = stage.GetPrimAtPath(joint_path)
        require(joint.IsValid() and joint.GetTypeName() == "PhysicsFixedJoint", f"Missing fixed joint: {joint_path}")
        require(joint.GetRelationship("physics:body0").GetTargets() == [root.GetPath()], f"Joint body0 mismatch: {joint_path}")
        require(joint.GetRelationship("physics:body1").GetTargets() == [track.GetPath()], f"Joint body1 mismatch: {joint_path}")
        total_mass += track_mass
        print(f"{side}: rigid body, collision, surface drive, fixed joint; {track_mass:.2f} kg")

    transform = UsdGeom.XformCache(Usd.TimeCode.Default()).GetLocalToWorldTransform(root)
    position = transform.ExtractTranslation()
    print(f"Scene: {scene_path}")
    print(f"UGV position: ({position[0]:.3f}, {position[1]:.3f}, {position[2]:.3f}) m")
    print(f"Explicit total mass: {total_mass:.2f} kg")
    print("GUI stage inspection: OK (read-only)")
    lab_scene_path = lab_stage.GetRootLayer().identifier if lab_stage is not None else "<none>"
    print(f"Isaac Lab current stage before binding: {lab_scene_path}")
    with sim_utils.use_stage(stage):
        require(sim_utils.get_current_stage() is stage, "Isaac Lab could not bind the open GUI stage")
        print("Isaac Lab can inspect the GUI stage: OK (temporary read-only binding)")


main()
