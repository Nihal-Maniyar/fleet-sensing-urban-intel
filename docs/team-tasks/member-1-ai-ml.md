# Member 1 — AI/ML

## Owns

YOLO model selection/evaluation, OpenCV preprocessing, inference output, and support for evidence-image generation.

## First deliverable

Define and validate a small pothole-first inference interface that returns detections with label, bounding box, confidence, and frame timestamp. Work with Member 2 so the output can feed ByteTrack and the event engine.

## Read first

- `AGENTS.md`
- `docs/ai-pipeline.md`
- `docs/api-contract.md`
- `docs/prototype-scope.md`

## Boundaries

Do not create events, MQTT payloads, database records, tickets, or dashboard behavior. Do not add event classes beyond the approved candidate list without a contract change. Keep weights, recordings, and generated evidence out of Git.

## Done when

- Pothole is the primary supported demonstration detection.
- Outputs are documented for Member 2 and have focused tests/fixtures.
- Model limitations and confidence assumptions are reported in the pull request.
