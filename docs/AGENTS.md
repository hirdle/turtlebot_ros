# Repository Guidelines

## Project Structure & Module Organization
- Core motion control: `bot.py` (TurtleBot3 Waffle Pi, publishes to `/cmd_vel`, reads `/scan`, `/imu`, `/odom`).
- Camera pipeline: `bot_camera.py` (subscribes to `/front_camera/image_raw`, color masks, ROI utilities).
- Template matching: `main_matching.py` (offline image matching) and `matching_live.py` (webcam/ROS camera loop).
- Assets: `template/` contains sign templates; `docs/` holds usage notes for camera and matching flows.

## Build, Run & Test Commands
- Run navigation logic: `rosrun turtlebot_ros bot.py` or `python3 bot.py` after sourcing your ROS workspace; requires a running `roscore` and TurtleBot3 topics.
- Test matching on a single image: `python3 main_matching.py` (expects `tesing.png` and templates in `template/`).
- Live matching from a camera: `python3 matching_live.py --template_folder template` (keyboard: `q` exit, `0-4` color override).
- Validate imports quickly: `python3 -m py_compile bot.py bot_camera.py main_matching.py matching_live.py`.

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indentation; keep functions small and reusable.
- Use descriptive snake_case for variables/functions; keep ROS topic names explicit (e.g., `/cmd_vel`, `/scan`).
- Prefer module-level docstrings and short inline comments only where logic is non-obvious (e.g., angle normalization).
- Keep external dependencies minimal: `rospy`, `cv2`, `numpy`, `cv_bridge`, and standard ROS messages.

## Testing Guidelines
- No formal test suite yet; add focused checks for image utilities (e.g., `detect_dominant_color`, `extract_object_roi`) using saved frames from `template/`.
- When adding motion routines, test in simulation first (e.g., Gazebo) before real hardware; log sensor readiness via `wait_for_sensors`.
- Provide reproducible commands and sample inputs in PRs (image paths, thresholds, topic remaps).

## Commit & Pull Request Guidelines
- Commit messages: concise, present-tense imperatives (current history example: `init project`); group related changes per commit.
- PRs should include: a short summary, what was tested (commands + environment), and before/after evidence when touching vision logic (images or brief metrics).
- Reference related tickets/issues and call out any ROS parameter or topic changes; note new runtime dependencies explicitly.
