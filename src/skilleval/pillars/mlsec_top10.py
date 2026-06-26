"""
ML Security Top 10 (ML-SEC-10) - Machine Learning Security

Based on: ML Commons AI Safety benchmarks and industry best practices
Focus: ML-specific vulnerabilities and attacks.
"""

import re
from pathlib import Path
from typing import List

from skilleval.models import Finding, Severity


class MLSecTop10Checker:
    """
    ML Security Top 10 checks.

    Covers:
    1. Model extraction/stealing
    2. Data poisoning
    3. Adversarial examples
    4. Model inversion
    5. Membership inference
    6. Backdoor attacks
    7. Model evasion
    8. Training data leakage
    9. Unsafe deserialization
    10. Inference manipulation
    """

    def check_all(self, skill_path: Path) -> List[Finding]:
        """Run all ML Security checks."""
        findings = []

        findings.extend(self._check_model_extraction(skill_path))
        findings.extend(self._check_data_poisoning(skill_path))
        findings.extend(self._check_adversarial_robustness(skill_path))
        findings.extend(self._check_model_inversion(skill_path))
        findings.extend(self._check_membership_inference(skill_path))
        findings.extend(self._check_backdoor_attacks(skill_path))
        findings.extend(self._check_unsafe_deserialization(skill_path))
        findings.extend(self._check_training_data_leak(skill_path))
        findings.extend(self._check_inference_security(skill_path))
        findings.extend(self._check_model_versioning(skill_path))

        return findings

    def _check_model_extraction(self, skill_path: Path) -> List[Finding]:
        """
        ML-SEC-01: Model Extraction/Stealing

        Risk: Attacker queries model to clone it.
        """
        findings = []

        for file_path in skill_path.rglob("*.py"):
            try:
                content = file_path.read_text()

                # API endpoint for model without rate limiting
                has_api = bool(re.search(r'@app\.route.*predict|@app\.post.*infer', content))
                has_rate_limit = bool(re.search(r'rate_limit|throttle|quota', content, re.IGNORECASE))

                if has_api and not has_rate_limit:
                    findings.append(Finding(
                        type="MLSEC01_MODEL_EXTRACTION",
                        severity=Severity.MEDIUM,
                        message="Model API without rate limiting - extraction risk",
                        file=str(file_path.relative_to(skill_path)),
                        line=None,
                        remediation="Add rate limiting to prevent model extraction attacks",
                    ))
            except Exception:
                pass

        return findings

    def _check_data_poisoning(self, skill_path: Path) -> List[Finding]:
        """
        ML-SEC-02: Data Poisoning

        Risk: Malicious data in training set corrupts model.
        """
        findings = []

        for file_path in skill_path.rglob("*.py"):
            try:
                content = file_path.read_text()

                # Training with user-provided data
                patterns = [
                    (r'train.*user_data', 'Training on user data without validation'),
                    (r'fit\(.*input', 'Model fit on unvalidated input'),
                    (r'update.*weights.*user', 'Weight update from user'),
                ]

                for pattern, desc in patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        # Check for validation
                        has_validation = bool(re.search(
                            r'validate|sanitize|filter|clean',
                            content,
                            re.IGNORECASE
                        ))

                        if not has_validation:
                            findings.append(Finding(
                                type="MLSEC02_DATA_POISONING",
                                severity=Severity.HIGH,
                                message=f"Data poisoning risk: {desc}",
                                file=str(file_path.relative_to(skill_path)),
                                line=None,
                                remediation="Validate training data to prevent poisoning",
                            ))
                        break
            except Exception:
                pass

        return findings

    def _check_adversarial_robustness(self, skill_path: Path) -> List[Finding]:
        """
        ML-SEC-03: Adversarial Examples

        Risk: Crafted inputs fool the model.
        """
        findings = []

        for file_path in skill_path.rglob("*.py"):
            try:
                content = file_path.read_text()

                # Model predictions without adversarial checks
                has_predict = bool(re.search(r'\.predict\(|\.classify\(', content))
                has_robustness = bool(re.search(
                    r'adversarial|robust|defense|certified',
                    content,
                    re.IGNORECASE
                ))

                if has_predict and not has_robustness:
                    findings.append(Finding(
                        type="MLSEC03_NO_ADVERSARIAL_DEFENSE",
                        severity=Severity.LOW,
                        message="Model lacks adversarial robustness checks",
                        file=str(file_path.relative_to(skill_path)),
                        line=None,
                        remediation="Add adversarial robustness testing",
                    ))
            except Exception:
                pass

        return findings

    def _check_model_inversion(self, skill_path: Path) -> List[Finding]:
        """
        ML-SEC-04: Model Inversion

        Risk: Reconstruct training data from model outputs.
        """
        findings = []

        for file_path in skill_path.rglob("*.py"):
            try:
                content = file_path.read_text()

                # Returning confidence scores/gradients (helps inversion)
                patterns = [
                    (r'return.*probability', 'Returning probabilities'),
                    (r'return.*confidence', 'Returning confidence scores'),
                    (r'return.*gradient', 'Returning gradients'),
                ]

                for pattern, desc in patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        findings.append(Finding(
                            type="MLSEC04_MODEL_INVERSION",
                            severity=Severity.MEDIUM,
                            message=f"Model inversion risk: {desc}",
                            file=str(file_path.relative_to(skill_path)),
                            line=None,
                            remediation="Limit exposure of model internals to prevent inversion",
                        ))
                        break
            except Exception:
                pass

        return findings

    def _check_membership_inference(self, skill_path: Path) -> List[Finding]:
        """
        ML-SEC-05: Membership Inference

        Risk: Determine if data was in training set.
        """
        findings = []

        for file_path in skill_path.rglob("*.py"):
            try:
                content = file_path.read_text()

                # Overfitting increases membership inference risk
                patterns = [
                    (r'epochs\s*=\s*[5-9]\d{2,}', 'Very high epoch count - overfitting risk'),
                    (r'train_acc.*>.*0\.99', 'Near-perfect training accuracy'),
                ]

                for pattern, desc in patterns:
                    if re.search(pattern, content):
                        findings.append(Finding(
                            type="MLSEC05_MEMBERSHIP_INFERENCE",
                            severity=Severity.LOW,
                            message=f"Membership inference risk: {desc}",
                            file=str(file_path.relative_to(skill_path)),
                            line=None,
                            remediation="Add regularization and differential privacy",
                        ))
            except Exception:
                pass

        return findings

    def _check_backdoor_attacks(self, skill_path: Path) -> List[Finding]:
        """
        ML-SEC-06: Backdoor/Trojan Attacks

        Risk: Model has hidden malicious behavior.
        """
        findings = []

        for file_path in skill_path.rglob("*.py"):
            try:
                content = file_path.read_text()

                # Loading pre-trained models from untrusted sources
                patterns = [
                    (r'load.*model.*http', 'Loading model from URL'),
                    (r'torch\.load\(.*url', 'Loading PyTorch model from URL'),
                    (r'keras\.models\.load.*download', 'Loading Keras model from download'),
                ]

                for pattern, desc in patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        findings.append(Finding(
                            type="MLSEC06_BACKDOOR_RISK",
                            severity=Severity.HIGH,
                            message=f"Backdoor risk: {desc}",
                            file=str(file_path.relative_to(skill_path)),
                            line=None,
                            remediation="Only load models from trusted sources with integrity checks",
                        ))
            except Exception:
                pass

        return findings

    def _check_unsafe_deserialization(self, skill_path: Path) -> List[Finding]:
        """
        ML-SEC-07: Unsafe Model Deserialization

        Risk: Malicious code in model files.
        """
        findings = []

        unsafe_patterns = [
            (r'pickle\.load\(', 'pickle.load - unsafe deserialization'),
            (r'joblib\.load\(', 'joblib.load without validation'),
            (r'torch\.load\(.*map_location', 'torch.load without weights_only=True'),
            (r'np\.load\(.*allow_pickle\s*=\s*True', 'numpy load with allow_pickle'),
        ]

        for file_path in skill_path.rglob("*.py"):
            try:
                content = file_path.read_text()

                for pattern, desc in unsafe_patterns:
                    for match in re.finditer(pattern, content):
                        line = content[:match.start()].count('\n') + 1
                        findings.append(Finding(
                            type="MLSEC07_UNSAFE_DESERIALIZE",
                            severity=Severity.CRITICAL,
                            message=f"Unsafe deserialization: {desc}",
                            file=str(file_path.relative_to(skill_path)),
                            line=line,
                            remediation="Use safe formats (HDF5, SafeTensors) or torch.load(weights_only=True)",
                        ))
            except Exception:
                pass

        return findings

    def _check_training_data_leak(self, skill_path: Path) -> List[Finding]:
        """
        ML-SEC-08: Training Data Leakage

        Risk: Training data exposed in model outputs.
        """
        findings = []

        for file_path in skill_path.rglob("*.py"):
            try:
                content = file_path.read_text()

                # Verbatim data in responses
                patterns = [
                    (r'return.*training_data', 'Returning training data'),
                    (r'response.*examples', 'Including examples in response'),
                ]

                for pattern, desc in patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        findings.append(Finding(
                            type="MLSEC08_DATA_LEAKAGE",
                            severity=Severity.HIGH,
                            message=f"Training data leakage: {desc}",
                            file=str(file_path.relative_to(skill_path)),
                            line=None,
                            remediation="Never expose training data in model outputs",
                        ))
            except Exception:
                pass

        return findings

    def _check_inference_security(self, skill_path: Path) -> List[Finding]:
        """
        ML-SEC-09: Inference-Time Manipulation

        Risk: Attacks during model inference.
        """
        findings = []

        for file_path in skill_path.rglob("*.py"):
            try:
                content = file_path.read_text()

                # Inference without input validation
                has_inference = bool(re.search(r'predict\(|infer\(|forward\(', content))
                has_input_val = bool(re.search(
                    r'validate_input|check_bounds|sanitize',
                    content,
                    re.IGNORECASE
                ))

                if has_inference and not has_input_val:
                    findings.append(Finding(
                        type="MLSEC09_NO_INPUT_VALIDATION",
                        severity=Severity.MEDIUM,
                        message="Inference without input validation",
                        file=str(file_path.relative_to(skill_path)),
                        line=None,
                        remediation="Validate inputs (shape, range, type) before inference",
                    ))
            except Exception:
                pass

        return findings

    def _check_model_versioning(self, skill_path: Path) -> List[Finding]:
        """
        ML-SEC-10: Lack of Model Versioning

        Risk: Can't track or rollback compromised models.
        """
        findings = []

        for file_path in skill_path.rglob("*.py"):
            try:
                content = file_path.read_text()

                # Model saving without versioning
                save_patterns = [
                    r'save_model\(',
                    r'\.save\(',
                    r'torch\.save\(',
                ]

                for pattern in save_patterns:
                    if re.search(pattern, content):
                        # Check for version tracking
                        has_version = bool(re.search(
                            r'version|timestamp|hash|checksum',
                            content,
                            re.IGNORECASE
                        ))

                        if not has_version:
                            findings.append(Finding(
                                type="MLSEC10_NO_VERSIONING",
                                severity=Severity.LOW,
                                message="Model saving without version tracking",
                                file=str(file_path.relative_to(skill_path)),
                                line=None,
                                remediation="Add version/timestamp to model saves",
                            ))
                        break
            except Exception:
                pass

        return findings


def check_mlsec_top10(skill_path: Path) -> List[Finding]:
    """
    Main entry point for ML Security Top 10 checks.

    Args:
        skill_path: Path to skill directory

    Returns:
        List of findings
    """
    checker = MLSecTop10Checker()
    return checker.check_all(skill_path)
