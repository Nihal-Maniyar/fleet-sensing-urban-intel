"""Edge camera stream interfaces and implementations."""

from edge.camera.stream import VideoStreamSource, OpenCVFileStream, SyntheticRoadStream

__all__ = ["VideoStreamSource", "OpenCVFileStream", "SyntheticRoadStream"]
