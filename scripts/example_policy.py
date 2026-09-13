"""Declared execution boundary for the two reviewed Random examples, not a sandbox."""

import json
import os
import re
from pathlib import Path
import shutil

CHILD = "child-modules/random-pet"
ROOT_MODULE = "root-modules/template-root-module"
CHILD_RUNS = {"defaults", "custom_inputs", "minimum_length", "zero_length", "negative_length", "generated_output"}
# (selected test directory, required file, required runs, explicit var-file)
INVENTORY = {
    CHILD: {
        "dependencies": (), "provider": "hashicorp/random", "apply": "random_pet only",
        "fixtures": {"child": ("tests", "random_pet.tftest.hcl", CHILD_RUNS, None)},
    },
    ROOT_MODULE: {
        "dependencies": (CHILD,), "provider": "hashicorp/random", "apply": "random_pet only",
        # Root and child deliberately share immutable engine-specific Random locks.
        "fixtures": {
            "behavior": ("tests", "behavior.tftest.hcl", {"custom_inputs", "minimum_length", "zero_length", "negative_length"}, None),
            "defaults": ("tests/defaults", "defaults.tftest.hcl", {"defaults"}, None),
            "example": ("tests/example", "example.tftest.hcl", {"shipped_example"}, None),
            "dev": ("tests/dev", "dev.tftest.hcl", {"dev_file"}, "tfvars/dev.tfvars"),
            "prod": ("tests/prod", "prod.tftest.hcl", {"prod_file"}, "tfvars/prod.tfvars"),
        },
    },
}
AUTO = ("terraform.tfvars", "terraform.tfvars.json", "*.auto.tfvars", "*.auto.tfvars.json")
SOURCE = (".tf", ".tf.json")
TEST = (".tftest.hcl", ".tftest.json")


def tokens(text):
    """Tokenize only enough syntax to apply the narrow review policy."""
    # Preserve strings while dropping comments. Native CLIs remain the HCL parser.
    # Heredocs are outside these examples' reviewed source/copy policy.
    if re.search(r"<<-?\w+", text):
        raise ValueError("Heredoc requires an explicit example-boundary review.")
    return [t for t in re.findall(r'"(?:\\.|[^"\\])*"|/\*[\s\S]*?\*/|//[^\n]*|\#[^\n]*|[A-Za-z_][\w-]*|[^\s]', text)
            if not t.startswith(("/*", "//", "#"))]


def inspect_source(path, module, is_test=False):
    """Reject known execution escapes before any init; not a generic HCL auditor."""
    text = path.read_text()
    parts = tokens(text)
    allowed_sources = {"hashicorp/random"}
    if module == ROOT_MODULE and not is_test:
        allowed_sources.add("../../child-modules/random-pet")
    if path.name.endswith(".json"):
        def inspect_json(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key in {"data", "backend", "cloud", "provisioner", "mock_provider", "override_resource", "override_module", "override_data"}:
                        raise ValueError(f"{path}: {key} is outside the reviewed Random execution policy.")
                    if key == "source" and item not in allowed_sources:
                        raise ValueError(f"{path}: unregistered source {item!r}.")
                    if key in ("resource", "provider"):
                        allowed = {"random_pet"} if key == "resource" else {"random"}
                        if not isinstance(item, dict) or not set(item) <= allowed:
                            raise ValueError(f"{path}: {key} requires an execution-policy review.")
                    if is_test and key == "module":
                        raise ValueError(f"{path}: test module substitution is not permitted.")
                    inspect_json(item)
            elif isinstance(value, list):
                for item in value:
                    inspect_json(item)
            elif isinstance(value, str) and re.search(r"\b(file[a-z0-9]*|templatefile)\s*\(", value):
                raise ValueError(f"{path}: filesystem function requires a copy-boundary review.")
        inspect_json(json.loads(text))
        return
    # This deliberately restrictive token policy handles the supplied HCL examples.
    words = [t[1:-1] if t.startswith('"') and t.endswith('"') else t for t in parts]
    forbidden = {"provisioner", "backend", "cloud", "data", "mock_provider", "override_resource", "override_module", "override_data"}
    for i, word in enumerate(words):
        after = words[i + 1:i + 3]
        if word in forbidden and after and (after[0] in ("{", ":") or parts[i + 1].startswith('"')):
            raise ValueError(f"{path}: {word} is outside the reviewed Random execution policy.")
        if word == "source" and after and after[0] in ("=", ":"):
            if len(after) < 2 or after[1] not in allowed_sources:
                raise ValueError(f"{path}: unregistered source; only {sorted(allowed_sources)} are permitted.")
        if word in ("resource", "provider") and after:
            name = after[0]
            if name not in ({"random_pet"} if word == "resource" else {"random"}):
                raise ValueError(f"{path}: {word} {name} requires an execution-policy review.")
    for i, word in enumerate(words):
        direct = re.fullmatch(r"file[a-z0-9]*|templatefile", word) and words[i + 1:i + 2] == ["("]
        interpolated = "${" in word and re.search(r"\b(file[a-z0-9]*|templatefile)\s*\(", word)
        if direct or interpolated:
            raise ValueError(f"{path}: filesystem function requires a copy-boundary review.")
    if is_test and any(w == "module" and words[i + 1:i + 2] == ["{"] for i, w in enumerate(words)):
        raise ValueError(f"{path}: test module substitution is not permitted for these real-example checks.")


def reject_masked_inputs(path, run_names):
    """Defaults/file cases must not supply inputs through higher-precedence blocks."""
    parts = tokens(path.read_text())
    depth, protected = 0, False
    for i, token in enumerate(parts):
        if depth == 0 and token == "run" and i + 1 < len(parts):
            protected = parts[i + 1].strip('"') in run_names
        if token == "variables" and (depth == 0 or protected):
            raise ValueError(f"{path}: variables block masks declared defaults or actual tfvars precedence.")
        depth += (token == "{") - (token == "}")


def inspect_tree(root):
    """Inspect actual working-tree files, including new/uncommitted modules."""
    discovered = set()
    for category in ("child-modules", "root-modules"):
        parent = root / category
        if parent.is_symlink():
            raise ValueError(f"Symlink outside the copy boundary: {parent}")
        for module in parent.iterdir():
            if module.is_symlink():
                raise ValueError(f"Symlink outside the copy boundary: {module}")
            if module.is_dir() and any(p.name.endswith(SOURCE) for p in module.iterdir()):
                discovered.add(module.relative_to(root).as_posix())
    if discovered != set(INVENTORY):
        raise ValueError(f"Module coverage mismatch: unregistered={sorted(discovered - set(INVENTORY))}, missing={sorted(set(INVENTORY) - discovered)}. Review and register dependencies, locks, fixtures and apply policy before execution.")
    selected = {}
    for module, policy in INVENTORY.items():
        base = root / module
        paths = list(base.glob("*.tf")) + list(base.glob("*.tf.json"))
        for mode, (testdir, filename, required, varfile) in policy["fixtures"].items():
            directory = base / testdir
            if directory.is_symlink() or any(p.is_symlink() for p in directory.parents if p != root and root in p.parents):
                raise ValueError(f"Symlink outside the copy boundary: {directory}")
            testfile = directory / filename
            if testfile.is_symlink() or not testfile.is_file():
                raise ValueError(f"Missing required test file: {testfile}")
            if mode in ("child", "defaults", "example", "dev", "prod"):
                reject_masked_inputs(testfile, {"defaults"} if mode == "child" else required)
            for folder in (base, directory):
                for pattern in AUTO:
                    for auto in folder.glob(pattern):
                        if not (module == ROOT_MODULE and auto == base / "example.auto.tfvars"):
                            raise ValueError(f"Unexpected auto-loaded variable file: {auto}; move it before checking defaults/precedence.")
            for p in directory.iterdir():
                if p.name.endswith((".tofutest.hcl", ".tofutest.json")):
                    raise ValueError(f"Engine-specific test shadow is not supported: {p}")
                if p.name.endswith(TEST):
                    paths.append(p)
            if varfile:
                paths.append(base / varfile)
        declared_dirs = {base / spec[0] for spec in policy["fixtures"].values()}
        # Never silently omit a newly added fixture directory or follow its symlink.
        for directory, subdirs, names in os.walk(base / "tests", followlinks=False):
            directory = Path(directory)
            if any((directory / name).is_symlink() for name in subdirs + names):
                raise ValueError(f"Symlink outside the test copy boundary: {directory}")
            if directory not in declared_dirs and any(name.endswith(TEST) for name in names):
                raise ValueError(f"Unregistered test directory: {directory}; declare its fixture before execution.")
        # Tests at module top level are also automatically discovered by both engines.
        if any(p.name.endswith(TEST + (".tofutest.hcl", ".tofutest.json")) for p in base.iterdir()):
            raise ValueError(f"Put tests in the declared test directories: {base}")
        if module == ROOT_MODULE:
            paths.append(base / "example.auto.tfvars")
        for p in set(paths):
            if p.is_symlink() or any(a.is_symlink() for a in p.parents if root in a.parents) or not p.is_file() or not p.stat().st_mode & 0o444:
                raise ValueError(f"Missing, unreadable or symlinked source: {p}")
            if p.name.endswith(SOURCE + TEST):
                inspect_source(p, module, p.name.endswith(TEST))
        selected[module] = set(paths)
    for tool in ("terraform", "tofu"):
        lock = root / CHILD / f"tests/locks/{tool}.lock.hcl"
        if lock.is_symlink() or any(a.is_symlink() for a in lock.parents if root in a.parents) or not lock.is_file():
            raise ValueError(f"Missing or symlinked provider lock: {lock}")
    return selected


def stage(root, destination, selected, module, mode, tool):
    """Copy only reviewed working-tree sources, preserving local dependencies."""
    for name in (module, *INVENTORY[module]["dependencies"]):
        for source in selected[name]:
            if mode == "defaults" and name == ROOT_MODULE and source.name == "example.auto.tfvars":
                continue
            target = destination / source.relative_to(root)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    work = destination / module
    shutil.copyfile(root / CHILD / f"tests/locks/{tool}.lock.hcl", work / ".terraform.lock.hcl")
    return work
