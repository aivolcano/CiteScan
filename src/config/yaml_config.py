"""
YAML configuration loader for citescan (bib-only).
"""
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class FilesConfig:
    """File path configuration (bib-only)."""
    bib: str = ""
    input_dir: str = ""
    output_dir: str = "citescan_output"


@dataclass
class BibliographyConfig:
    """Bibliography check configuration."""
    check_metadata: bool = True
    check_duplicates: bool = True
    check_preprint_ratio: bool = True
    preprint_warning_threshold: float = 0.50


@dataclass
class WorkflowStep:
    """Single step in the reference check workflow."""
    name: str
    enabled: bool = True
    description: str = ""


@dataclass
class OutputConfig:
    """Output configuration."""
    quiet: bool = False
    minimal_verified: bool = False


@dataclass
class CiteScanConfig:
    """citescan configuration"""
    files: FilesConfig = field(default_factory=FilesConfig)
    bibliography: BibliographyConfig = field(default_factory=BibliographyConfig)
    workflow: List[WorkflowStep] = field(default_factory=list)
    output: OutputConfig = field(default_factory=OutputConfig)

    _bib_files: List[Path] = field(default_factory=list)
    _config_dir: Path = field(default_factory=lambda: Path.cwd())

    def resolve_path(self, path: str) -> Path:
        p = Path(path)
        if p.is_absolute():
            return p
        return self._config_dir / p

    @property
    def bib_path(self) -> Path:
        return self.resolve_path(self.files.bib)

    @property
    def input_dir_path(self) -> Path:
        return self.resolve_path(self.files.input_dir)

    @property
    def output_dir_path(self) -> Path:
        return self.resolve_path(self.files.output_dir)


def load_config(config_path: str) -> CiteScanConfig:
    """Load configuration from YAML file."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    config = CiteScanConfig()
    config._config_dir = path.parent.absolute()

    if "files" in data:
        files = data["files"]
        config.files = FilesConfig(
            bib=files.get("bib", ""),
            input_dir=files.get("input_dir", ""),
            output_dir=files.get("output_dir", "citescan_output"),
        )
    if "bibliography" in data:
        bib = data["bibliography"]
        config.bibliography = BibliographyConfig(
            check_metadata=bib.get("check_metadata", True),
            check_duplicates=bib.get("check_duplicates", True),
            check_preprint_ratio=bib.get("check_preprint_ratio", True),
            preprint_warning_threshold=bib.get("preprint_warning_threshold", 0.50),
        )
    if "workflow" in data:
        config.workflow = [
            WorkflowStep(
                name=step.get("name", ""),
                enabled=step.get("enabled", True),
                description=step.get("description", ""),
            )
            for step in data["workflow"]
        ]
    if "output" in data:
        out = data["output"]
        config.output = OutputConfig(
            quiet=out.get("quiet", False),
            minimal_verified=out.get("minimal_verified", False),
        )
    return config


def find_config_file() -> Optional[Path]:
    """Find config file in current directory or parent directories."""
    names = ["config.yaml", "citescan.yaml", "citescan.yml", ".citescan.yaml", ".citescan.yml"]
    current = Path.cwd()
    for _ in range(5):
        for name in names:
            p = current / name
            if p.exists():
                return p
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def create_default_config(output_path: str = "config.yaml") -> str:
    """Create a default config file (bib-only)."""
    default = """# citescan Configuration (bib-only)

files:
  bib: "paper.bib"
  output_dir: "citescan_output"

bibliography:
  check_metadata: true
  check_duplicates: true
  check_preprint_ratio: true
  preprint_warning_threshold: 0.50

workflow:
  - name: arxiv_id
    enabled: true
  - name: crossref_doi
    enabled: true
  - name: semantic_scholar
    enabled: true
  - name: dblp
    enabled: true
  - name: openalex
    enabled: true
  - name: arxiv_title
    enabled: true
  - name: crossref_title
    enabled: true
  - name: google_scholar
    enabled: false

output:
  quiet: false
  minimal_verified: false
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(default)
    return output_path
