import copy
import unittest
from pathlib import Path

from scripts.smoke_hakusan_release import validate


class CloudContractTests(unittest.TestCase):
    def test_otp_digest_uses_push_evidence_without_analysis_permissions(self):
        deploy = Path("scripts/deploy-hakusan-otp.sh").read_text()
        self.assertNotIn("gcloud artifacts docker images describe", deploy)
        self.assertIn("carless-otp-push.log", deploy)
        self.assertIn("tee /workspace/carless-otp-push.log", Path("cloudbuild.yaml").read_text())

    def test_smoke_rejects_mock_missing_dates_and_unknown(self):
        categories = ["supermarket", "hospital", "pharmacy", "city_hall", "station", "social"]
        diagnosis = {"data_source": "routing_provider", "item_results": [
            {"destination_id": c, "category": c, "status": "caution"} for c in categories
        ]}
        tasks = [{"destination_id": c, "data_source": "routing_provider",
                  "outbound_departure": "out", "return_departure": "back",
                  "voice_script_ja": "指定日時の練習"} for c in categories]
        validate(diagnosis, tasks, "out", "back")
        invalid = copy.deepcopy(diagnosis)
        invalid["data_source"] = "fixture"
        with self.assertRaises(AssertionError):
            validate(invalid, tasks, "out", "back")
        invalid = copy.deepcopy(diagnosis)
        invalid["item_results"][0]["status"] = "unknown"
        with self.assertRaises(AssertionError):
            validate(invalid, tasks, "out", "back")
        with self.assertRaises(AssertionError):
            validate(diagnosis, tasks, "different", "back")

    def test_release_wires_private_otp_and_all_real_gates(self):
        build = Path("cloudbuild.yaml").read_text()
        release = Path("scripts/promote-and-verify.sh").read_text()
        self.assertIn("--build-arg=VITE_DATA_PROFILE=hakusan", build)
        self.assertIn("--file=backend/Dockerfile", build)
        self.assertIn("sha256sum -c", build)
        self.assertEqual(release.count("python3 scripts/smoke_hakusan_release.py"), 3)
        self.assertIn('env.get("OTP_IDENTITY_AUDIENCE")', release)
        self.assertIn("OTP_SERVICE_URL", release)
        self.assertIn("release_release_lock", release)
        docker = Path("backend/Dockerfile").read_text()
        self.assertIn("COPY data/hakusan /app/data/hakusan", docker)
        self.assertIn("WORKDIR /app/backend", docker)


if __name__ == "__main__":
    unittest.main()
