"""Declared execution boundary for the two reviewed Random examples, not a sandbox."""

import os
from pathlib import Path
import shutil

from example_syntax import SCHEMAS, read_body

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


def inspect_source(path, module, is_test=False):
    """Check real declarations; values/labels are not declaration keywords."""
    body = read_body(path, is_test)

    def inspect(body, context):
        schema = SCHEMAS.get(context, {})
        if context in ("source", "tests") and body.attrs:
            raise ValueError(f"{path}: top-level attributes require an execution-policy review.")
        for name, labels, child in body.blocks:
            if name not in schema or len(labels) != schema[name]:
                raise ValueError(f"{path}: {name} is outside the reviewed execution-policy declarations.")
            if name in ("resource", "provider") and labels[0] != ("random_pet" if name == "resource" else "random"):
                raise ValueError(f"{path}: {name} {labels[0]} requires an execution-policy review.")
            if name == "module":
                source = child.attrs.get("source")
                if module != ROOT_MODULE or is_test or source is None or source.literal() != "../../child-modules/random-pet":
                    raise ValueError(f"{path}: unregistered source; only the root's declared local child is permitted.")
            if name == "required_providers":
                for provider, requirement in child.attrs.items():
                    fields = requirement.object_attrs()
                    source = fields.get("source")
                    if provider != "random" or source is None or source.literal() != "hashicorp/random":
                        raise ValueError(f"{path}: unregistered source/provider; only hashicorp/random is permitted.")
            inspect(child, name)

    inspect(body, "tests" if is_test else "source")


def reject_masked_inputs(path, run_names):
    """Defaults/file cases must not supply higher-precedence variables blocks."""
    body = read_body(path, is_test=True)
    if any(name == "variables" or (name == "run" and len(labels) == 1 and labels[0] in run_names and
           any(kind == "variables" for kind, _, _ in child.blocks))
           for name, labels, child in body.blocks):
        raise ValueError(f"{path}: variables block masks declared defaults or actual tfvars precedence.")


def reject_engine_sources(directory, names):
    for name in names:
        if name.endswith((".tofu", ".tofu.json", ".tofutest.hcl", ".tofutest.json")):
            raise ValueError(f"Engine-specific source/test shadow is not supported: {directory / name}; "
                             "use shared .tf/.tf.json and .tftest files so both engines check the same source.")


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
            if module.is_dir():
                reject_engine_sources(module, [p.name for p in module.iterdir()])
                if any(p.name.endswith(SOURCE) for p in module.iterdir()):
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
            reject_engine_sources(directory, [p.name for p in directory.iterdir()])
            for p in directory.iterdir():
                if p.name.endswith(TEST):
                    paths.append(p)
            if varfile:
                paths.append(base / varfile)
        declared_dirs = {base / spec[0] for spec in policy["fixtures"].values()}
        # Never silently omit a newly added fixture directory or follow its symlink.
        for directory, subdirs, names in os.walk(base / "tests", followlinks=False):
            directory = Path(directory)
            reject_engine_sources(directory, names)
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
