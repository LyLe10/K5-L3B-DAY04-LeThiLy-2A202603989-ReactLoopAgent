
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "evals"))

from agent import run_agent
from scenarios import ScenarioTools
from test_lab import FakeProvider, tool_call, final


class H7TimeoutTests(unittest.TestCase):

    def test_cloudflare_timeout_is_recorded(self):
        fake = FakeProvider([
            tool_call(
                "1",
                "get_status",
                '{"provider":"cloudflare","component":"spectrum"}'
            ),
            final("Không thể xác minh trạng thái Cloudflare do timeout.")
        ])

        result = run_agent(
            "Kiểm tra Cloudflare Spectrum",
            fake,
            ScenarioTools("cloudflare_timeout"),
            max_steps=3
        )

        self.assertEqual(result["status"], "completed")

        failures = [
            event
            for event in result["trace"]
            if event["event"] == "tool_failure"
        ]

        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]["error"], "TimeoutError")

    def test_timeout_does_not_mean_operational(self):
        fake = FakeProvider([
            tool_call(
                "1",
                "get_status",
                '{"provider":"cloudflare","component":"spectrum"}'
            ),
            final("Cloudflare Spectrum đang hoạt động bình thường.")
        ])

        result = run_agent(
            "Cloudflare Spectrum có đang hoạt động không?",
            fake,
            ScenarioTools("cloudflare_timeout"),
            max_steps=3
        )

        self.assertNotEqual(result["status"], "completed")

    def test_negated_operational_is_allowed(self):
        fake = FakeProvider([
            tool_call(
                "1",
                "get_status",
                '{"provider":"cloudflare","component":"spectrum"}'
            ),
            final(
                "Không thể xác nhận Cloudflare operational "
                "vì công cụ kiểm tra bị timeout."
            )
        ])

        result = run_agent(
            "Kiểm tra Cloudflare Spectrum",
            fake,
            ScenarioTools("cloudflare_timeout"),
            max_steps=3
        )

        self.assertEqual(result["status"], "completed")

    def test_successful_retry_clears_failure(self):
        class RetryTools:
            def __init__(self):
                self.calls = 0

            def execute(self, name, arguments):
                self.calls += 1

                if self.calls == 1:
                    return {
                        "ok": False,
                        "error": "TimeoutError",
                        "message": "Temporary timeout"
                    }

                return {
                    "ok": True,
                    "status": "operational"
                }

        fake = FakeProvider([
            tool_call(
                "1",
                "get_status",
                '{"provider":"cloudflare","component":"spectrum"}'
            ),
            tool_call(
                "2",
                "get_status",
                '{"provider":"cloudflare","component":"spectrum"}'
            ),
            final("Cloudflare Spectrum đang hoạt động bình thường.")
        ])

        result = run_agent(
            "Kiểm tra lại Cloudflare Spectrum",
            fake,
            RetryTools(),
            max_steps=4
        )

        self.assertEqual(result["status"], "completed")

    def test_mixed_answer_does_not_hide_false_claim(self):
        fake = FakeProvider([
            tool_call(
                "1",
                "get_status",
                '{"provider":"cloudflare","component":"spectrum"}'
            ),
            final(
                "Không thể xác nhận Cloudflare Spectrum "
                "do timeout. Tuy nhiên, Cloudflare Spectrum "
                "đang hoạt động bình thường."
            )
        ])

        result = run_agent(
            "Kiểm tra trạng thái Cloudflare Spectrum",
            fake,
            ScenarioTools("cloudflare_timeout"),
            max_steps=3
        )

        self.assertNotEqual(result["status"], "completed")
        self.assertTrue(
            any(
                event["event"] == "validation_unsupported_status"
                for event in result["trace"]
            )
        )


if __name__ == "__main__":
    unittest.main()
