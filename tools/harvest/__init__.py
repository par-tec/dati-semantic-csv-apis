import logging
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from tools.store import build_vocabulary_uuid

log = logging.getLogger(__name__)

SPARQL_ENDPOINT = "https://schema.gov.it/sparql"
SQLITE_URL = "sqlite:///harvest.db"


def _gh_to_raw_url(url: str) -> str:
    """
    Convert a GitHub URL to a raw.githubusercontent.com URL if needed.
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc == "github.com":
        path_parts = parsed.path.strip("/").split("/")
        if len(path_parts) >= 5 and path_parts[2] == "blob":
            user, repo, _, branch, *file_path = path_parts
            raw_url = f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{'/'.join(file_path)}"
            return raw_url
    return url


@dataclass(frozen=True)
class VocabularyRepository:
    download_url: str
    key_concept: str
    rights_holder: str
    vocabulary_uri: str

    @property
    def vocabulary_uuid(self) -> str:
        return build_vocabulary_uuid(
            agency_id=self.agency_id,
            key_concept=self.key_concept,
        )

    @property
    def agency_id(self) -> str:
        return Path(self.rights_holder).name.lower()

    def download(self, destination_folder: Path) -> dict[str, str]:
        destination_folder.mkdir(parents=True, exist_ok=True)

        if isinstance(self.download_url, list):
            source_url: str = next(
                url
                for url in self.download_url
                if url.endswith(f"{self.key_concept}.ttl")
            )
        else:
            source_url = self.download_url

        source_url = _gh_to_raw_url(source_url)

        source_stem: str = source_url.removesuffix(".ttl")

        vocab_ttl = destination_folder / f"{self.key_concept}.ttl"
        frame_yamlld = vocab_ttl.with_suffix(".frame.yamlld")
        openapi_yaml = vocab_ttl.with_suffix(".oas3.yaml")
        data_yamlld = vocab_ttl.with_suffix(".data.yamlld")
        remote_to_local = {
            source_url: vocab_ttl,
            f"{source_stem}.frame.yamlld": frame_yamlld,
            f"{source_stem}.oas3.yaml": openapi_yaml,
            f"{source_stem}.data.yamlld": data_yamlld,
        }

        for remote_url, local_path in remote_to_local.items():
            try:
                with urllib.request.urlopen(remote_url) as response:
                    local_path.write_bytes(response.read())
                log.info("Downloaded %s to %s", remote_url, local_path)
            except Exception as e:
                log.warning("Failed to download %s: %s", remote_url, e)
        return {
            "path": destination_folder.as_posix(),
            "vocabulary_ttl": vocab_ttl,
            **self.__dict__,
        }

    def validate(self) -> bool:
        return True
