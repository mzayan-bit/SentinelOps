"""
SentinelOps — Live Video Tracking Test
=========================================
Script to test the ByteTrack video tracking pipeline.
"""

import sys
from pathlib import Path

# Ensure project root is in PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from inference.tracker import VideoTracker


def main() -> None:
    # 1. Initialise the tracking service
    tracker = VideoTracker(confidence=0.25)

    # 2. Run tracking on the test video
    # Set show=True to see the live OpenCV window
    tracker.process_video(
        input_path="test_assets/worker_video.mp4",
        output_path="output_tracked.mp4",
        show=False,  # Set to True to watch live
        tracker_type="bytetrack.yaml",
    )


if __name__ == "__main__":
    main()