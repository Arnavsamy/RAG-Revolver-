import json, shutil, tempfile, zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
DATA=ROOT/"data"; BACKUPS=DATA/"backups"

def create_backup():
    BACKUPS.mkdir(parents=True,exist_ok=True); stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"); target=BACKUPS/f"revolver-{stamp}.zip"; included=[]
    with zipfile.ZipFile(target,"w",zipfile.ZIP_DEFLATED) as archive:
        for path in [DATA/"revolver.sqlite3", DATA/"chroma", ROOT/"models"]:
            if path.is_file(): archive.write(path,path.relative_to(ROOT)); included.append(str(path.relative_to(ROOT)))
            elif path.is_dir():
                for child in path.rglob("*"):
                    if child.is_file(): archive.write(child,child.relative_to(ROOT)); included.append(str(child.relative_to(ROOT)))
        archive.writestr("manifest.json",json.dumps({"created_at":stamp,"files":included},indent=2))
    return {"path":str(target),"name":target.name,"created_at":stamp,"files":included}

def list_backups():
    BACKUPS.mkdir(parents=True,exist_ok=True); return [{"name":p.name,"path":str(p),"size":p.stat().st_size} for p in sorted(BACKUPS.glob("*.zip"),reverse=True)]

def restore_backup(name: str):
    target=(BACKUPS/name).resolve()
    if target.parent != BACKUPS.resolve() or target.suffix.lower() != ".zip" or not target.exists(): raise FileNotFoundError("backup not found")
    with tempfile.TemporaryDirectory() as temp:
        with zipfile.ZipFile(target) as archive: archive.extractall(temp)
        source=Path(temp)
        for relative in [Path("data/revolver.sqlite3"),Path("data/chroma"),Path("models")]:
            src=source/relative
            if not src.exists(): continue
            dst=ROOT/relative; dst.parent.mkdir(parents=True,exist_ok=True)
            if src.is_dir():
                if dst.exists(): shutil.rmtree(dst)
                shutil.copytree(src,dst)
            else: shutil.copy2(src,dst)
    return {"restored":name}
