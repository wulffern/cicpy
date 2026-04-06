#!/usr/bin/env python3
import argparse
import os
import re
import shutil
import subprocess

def run_command(cmd):
    result = subprocess.run(cmd, shell=True, check=True, text=True, capture_output=True)
    return result.stdout


def parse_block(buff):
    obj = {}
    for raw_line in buff.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        obj[key.strip()] = value.strip()
    return obj


def resolve_input_path(path_value, base_dir):
    if os.path.isabs(path_value):
        return path_value
    return os.path.normpath(os.path.join(base_dir, path_value))


def handle_cat(buff, outdir, base_dir):
    obj = parse_block(buff)
    display_name = obj["file"]
    finame = resolve_input_path(display_name, base_dir)
    language = obj.get("language", "")
    line_limit = int(obj["lines"]) if "lines" in obj else None
    linenumbers = obj.get("linenumbers", "").lower() in ("1", "true", "yes")

    rendered = []
    with open(finame) as fi:
        for linenr, line in enumerate(fi):
            if line_limit is not None and linenr >= line_limit:
                break
            if linenumbers:
                rendered.append(f"{linenr} {line}")
            else:
                rendered.append(line)

    text = "".join(rendered)
    if language == "markdown":
        return text + "\n\n"
    return f"{display_name}:\n```{language}\n{text}\n```\n\n"


def handle_run_output(buff, outdir, base_dir):
    obj = parse_block(buff)
    cmd = obj["run"]
    return f"```bash\n{cmd}\n```\n\n```bash\n{run_command(cmd)}\n```\n\n"


def handle_run_image(buff, outdir, base_dir):
    obj = parse_block(buff)
    cmd = obj["run"]
    image = resolve_input_path(obj["output_image"], base_dir)
    asset_name = obj.get("asset_name", os.path.basename(image))
    assets_dir = os.path.join(outdir, "assets")
    os.makedirs(assets_dir, exist_ok=True)
    dst = os.path.join(assets_dir, asset_name)
    subprocess.run(cmd, shell=True, check=True)
    copy_if_newer(image, dst)
    return f"```bash\n{cmd}\n```\n\n![](/cicpy/assets/{asset_name})\n\n"


def handle_copy_image(buff, outdir, base_dir):
    obj = parse_block(buff)
    image = resolve_input_path(obj["output_image"], base_dir)
    asset_name = obj.get("asset_name", os.path.basename(image))
    assets_dir = os.path.join(outdir, "assets")
    os.makedirs(assets_dir, exist_ok=True)
    dst = os.path.join(assets_dir, asset_name)
    copy_if_newer(image, dst)
    return f"![](/cicpy/assets/{asset_name})\n\n"


def copy_if_newer(src, dst):
    if not os.path.exists(dst):
        shutil.copy2(src, dst)
        return
    if os.path.getmtime(src) > os.path.getmtime(dst):
        shutil.copy2(src, dst)


HANDLERS = {
    "cat": handle_cat,
    "run_output": handle_run_output,
    "run_image": handle_run_image,
    "copy_image": handle_copy_image,
}


def cli(finame, foname):
    outdir = os.path.dirname(foname)
    base_dir = os.path.dirname(os.path.abspath(finame))
    cmd = ""
    collecting = False
    buff = []

    if outdir:
        os.makedirs(outdir, exist_ok=True)

    with open(finame) as fi, open(foname, "w") as fo:
        for line in fi:
            if re.search(r"^-->", line):
                collecting = False
                handler = HANDLERS.get(cmd)
                if handler is None:
                    raise RuntimeError(f"Unsupported docs command: {cmd}")
                fo.write(handler("".join(buff), outdir, base_dir))
                cmd = ""
                buff = []
                continue

            if collecting:
                buff.append(line)
                continue

            m = re.search(r"^<!--([^:]+):", line)
            if m:
                collecting = True
                cmd = m.group(1)
                buff = []
                continue

            fo.write(line)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("finame")
    parser.add_argument("foname")
    args = parser.parse_args()
    cli(args.finame, args.foname)
