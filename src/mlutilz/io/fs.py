import bz2
import gzip
import os
import shutil
import ssl
import tarfile
import tempfile
import urllib
import zipfile
from pathlib import Path
from typing import IO, List, Union
import logging
import fsspec

LOGGER = logging.getLogger(__name__)


def get_fs(path: Union[str, Path]):
    from gcsfs import GCSFileSystem

    return None if is_local(path) else GCSFileSystem()


def _is_gcs_path(path: Union[str, Path]) -> bool:
    if isinstance(path, str):
        return path.startswith("gs://") or path.startswith("gcs://")
    else:
        return False


def is_local(path: Union[str, Path]):
    if isinstance(path, Path):
        return True
    else:
        return not (path.startswith("gs://") or path.startswith("gcs://") or path.startswith("s3://"))


def local_path(path: Union[str, Path]) -> Path:
    assert path is not None and is_local(path), f"{path} must be a local path"
    return path if isinstance(path, Path) else Path(path)


def ls(
    path: Union[str, Path],
    file_pattern: str = ".parquet",
    recursive: bool = True,
    ignore_manifest: bool = True,
    with_dirs: bool = False,
) -> List[Union[str, Path]]:
    from gcsfs import GCSFileSystem

    if _is_gcs_path(path):
        fs = GCSFileSystem()
        files = list(fs.find(path, maxdepth=None if recursive else 1, with_dirs=with_dirs))
        filtered_files = [f"gs://{f}" for f in files if file_pattern in f.split("/")[-1]]
        if ignore_manifest:
            return [f for f in filtered_files if not f.split("/")[-1].startswith("_MANIFEST")]
        return filtered_files  # type: ignore
    else:
        path = local_path(path)
        return [x for x in path.rglob("*") if file_pattern in x.name]


def exists(path: Union[str, Path]) -> bool:
    is_exists: bool
    if _is_gcs_path(path):
        is_exists = fsspec.filesystem("gs").exists(path)
    else:
        path = local_path(path)
        is_exists = path.exists()
    return is_exists


def open_fileptr(path: Union[str, Path], **kwargs):
    if _is_gcs_path(path):
        return fsspec.filesystem("gcs").open(path, **kwargs)
    else:
        path = local_path(path)
        return path.open(**kwargs)


def close_fileptr(path: Union[IO, fsspec.core.OpenFile]):
    if hasattr(path, "close"):
        path.close()


def mkdir(path: Union[str, Path], parents=True, exist_ok=True, **kwargs):
    if _is_gcs_path(path):
        fsspec.filesystem("gcs").mkdir(path)
    else:
        path = local_path(path)
        path.mkdir(parents=parents, exist_ok=exist_ok, **kwargs)


def join(path: Union[str, Path], join_str: Union[str, List[str]]) -> Union[str, Path]:
    join_str = join_str if isinstance(join_str, list) else [join_str]
    if _is_gcs_path(path):
        base_path: str = path.rstrip("/")  # type: ignore
        for j in join_str:
            base_path += "/" + j
        return base_path
    else:
        joined_path: Path = local_path(path)
        for j in join_str:
            joined_path = joined_path / j
        return joined_path


def download_url(url: str, folder: str):
    r"""Downloads the content of an URL to a specific folder.

    Args:
        url (string): The url.
        folder (string): The folder.
        log (bool, optional): If :obj:`False`, will not print anything to the
            console. (default: :obj:`True`)
    """
    from ray.air._internal.remote_storage import upload_to_uri

    filename = url.rpartition("/")[2]
    filename = filename if filename[0] == "?" else filename.split("?")[0]
    path = join(folder, filename)

    if exists(path):  # pragma: no cover
        LOGGER.info(f"Using existing file {filename}")
        return path

    LOGGER.info(f"Downloading {url}")

    # We download the zip file to a temporary folder and then copy it to the needed location
    tmp_folder = Path(tempfile.mkdtemp())
    tmp_folder.mkdir(parents=True, exist_ok=True)

    context = ssl._create_unverified_context()
    data = urllib.request.urlopen(url, context=context)  # type: ignore

    with open(join(tmp_folder, filename), "wb") as f:
        f.write(data.read())

    if not is_local(path):
        upload_to_uri(str(join(tmp_folder, filename)), str(path))
    else:
        Path(folder).mkdir(parents=True, exist_ok=True)
        shutil.copy(join(tmp_folder, filename), path)

    return path


def extract_tar(path: str, folder: str, mode: str = "r:gz"):
    r"""Extracts a tar archive to a specific folder.

    Args:
        path (string): The path to the tar archive.
        folder (string): The folder.
        mode (string, optional): The compression mode. (default: :obj:`"r:gz"`)
        log (bool, optional): If :obj:`False`, will not print anything to the
            console. (default: :obj:`True`)
    """
    LOGGER.debug(f"Extracting {path}")
    with tarfile.open(path, mode) as f:
        f.extractall(folder)


def extract_zip(path: Union[str, Path], folder: Union[str, Path]):
    r"""Extracts a zip archive to a specific folder.

    Args:
        path (string): The path to the tar archive.
        folder (string): The folder.
        log (bool, optional): If :obj:`False`, will not print anything to the
            console. (default: :obj:`True`)
    """
    from ray.air._internal.remote_storage import download_from_uri, upload_to_uri

    path = str(path)
    folder = str(folder)
    LOGGER.debug(f"Extracting {path} to {folder}")
    if not is_local(path):
        _local_path = str(Path(tempfile.mkdtemp()) / path.split("/")[-1])
        download_from_uri(path, _local_path)
    else:
        _local_path = path

    if not is_local(folder):
        _local_folder = str(Path(tempfile.mkdtemp()) / folder.split("/")[-1])
    else:
        _local_folder = folder

    with zipfile.ZipFile(_local_path, "r") as f:
        f.extractall(_local_folder)

    if not is_local(path):
        upload_to_uri(_local_folder, folder)


def extract_bz2(path: str, folder: str):
    r"""Extracts a bz2 archive to a specific folder.

    Args:
        path (string): The path to the tar archive.
        folder (string): The folder.
        log (bool, optional): If :obj:`False`, will not print anything to the
            console. (default: :obj:`True`)
    """
    LOGGER.debug(f"Extracting {path}")
    path = os.path.abspath(path)
    with bz2.open(path, "r") as r:
        with open(os.path.join(folder, ".".join(path.split(".")[:-1])), "wb") as w:
            w.write(r.read())


def extract_gz(path: str, folder: str):
    r"""Extracts a gz archive to a specific folder.

    Args:
        path (string): The path to the tar archive.
        folder (string): The folder.
        log (bool, optional): If :obj:`False`, will not print anything to the
            console. (default: :obj:`True`)
    """
    LOGGER.debug(f"Extracting {path}")
    path = os.path.abspath(path)
    with gzip.open(path, "r") as r:
        with open(os.path.join(folder, ".".join(path.split(".")[:-1])), "wb") as w:
            w.write(r.read())
