import os
import json
import pytest
from pysrt import SubRipFile, SubRipItem, SubRipTime
from scenesage import detect_scenes, Scene

def create_test_subtitle():
    """Create a test subtitle file with known scenes."""
    subs = SubRipFile()
    
    # Scene 1
    subs.append(SubRipItem(
        index=1,
        start=SubRipTime(0, 0, 22, 719),
        end=SubRipTime(0, 0, 26, 759),
        text="Greetings, my friend."
    ))
    subs.append(SubRipItem(
        index=2,
        start=SubRipTime(0, 0, 26, 860),
        end=SubRipTime(0, 0, 31, 507),
        text="We are all interested in the future."
    ))
    
    # Scene 2 (after 5 second pause)
    subs.append(SubRipItem(
        index=3,
        start=SubRipTime(0, 0, 36, 507),
        end=SubRipTime(0, 0, 40, 507),
        text="The future is where we're going."
    ))
    
    return subs

def test_detect_scenes():
    """Test scene detection functionality."""
    subs = create_test_subtitle()
    scenes = detect_scenes(subs, min_pause=4)
    
    assert len(scenes) == 2
    assert scenes[0]["start"].to_string() == "00:00:22,719"
    assert scenes[0]["end"].to_string() == "00:00:31,507"
    assert scenes[1]["start"].to_string() == "00:00:36,507"
    assert scenes[1]["end"].to_string() == "00:00:40,507"

def test_scene_model():
    """Test Scene model validation."""
    scene = Scene(
        start="00:00:22,719",
        end="00:00:31,507",
        transcript="Test transcript",
        summary="Test summary",
        characters=["Character1"],
        mood="test",
        cultural_refs=[]
    )
    
    assert scene.start == "00:00:22,719"
    assert scene.end == "00:00:31,507"
    assert len(scene.characters) == 1
    assert len(scene.cultural_refs) == 0

if __name__ == "__main__":
    pytest.main([__file__]) 