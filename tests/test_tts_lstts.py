"""离线验证 Trisolaris 的 TTS 通道只剩 lstts(IndexTTS)。

不访问网络、不调用真实 TTS、不依赖 ffmpeg：lstts_core 由桩模块替代。
"""

from __future__ import annotations

import importlib.util
import json
import math
import shutil
import struct
import sys
import tempfile
import types
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
AUDIO_DIR = REPO / "tools" / "audio"
sys.path.insert(0, str(AUDIO_DIR))

try:  # 测试机未装 pyserial 时用桩顶替，避免 import 失败
    import serial  # noqa: F401
except ImportError:  # pragma: no cover - 仅在缺依赖时触发
    serial_stub = types.ModuleType("serial")
    serial_stub.Serial = object
    sys.modules["serial"] = serial_stub

play_stub = types.ModuleType("listenai_play_repo")
play_stub.resolve_listenai_play = lambda update=False: Path("listenai_play.py")
sys.modules.setdefault("listenai_play_repo", play_stub)

SPEC = importlib.util.spec_from_file_location("fan_validation_helper", AUDIO_DIR / "fan_validation_helper.py")
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)


def write_wav(path: Path, rate: int = 24000, channels: int = 1, seconds: float = 0.3, amplitude: int = 3000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        frames = int(rate * seconds)
        for index in range(frames):
            handle.writeframes(struct.pack("<h", int(amplitude * math.sin(2 * math.pi * 220 * index / rate))))


def wav_info(path: Path) -> tuple[int, int, int]:
    with wave.open(str(path), "rb") as handle:
        return handle.getframerate(), handle.getnchannels(), handle.getsampwidth()


class StubLsttsCore(types.ModuleType):
    def __init__(self, rate: int = 16000, error: Exception | None = None) -> None:
        super().__init__("lstts_core")
        self.calls: list[dict] = []
        self.rate = rate
        self.error = error

        def load_config(name: str = "index_tts.json", path=None):
            return {"base_url": "http://stub.invalid", "token": "stub", "request_timeout": 5}

        def synthesize_one(text, output, *, voice="付小春", emotion=None, config=None, timeout_s=None, validate_audio=True):
            self.calls.append({"text": text, "voice": voice, "output": str(output), "timeout_s": timeout_s})
            if self.error:
                raise self.error
            write_wav(Path(output), rate=self.rate)

        self.load_config = load_config
        self.synthesize_one = synthesize_one


class RunTtsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.out = self.root / "cache" / "hello.wav"

    def tearDown(self):
        self.temp.cleanup()
        sys.modules.pop("lstts_core", None)

    def install_stub(self, **kwargs) -> StubLsttsCore:
        stub = StubLsttsCore(**kwargs)
        sys.modules["lstts_core"] = stub
        return stub

    def test_config_defaults_when_file_missing(self):
        missing = self.root / "nope.json"
        with patch.object(helper, "TTS_CONFIG_PATH", missing):
            config = helper.load_tts_config()
        self.assertEqual(config["engine"], "lstts")
        self.assertEqual(config["default_voice"], "付小春")
        self.assertEqual(config["sample_rate"], 16000)
        self.assertEqual(config["voice_map"], {})

    def test_repo_config_maps_legacy_voices(self):
        config = helper.load_tts_config()
        self.assertEqual(helper.resolve_tts_voice("Microsoft Huihui Desktop", config), "付小春")
        self.assertEqual(helper.resolve_tts_voice("zh-CN-YunxiNeural", config), "小宁")
        self.assertEqual(helper.resolve_tts_voice("付小春", config), "付小春")
        self.assertEqual(helper.resolve_tts_voice("custom-voice", config), "custom-voice")

    def test_sapi_like_name_falls_back_to_default_voice(self):
        config = helper.load_tts_config()
        self.assertEqual(helper.resolve_tts_voice("Microsoft Yaoyao Desktop", config), "付小春")

    def test_run_tts_uses_lstts_and_keeps_output_path(self):
        stub = self.install_stub(rate=16000)
        helper.run_tts("打开风扇", self.out, "Microsoft Huihui Desktop", 0)
        self.assertTrue(self.out.is_file())
        self.assertEqual(len(stub.calls), 1)
        self.assertEqual(stub.calls[0]["voice"], "付小春")
        self.assertEqual(Path(stub.calls[0]["output"]), self.out.with_suffix(".lstts.wav"))
        self.assertEqual(wav_info(self.out), (16000, 1, 2))
        self.assertFalse(self.out.with_suffix(".lstts.wav").exists(), "临时文件应被清理")

    def test_run_tts_converts_non_compliant_rate(self):
        self.install_stub(rate=24000)

        def fake_run(command, **kwargs):
            # 模拟 ffmpeg：把源音频转成 16 kHz 单声道
            source, target = Path(command[command.index("-i") + 1]), Path(command[-1])
            write_wav(target, rate=16000)
            return types.SimpleNamespace(returncode=0, stdout="", stderr="")

        with patch.object(helper.shutil, "which", return_value="/usr/bin/ffmpeg"), patch.object(helper.subprocess, "run", side_effect=fake_run):
            helper.run_tts("打开风扇", self.out, "付小春", 0)
        self.assertEqual(wav_info(self.out), (16000, 1, 2))

    def test_run_tts_reports_missing_ffmpeg_instead_of_falling_back(self):
        self.install_stub(rate=24000)
        with patch.object(helper.shutil, "which", return_value=None):
            with self.assertRaises(RuntimeError) as caught:
                helper.run_tts("打开风扇", self.out, "付小春", 0)
        self.assertIn("ffmpeg is required", str(caught.exception))
        self.assertFalse(self.out.exists())
        self.assertFalse(self.out.with_suffix(".lstts.wav").exists())

    def test_missing_lstts_core_points_at_install_command(self):
        original_import = __import__

        def blocking_import(name, *args, **kwargs):
            if name == "lstts_core" or name.startswith("lstts_core."):
                raise ImportError("simulated missing lstts_core")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=blocking_import):
            with self.assertRaises(RuntimeError) as caught:
                helper.run_tts("打开风扇", self.out, "付小春", 0)
        message = str(caught.exception)
        self.assertIn("lstts_core is required", message)
        self.assertIn("pip install", message)
        self.assertIn("github.com/zjashanda/lstts", message)

    def test_lstts_failure_is_not_masked(self):
        self.install_stub(error=RuntimeError("service 502"))
        with self.assertRaises(RuntimeError) as caught:
            helper.run_tts("打开风扇", self.out, "付小春", 0)
        self.assertIn("lstts synthesis failed", str(caught.exception))
        self.assertIn("service 502", str(caught.exception))
        self.assertFalse(self.out.exists())

    def test_empty_text_rejected(self):
        with self.assertRaises(ValueError):
            helper.run_tts("   ", self.out, "付小春", 0)

    def test_no_legacy_engine_left_in_source(self):
        # 旧通道关键字拆开拼装，避免本文件自身被全仓 grep 误判为残留
        legacy = ("edge" + "_tts", "edge-" + "tts", "power" + "shell", "e" + "speak", "system." + "speech")
        source = (AUDIO_DIR / "fan_validation_helper.py").read_text(encoding="utf-8").lower()
        for token in legacy:
            self.assertNotIn(token, source, f"旧合成通道残留：{token}")

    def test_ensure_cached_tts_records_engine_and_reuses_cache(self):
        self.install_stub(rate=16000)
        cache_dir = self.root / "audio_cache" / "tts"
        manifest_path = self.root / "audio_cache" / "manifest.json"
        with patch.object(helper, "ROOT", self.root), patch.object(helper, "AUDIO_CACHE_DIR", cache_dir), \
                patch.object(helper, "MANIFEST_PATH", manifest_path):
            first, cached_first = helper.ensure_cached_tts("打开风扇", "Microsoft Huihui Desktop", 0, "probe")
            second, cached_second = helper.ensure_cached_tts("打开风扇", "Microsoft Huihui Desktop", 0, "probe")
        self.assertFalse(cached_first)
        self.assertTrue(cached_second)
        self.assertEqual(first, second)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        entry = next(iter(manifest["entries"].values()))
        self.assertEqual(entry["engine"], "lstts")
        self.assertEqual(entry["sample_rate"], 16000)


if __name__ == "__main__":
    unittest.main()
