"""
Eu Edito — Intelligent Narrative Motion Design Engine
Four-stage modular architecture:
  A. Visual Interpreter  (interpreter.py)
  B. Art Direction Engine (art_director.py)
  C. Scene Composer       (scene_composer.py)
  D. Animation Engine     (animation_engine.py)
Supported by Frame Analysis (frame_analyzer.py), Modular Assets Library (assets_library.py),
and Visual Quality Gate (quality_gate.py).
"""
from .frame_analyzer import analyze_video_frames
from .interpreter import interpret_segment
from .art_director import direct_art
from .scene_composer import compose_scene_plan
from .animation_engine import render_scene_clip, render_scene_frame
from .quality_gate import validate_and_refine_plan, audit_rendered_frame

__all__ = [
    "analyze_video_frames",
    "interpret_segment",
    "direct_art",
    "compose_scene_plan",
    "render_scene_clip",
    "render_scene_frame",
    "validate_and_refine_plan",
    "audit_rendered_frame",
]
