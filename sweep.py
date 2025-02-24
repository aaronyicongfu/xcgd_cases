import argparse
import os
import shutil
import logging
import re
import json
import pandas as pd
import itertools
import subprocess

logger = logging.getLogger(__name__)


def create_submit_sbatch(
    batch_name,
    case_id,
    case_path,
    exe,
    cfg,
    dry_run,
    smoke_test,
    hours: int,
):
    sbatch_path = os.path.join(case_path, "submit.sbatch")
    with open(sbatch_path, "w") as f:
        f.write("#!/bin/bash\n")
        f.write(f"#SBATCH -J {batch_name}_{case_id}\n")
        f.write("#SBATCH --account=gts-gkennedy9-coda20\n")
        f.write("#SBATCH -N1 --ntasks-per-node=1\n")
        f.write("#SBATCH --mem-per-cpu=4G\n")
        f.write(f"#SBATCH -t {hours}:00:00\n")
        f.write("#SBATCH -q inferno\n")
        f.write(f"#SBATCH -o {os.path.join(case_path,'Report-%j.out')}\n")
        f.write("\n")
        f.write(f"cd {os.path.abspath(case_path)}\n")
        if smoke_test:
            f.write(f"srun --account=gts-gkennedy9-coda20 {exe} {cfg} --smoke\n")
        else:
            f.write(f"srun --account=gts-gkennedy9-coda20 {exe} {cfg}\n")

    cmd = ["sbatch", os.path.abspath(sbatch_path)]
    if dry_run:
        logger.info("dryrun: " + " ".join(cmd))
    else:
        logger.info("executing: " + " ".join(cmd))
        subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )


def create_cases(
    sweep_json,
    exe_path,
    template_cfg_path,
    output_path,
    dry_run=False,
    smoke_test=False,
    hours=24,
):
    with open(sweep_json, "r") as f:
        json_dict = json.load(f)

    if "__comment__" in json_dict:
        del json_dict["__comment__"]

    const_params = {}
    variable_params = {}
    grouped_params = {}

    for k, v in json_dict.items():
        if isinstance(v, list):
            variable_params[k] = v
        elif isinstance(v, dict):
            grouped_params[k] = v
            # Sanity check
            nopts = len(next(iter(v.values())))
            for kk, vv in v.items():
                assert isinstance(
                    vv, list
                ), f"options in {k} should all be specified as lists"
                assert (
                    len(vv) == nopts
                ), f"options lists in {k} should all have same length"

        else:
            const_params[k] = v

    opt_names = list(variable_params.keys()) + list(
        list(d.keys()) for d in grouped_params.values()
    )
    opt_vals = list(variable_params.values()) + [
        [list(v) for v in zip(*d.values())] for d in grouped_params.values()
    ]

    cases_params = []
    for vals in itertools.product(*opt_vals):
        opts_dict = const_params.copy()

        for k, v in zip(opt_names, vals):
            if isinstance(k, list):
                for kk, vv in zip(k, v):
                    opts_dict[kk] = vv
            else:
                opts_dict[k] = v
        cases_params.append(opts_dict)

    df = pd.DataFrame(cases_params)
    options = list(df.columns)

    df.insert(0, "case_id", df.index)
    # df.insert(1, "case_path", "case_" + df.index.astype(str))
    df.to_csv(os.path.join(output_path, "cases.csv"))

    re_patterns = [re.compile(opt + r".*\n") for opt in options]

    # Populate each case folder
    for case_id, case_dict in enumerate(cases_params):
        case_path = os.path.join(output_path, f"case_{case_id}")
        os.makedirs(case_path, exist_ok=False)

        # Create case cfg
        cfg = os.path.basename(template_cfg_path)
        with open(template_cfg_path, "r") as infile, open(
            os.path.join(case_path, cfg), "w"
        ) as outfile:
            for line in infile:
                for opt, patt in zip(options, re_patterns):
                    line = patt.sub(f"{opt} = {case_dict[opt]}\n", line)

                outfile.write(line)

        # Copy executable
        exe = os.path.basename(exe_path)
        shutil.copy2(exe_path, case_path)

        # Create sbatch
        batch_name = os.path.basename(output_path)
        create_submit_sbatch(
            batch_name, case_id, case_path, exe, cfg, dry_run, smoke_test, hours
        )


if __name__ == "__main__":

    default_asset_dir = os.path.join(
        str(os.environ.get("HOME")),
        "git",
        "xcgd",
        "build",
        "examples",
        "topology_optimization",
    )

    p = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument(
        "template_cfg_path",
        type=str,
        help="path to the template config file",
    )
    p.add_argument(
        "sweep_json_path",
        type=str,
        help="path to a json defining the sweep parameters",
    )
    p.add_argument(
        "output_path",
        type=str,
        help="path to a folder where we put all cases in this batch in",
    )
    p.add_argument(
        "--exe-path",
        default=os.path.join(default_asset_dir, "topo"),
        type=str,
        help="path to the executable",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="generate folders, files and commands, but don't submit jobs",
    )
    p.add_argument(
        "--smoke-test",
        action="store_true",
        help="perform smoke test with reduced-size problems",
    )
    p.add_argument("--hours", default=24, type=int, help="job time limit")
    args = p.parse_args()

    os.makedirs(args.output_path, exist_ok=False)
    logging.basicConfig(
        handlers=[
            logging.FileHandler(os.path.join(args.output_path, "sweep.log")),
            logging.StreamHandler(),
        ],
        level=logging.INFO,
        format="[%(levelname)s][%(asctime)s]%(name)s:%(message)s",
    )

    shutil.copy2(args.sweep_json_path, args.output_path)
    shutil.copy2(args.template_cfg_path, args.output_path)

    create_cases(
        args.sweep_json_path,
        args.exe_path,
        args.template_cfg_path,
        args.output_path,
        dry_run=args.dry_run,
        smoke_test=args.smoke_test,
        hours=args.hours,
    )
