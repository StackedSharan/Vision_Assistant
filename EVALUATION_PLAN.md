# Evaluation Plan — Vision Assistant (Summary)

Purpose: Validate usability, safety, and effectiveness of Vision Assistant for blind users.

1. Goals
- Measure task completion rate for common navigation tasks (e.g., walk from A→B).
- Measure obstacle detection usefulness (alerts perceived as helpful).
- Collect qualitative user satisfaction and suggestions.

2. Metrics
- Task completion: percentage of participants who reach the destination unaided.
- Time-on-task: average time to complete navigation tasks.
- False positive/negative rate for obstacle alerts (logged vs. ground truth).
- SUS (System Usability Scale) or Likert satisfaction scores.

3. Protocol (example)
- Recruit 6–12 participants (blind or low-vision) with informed consent.
- Setup device and calibration routine; record demographics.
- Tasks: 3 indoor navigation routes, 3 outdoor short routes with obstacles.
- Observers record events and note any confusion/errors.

4. Logging & Privacy
- Log only anonymized events: timestamps, event type (navigation step, obstacle alert), and coarse location.
- Do not store raw camera frames or audio without explicit consent.

5. Analysis
- Compute completion rates, average times, and compute basic precision/recall for alerts.
- Summarize qualitative feedback into improvement actions.

6. Deliverables
- Results summary, annotated logs, suggested next features prioritized by user impact.
