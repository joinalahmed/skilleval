"""
CVE scanner using pip-audit and grype.
"""

import subprocess
import json
from pathlib import Path
from typing import List, Dict, Any, Optional


class CVEScanner:
    """Scan for CVEs in dependencies and container images."""

    @staticmethod
    def scan_python_dependencies(skill_path: Path) -> List[Dict[str, Any]]:
        """
        Scan Python dependencies for CVEs using pip-audit.

        Args:
            skill_path: Path to skill directory

        Returns:
            List of CVE findings
        """
        findings = []

        # Look for requirements.txt or pyproject.toml
        requirements_files = list(skill_path.glob("**/requirements.txt"))
        pyproject_files = list(skill_path.glob("**/pyproject.toml"))

        if not requirements_files and not pyproject_files:
            return findings

        # Check if pip-audit is available
        try:
            subprocess.run(
                ["pip-audit", "--version"],
                capture_output=True,
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            # pip-audit not installed, skip
            return findings

        # Scan each requirements file
        for req_file in requirements_files:
            try:
                result = subprocess.run(
                    ["pip-audit", "-r", str(req_file), "--format", "json"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                if result.returncode == 0 and result.stdout:
                    data = json.loads(result.stdout)
                    for vuln in data.get("vulnerabilities", []):
                        findings.append({
                            "type": "CVE",
                            "cve_id": vuln.get("id", "UNKNOWN"),
                            "package": vuln.get("name", ""),
                            "version": vuln.get("version", ""),
                            "severity": vuln.get("severity", "MEDIUM").upper(),
                            "description": vuln.get("description", "")[:200],
                            "fix_version": vuln.get("fix_versions", [""])[0],
                            "file": str(req_file.relative_to(skill_path)),
                        })
            except Exception:
                # Skip on error
                pass

        return findings

    @staticmethod
    def scan_container_images(skill_path: Path) -> List[Dict[str, Any]]:
        """
        Scan container images for CVEs using grype.

        Args:
            skill_path: Path to skill directory

        Returns:
            List of CVE findings
        """
        findings = []

        # Look for Dockerfile or Containerfile
        dockerfile_patterns = ["**/Dockerfile", "**/Containerfile", "**/*.dockerfile"]
        dockerfiles = []
        for pattern in dockerfile_patterns:
            dockerfiles.extend(skill_path.glob(pattern))

        if not dockerfiles:
            return findings

        # Check if grype is available
        try:
            subprocess.run(
                ["grype", "version"],
                capture_output=True,
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            # grype not installed, skip
            return findings

        # Extract base images from Dockerfiles
        images = set()
        for dockerfile in dockerfiles:
            try:
                content = dockerfile.read_text()
                for line in content.splitlines():
                    if line.strip().upper().startswith("FROM"):
                        parts = line.split()
                        if len(parts) >= 2:
                            images.add(parts[1])
            except Exception:
                pass

        # Scan each unique image
        for image in images:
            try:
                result = subprocess.run(
                    ["grype", image, "-o", "json"],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )

                if result.returncode == 0 and result.stdout:
                    data = json.loads(result.stdout)
                    for match in data.get("matches", [])[:20]:  # Limit to 20
                        vuln = match.get("vulnerability", {})
                        findings.append({
                            "type": "CONTAINER_CVE",
                            "cve_id": vuln.get("id", "UNKNOWN"),
                            "package": match.get("artifact", {}).get("name", ""),
                            "version": match.get("artifact", {}).get("version", ""),
                            "severity": vuln.get("severity", "MEDIUM").upper(),
                            "description": vuln.get("description", "")[:200],
                            "fix_version": vuln.get("fix", {}).get("versions", [""])[0],
                            "image": image,
                        })
            except Exception:
                # Skip on error
                pass

        return findings
