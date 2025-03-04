import numpy as np
import os
import argparse
from glob import glob
from tqdm import tqdm
import pandas as pd

import logging
logger = logging.getLogger(__name__)

def parse_mma_history(mma_apath):
    num_iters = -1
    fobj = np.nan
    if not os.path.exists(mma_apath):
        return num_iters, fobj

    lines = []
    with open(mma_apath, "r") as f:
        for l in f:
            lines.append(l.strip())

    for l in reversed(lines):
        if "MMA" in l:
            continue  # Skip header lines
        num_iters = int(l.split()[0])
        fobj = float(l.split()[2])
        break

    return num_iters, fobj


if __name__ == "__main__":

    p = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument(
        "batch_path",
        type=str,
        help="path to a folder where we put all cases in this batch in",
    )
    args = p.parse_args()

    batch_apath = os.path.abspath(args.batch_path)
    if not os.path.isdir(batch_apath):
        raise RuntimeError(f"batch folder {batch_apath} doesn't exist")

    logging.basicConfig(
        handlers=[
            logging.FileHandler(os.path.join(batch_apath, "visualize.log")),
            logging.StreamHandler(),
        ],
        level=logging.INFO,
        format="[%(levelname)s][%(asctime)s]%(message)s",
    )

    # Find all case folders
    case_apaths = glob(os.path.join(batch_apath, "case_*"))
    case_apaths = [d for d in case_apaths if os.path.isdir(d)]
    case_apaths.sort(
        key=lambda case_path: int(os.path.basename(case_path).split("_")[-1])
    )

    df_data = {"case_id": [], "niters": [], "fobj": []}

    for case_apath in tqdm(case_apaths):
        results = glob(os.path.join(case_apath, "opt_*"))
        results = [d for d in results if os.path.isdir(d)]
        results.sort(
            key=lambda result_folder: int(
                os.path.basename(result_folder).split("_")[-1]
            )
        )

        if len(results) == 0:
            logger.warning(f"no result folder for case {case_apath}")
            continue

        result_folder = results[-1]
        if len(results) > 1:
            logger.warning(
                f" {case_apath} contains multiple result folders, using latest {result_folder}"
            )

        # parse mma history
        niters, fobj = parse_mma_history(os.path.join(result_folder, "paropt.mma"))

        # Get case id
        case_id = int(os.path.basename(case_apath).split("_")[-1])

        df_data["case_id"].append(case_id)
        df_data["niters"].append(niters)
        df_data["fobj"].append(fobj)

    df = pd.DataFrame(df_data)
    df.to_csv(os.path.join(batch_apath, "mma_results.csv"))
