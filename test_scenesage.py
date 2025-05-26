import os
import json
import pytest
from pysrt import SubRipFile, SubRipItem, SubRipTime
from scenesage import detect_scenes, format_subrip_time

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

def create_single_subtitle():
    """Create a subtitle file with a single subtitle."""
    subs = SubRipFile()
    subs.append(SubRipItem(
        index=1,
        start=SubRipTime(0, 0, 0, 0),
        end=SubRipTime(0, 0, 5, 0),
        text="Single subtitle test."
    ))
    return subs

def create_overlapping_subtitles():
    """Create a subtitle file with overlapping subtitles."""
    subs = SubRipFile()
    subs.append(SubRipItem(
        index=1,
        start=SubRipTime(0, 0, 0, 0),
        end=SubRipTime(0, 0, 5, 0),
        text="First subtitle."
    ))
    subs.append(SubRipItem(
        index=2,
        start=SubRipTime(0, 0, 4, 0),  # Overlaps with first subtitle
        end=SubRipTime(0, 0, 9, 0),
        text="Overlapping subtitle."
    ))
    return subs

def create_long_pause_subtitles():
    """Create a subtitle file with a very long pause."""
    subs = SubRipFile()
    subs.append(SubRipItem(
        index=1,
        start=SubRipTime(0, 0, 0, 0),
        end=SubRipTime(0, 0, 5, 0),
        text="First scene."
    ))
    subs.append(SubRipItem(
        index=2,
        start=SubRipTime(0, 1, 0, 0),  # 1 minute pause
        end=SubRipTime(0, 1, 5, 0),
        text="Second scene after long pause."
    ))
    return subs

def test_detect_scenes():
    """Test scene detection functionality."""
    subs = create_test_subtitle()
    scenes = detect_scenes(subs, min_pause=4)
    
    assert len(scenes) == 2
    
    # Test first scene
    assert format_subrip_time(scenes[0]["start"]) == "00:00:22,719"
    assert format_subrip_time(scenes[0]["end"]) == "00:00:31,507"
    assert scenes[0]["text"] == "Greetings, my friend. We are all interested in the future."
    
    # Test second scene
    assert format_subrip_time(scenes[1]["start"]) == "00:00:36,507"
    assert format_subrip_time(scenes[1]["end"]) == "00:00:40,507"
    assert scenes[1]["text"] == "The future is where we're going."

def test_detect_scenes_different_pause():
    """Test scene detection with different pause durations."""
    subs = create_test_subtitle()
    
    # Test with shorter pause (should combine scenes)
    scenes_short = detect_scenes(subs, min_pause=6)
    assert len(scenes_short) == 1
    
    # Test with longer pause (should keep scenes separate)
    scenes_long = detect_scenes(subs, min_pause=3)
    assert len(scenes_long) == 2

def test_single_subtitle():
    """Test scene detection with a single subtitle."""
    subs = create_single_subtitle()
    scenes = detect_scenes(subs, min_pause=4)
    
    assert len(scenes) == 1
    assert format_subrip_time(scenes[0]["start"]) == "00:00:00,000"
    assert format_subrip_time(scenes[0]["end"]) == "00:00:05,000"
    assert scenes[0]["text"] == "Single subtitle test."

def test_empty_subtitles():
    """Test scene detection with empty subtitle file."""
    subs = SubRipFile()
    with pytest.raises(IndexError):
        detect_scenes(subs, min_pause=4)

def test_overlapping_subtitles():
    """Test scene detection with overlapping subtitles."""
    subs = create_overlapping_subtitles()
    scenes = detect_scenes(subs, min_pause=4)
    
    assert len(scenes) == 1
    assert format_subrip_time(scenes[0]["start"]) == "00:00:00,000"
    assert format_subrip_time(scenes[0]["end"]) == "00:00:09,000"
    assert scenes[0]["text"] == "First subtitle. Overlapping subtitle."

def test_long_pause_subtitles():
    """Test scene detection with very long pauses."""
    subs = create_long_pause_subtitles()
    scenes = detect_scenes(subs, min_pause=4)
    
    assert len(scenes) == 2
    assert format_subrip_time(scenes[0]["start"]) == "00:00:00,000"
    assert format_subrip_time(scenes[0]["end"]) == "00:00:05,000"
    assert scenes[0]["text"] == "First scene."
    
    assert format_subrip_time(scenes[1]["start"]) == "00:01:00,000"
    assert format_subrip_time(scenes[1]["end"]) == "00:01:05,000"
    assert scenes[1]["text"] == "Second scene after long pause."

def test_format_subrip_time():
    """Test SubRipTime formatting."""
    time = SubRipTime(1, 2, 3, 456)
    assert format_subrip_time(time) == "01:02:03,456"
    
    # Test edge cases
    zero_time = SubRipTime(0, 0, 0, 0)
    assert format_subrip_time(zero_time) == "00:00:00,000"
    
    max_time = SubRipTime(23, 59, 59, 999)
    assert format_subrip_time(max_time) == "23:59:59,999"

if __name__ == "__main__":
    pytest.main([__file__]) 