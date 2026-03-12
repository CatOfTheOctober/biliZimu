from bilibili_extractor.modules.asr_engine import FunASREngine


def test_parse_funasr_sentence_info_segments():
    engine = FunASREngine()
    result = {
        "sentence_info": [
            {"start": 0, "end": 1200, "sentence": "第一句。"},
            {"start": 1300, "end": 2500, "sentence": "第二句！"},
        ]
    }

    segments = engine._parse_funasr_result(result)

    assert len(segments) == 2
    assert segments[0].start_time == 0.0
    assert segments[0].end_time == 1.2
    assert segments[0].text == "第一句。"
    assert segments[1].start_time == 1.3
    assert segments[1].end_time == 2.5


def test_parse_funasr_character_timestamps_to_clause_segments():
    engine = FunASREngine()
    result = {
        "text": "你好，世界。再见！",
        "timestamp": [
            [0, 100],
            [100, 200],
            [300, 400],
            [400, 500],
            [600, 700],
            [700, 800],
        ],
    }

    segments = engine._parse_funasr_result(result)

    assert [segment.text for segment in segments] == ["你好，", "世界。", "再见！"]
    assert segments[0].start_time == 0.0
    assert segments[0].end_time == 0.2
    assert segments[1].start_time == 0.3
    assert segments[1].end_time == 0.5
    assert segments[2].start_time == 0.6
    assert segments[2].end_time == 0.8


def test_parse_funasr_word_level_timestamp_format():
    engine = FunASREngine()
    result = {
        "timestamp": [
            ["你好", 0, 500],
            ["世界", 600, 1200],
        ]
    }

    segments = engine._parse_funasr_result(result)

    assert len(segments) == 2
    assert segments[0].text == "你好"
    assert segments[0].start_time == 0.0
    assert segments[0].end_time == 0.5
    assert segments[1].text == "世界"
    assert segments[1].start_time == 0.6
    assert segments[1].end_time == 1.2
